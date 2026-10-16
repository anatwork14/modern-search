use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{mpsc, Mutex, OnceLock};
use std::path::PathBuf;
use std::thread;
use std::time::Duration;
use tauri::Manager;

const SERVICE_TIMEOUT: Duration = Duration::from_secs(30);
const MAX_RESPONSE_BYTES: u64 = 8 * 1024 * 1024;
const MAX_REQUEST_BYTES: usize = 1_048_576;

#[derive(Debug, Deserialize, Serialize)]
struct RpcRequest {
    version: u8,
    id: String,
    command: String,
    #[serde(default)]
    payload: Value,
}

#[derive(Debug, Deserialize, Serialize)]
struct RpcError {
    code: String,
    message: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct RpcResponse {
    version: u8,
    id: String,
    ok: bool,
    #[serde(default)]
    data: Option<Value>,
    #[serde(default)]
    error: Option<RpcError>,
}

static BUNDLED_RESOURCE_ROOT: OnceLock<PathBuf> = OnceLock::new();

fn repository_root() -> Result<PathBuf, String> {
    if !cfg!(debug_assertions) {
        let resources = BUNDLED_RESOURCE_ROOT.get()
            .ok_or_else(|| "Bundled backend resources are not initialized".to_string())?;
        if !resources.join("backend/service.py").is_file() {
            return Err("The packaged search service is missing from Resources".into());
        }
        return Ok(resources.clone());
    }
    // Development uses the checked-out source tree. Production uses the
    // bundled, read-only backend modules, never UI-provided executable paths.
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest.parent().and_then(|p| p.parent()).and_then(|p| p.parent())
        .ok_or_else(|| "Could not locate the repository root".to_string())?;
    if !root.join("backend/service.py").is_file() {
        return Err("Local search backend source is missing".into());
    }
    Ok(root.to_path_buf())
}

fn python_executable() -> PathBuf {
    if let Ok(configured) = std::env::var("MODERN_SEARCH_PYTHON") {
        if !configured.is_empty() {
            return PathBuf::from(configured);
        }
    }
    // Finder-launched macOS apps often do not inherit the Homebrew PATH.
    // Prefer explicitly installed host Python before the system fallback.
    for candidate in [
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/opt/homebrew/bin/python3.11",
        "/usr/local/bin/python3.11",
        "/usr/bin/python3",
    ] {
        if PathBuf::from(candidate).is_file() {
            return PathBuf::from(candidate);
        }
    }
    PathBuf::from("python3")
}

fn internal_error(message: &str) -> RpcError {
    RpcError { code: "INTERNAL_ERROR".into(), message: message.into() }
}

/// Read exactly one newline-delimited response without allowing an unbounded
/// stdout allocation. A malformed or overlarge frame invalidates this worker.
fn read_bounded_frame(reader: &mut impl BufRead) -> Result<Option<Vec<u8>>, String> {
    let mut frame = Vec::new();
    loop {
        let available = reader.fill_buf().map_err(|_| "Worker response read failed".to_string())?;
        if available.is_empty() {
            return if frame.is_empty() {
                Ok(None)
            } else {
                Err("Worker closed an incomplete response".to_string())
            };
        }
        let newline = available.iter().position(|byte| *byte == b'\n');
        let take = newline.map_or(available.len(), |index| index + 1);
        if frame.len().saturating_add(take) > MAX_RESPONSE_BYTES as usize {
            return Err("Worker response exceeded the size limit".to_string());
        }
        frame.extend_from_slice(&available[..take]);
        reader.consume(take);
        if newline.is_some() {
            return Ok(Some(frame));
        }
    }
}

/// Single child owned by the app. The stdio channel is never exposed over a
/// listening port; child I/O is serialized so response IDs cannot interleave.
struct Worker {
    child: Child,
    stdin: ChildStdin,
    responses: mpsc::Receiver<Result<Vec<u8>, String>>,
}

impl Worker {
    fn spawn() -> Result<Self, RpcError> {
        let root = repository_root().map_err(|message| internal_error(&message))?;
        let mut child = Command::new(python_executable())
            .arg("-m")
            .arg("backend.service")
            .current_dir(&root)
            .env("PYTHONPATH", &root)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|_| internal_error("Could not start the local Python service. Check Python 3.11+."))?;
        let stdin = child.stdin.take().ok_or_else(|| internal_error("Could not open worker input"))?;
        let stdout = child.stdout.take().ok_or_else(|| internal_error("Could not open worker output"))?;
        let (sender, receiver) = mpsc::channel();
        thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            loop {
                match read_bounded_frame(&mut reader) {
                    Ok(Some(frame)) => {
                        if sender.send(Ok(frame)).is_err() {
                            break;
                        }
                    }
                    Ok(None) => {
                        let _ = sender.send(Err("Worker exited".to_string()));
                        break;
                    }
                    Err(message) => {
                        let _ = sender.send(Err(message));
                        break;
                    }
                }
            }
        });
        Ok(Self { child, stdin, responses: receiver })
    }

    fn exchange(&mut self, request: &[u8]) -> Result<Vec<u8>, RpcError> {
        if self.child.try_wait().map_err(|_| internal_error("Worker status unavailable"))?.is_some() {
            return Err(internal_error("Local worker unexpectedly exited"));
        }
        self.stdin.write_all(request)
            .and_then(|_| self.stdin.write_all(b"\n"))
            .and_then(|_| self.stdin.flush())
            .map_err(|_| internal_error("Could not send request to the local worker"))?;
        self.responses.recv_timeout(SERVICE_TIMEOUT)
            .map_err(|_| internal_error("Local search worker timed out or disconnected"))?
            .map_err(|_| internal_error("Local search worker sent an invalid response"))
    }
}

impl Drop for Worker {
    fn drop(&mut self) {
        // On timeout, invalid response or app shutdown, do not leave a
        // detached process processing private research data.
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

static SERVICE_WORKER: OnceLock<Mutex<Option<Worker>>> = OnceLock::new();

fn invoke_service(command_name: &str, payload: Value) -> Result<Value, RpcError> {
    let request = RpcRequest {
        version: 1,
        id: format!("desktop-{}", uuid()),
        command: command_name.into(),
        payload,
    };
    let request_bytes = serde_json::to_vec(&request)
        .map_err(|_| internal_error("Could not encode the search request"))?;
    if request_bytes.len() > MAX_REQUEST_BYTES {
        return Err(RpcError {
            code: "INVALID_REQUEST".into(),
            message: "Local search request exceeded the 1 MiB limit".into(),
        });
    }

    let mut slot = SERVICE_WORKER
        .get_or_init(|| Mutex::new(None))
        .lock()
        .map_err(|_| internal_error("Local worker synchronization failed"))?;
    if slot.is_none() {
        *slot = Some(Worker::spawn()?);
    }
    let raw = match slot.as_mut().expect("worker initialized").exchange(&request_bytes) {
        Ok(raw) => raw,
        Err(error) => {
            // Drop/reap unhealthy child now; the NEXT user request will start
            // a clean worker. Avoid silently retrying an already-sent request.
            *slot = None;
            return Err(error);
        }
    };

    let response: RpcResponse = match serde_json::from_slice(&raw) {
        Ok(parsed) => parsed,
        Err(_) => {
            *slot = None;
            return Err(internal_error("Local worker returned malformed JSON"));
        }
    };
    if response.version != 1 || response.id != request.id {
        *slot = None;
        return Err(internal_error("Local worker returned a mismatched response"));
    }
    // Application-level invalid filter / request errors are well-formed and
    // DO NOT terminate the healthy worker.
    if response.ok {
        Ok(response.data.unwrap_or(Value::Null))
    } else {
        Err(response.error.unwrap_or_else(|| internal_error("Local search request failed")))
    }
}

async fn invoke_service_async(command_name: &'static str, payload: Value) -> Result<Value, RpcError> {
    tauri::async_runtime::spawn_blocking(move || invoke_service(command_name, payload))
        .await
        .map_err(|_| RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "The local search worker could not complete the request.".into(),
        })?
}

fn uuid() -> String {
    // Request IDs are correlation labels, not credentials or authorization tokens.
    format!("{}-{}", std::process::id(), std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos())
}

#[tauri::command]
async fn service_health() -> Result<Value, RpcError> {
    invoke_service_async("health", Value::Object(Default::default())).await
}

#[tauri::command]
async fn search(request: Value) -> Result<Value, RpcError> {
    invoke_service_async("search", request).await
}

#[tauri::command]
async fn taxonomy() -> Result<Value, RpcError> {
    invoke_service_async("taxonomy", Value::Object(Default::default())).await
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![service_health, search, taxonomy])
        .setup(|app| {
            if !cfg!(debug_assertions) {
                let resources = app.path().resource_dir()?;
                if !resources.join("backend/service.py").is_file() {
                    return Err("Packaged Python search backend is missing".into());
                }
                let _ = BUNDLED_RESOURCE_ROOT.set(resources);
            }
            if let Some(window) = app.get_webview_window("main") {
                window.set_title("ResearchOS")?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running ResearchOS desktop");
}

#[cfg(test)]
mod tests {
    use super::invoke_service;
    use serde_json::json;
    use std::path::Path;


    #[test]
    fn bounded_frames_reject_oversize_and_partial_responses() {
        use super::{read_bounded_frame, MAX_RESPONSE_BYTES};
        use std::io::BufReader;
        let mut good = BufReader::new(&b"ready\n"[..]);
        assert_eq!(read_bounded_frame(&mut good).unwrap(), Some(b"ready\n".to_vec()));
        assert_eq!(read_bounded_frame(&mut good).unwrap(), None);
        let too_large = vec![b'x'; MAX_RESPONSE_BYTES as usize + 1];
        assert!(read_bounded_frame(&mut BufReader::new(too_large.as_slice())).is_err());
        assert!(read_bounded_frame(&mut BufReader::new(&b"partial"[..])).is_err());
    }

    #[test]
    fn stdio_health_taxonomy_and_search_use_real_local_service() {
        let configured_db = std::env::var("RESEARCHOS_DB_PATH")
            .expect("set RESEARCHOS_DB_PATH to a disposable local test database");
        assert!(Path::new(&configured_db).is_absolute());

        let health = invoke_service("health", json!({})).expect("health RPC should succeed");
        assert_eq!(health["status"], "ready");
        assert_eq!(health["offline"], true);
        assert_eq!(health["paper_count"], 0);

        let taxonomy = invoke_service("taxonomy", json!({})).expect("taxonomy RPC should succeed");
        assert_eq!(taxonomy["tags"].as_array().map(Vec::len), Some(0));

        let search = invoke_service(
            "search",
            json!({
                "query": "desktop-stdio-smoke-no-match-7f2c",
                "mode": "STRICT",
                "scope": "LOCAL_ONLY",
                "hard_filters": {
                    "eligibility": ["unknown"],
                    "review_state": ["discovered", "abstract-screened", "fulltext-indexed", "manually-verified"],
                    "facets": [],
                    "exclude_paper_ids": []
                },
                "limit": 5,
                "cursor": null
            }),
        )
        .expect("search RPC should succeed");
        assert_eq!(search["total"], 0);
        assert_eq!(search["results"].as_array().map(Vec::len), Some(0));
        assert!(search["index_version"].is_string());
    }
}
