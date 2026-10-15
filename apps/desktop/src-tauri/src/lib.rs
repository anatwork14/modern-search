use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::io::{Read, Write};
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;
use tauri::Manager;
use wait_timeout::ChildExt;

const SERVICE_TIMEOUT: Duration = Duration::from_secs(30);
const MAX_RESPONSE_BYTES: u64 = 8 * 1024 * 1024;

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

fn repository_root() -> Result<std::path::PathBuf, String> {
    // src-tauri lives at <repo>/apps/desktop/src-tauri. In a packaged build,
    // resources must be bundled explicitly; never accept a path from the UI.
    if !cfg!(debug_assertions) {
        return Err("The local service is not bundled in this development build.".into());
    }
    let manifest = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest
        .parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .ok_or_else(|| "Could not locate the application source root.".to_string())?;
    if !root.join("backend").is_dir() {
        return Err("The local search service is not available in this checkout yet.".into());
    }
    Ok(root.to_path_buf())
}

fn invoke_service(command_name: &str, payload: Value) -> Result<Value, RpcError> {
    let root = repository_root().map_err(|message| RpcError {
        code: "INTERNAL_ERROR".into(),
        message,
    })?;
    let request = RpcRequest {
        version: 1,
        id: format!("desktop-{}", uuid()),
        command: command_name.to_string(),
        payload,
    };
    let request_bytes = serde_json::to_vec(&request).map_err(|_| RpcError {
        code: "INTERNAL_ERROR".into(),
        message: "Could not encode the local search request.".into(),
    })?;
    let python = std::env::var("MODERN_SEARCH_PYTHON").unwrap_or_else(|_| "python3".into());
    let mut child = Command::new(python)
        .arg("-m")
        .arg("backend.service")
        .current_dir(&root)
        .env("PYTHONPATH", &root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "Could not start the local search service. Check Python 3.11+ is installed.".into(),
        })?;
    let Some(stdout) = child.stdout.take() else {
        let _ = child.kill();
        let _ = child.wait();
        return Err(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "Could not open the local service response channel.".into(),
        });
    };
    let stdout_reader = thread::spawn(move || {
        let mut bytes = Vec::new();
        let mut buffer = [0; 8192];
        let mut exceeded_limit = false;
        let mut stdout = stdout;
        loop {
            let count = stdout.read(&mut buffer)?;
            if count == 0 {
                break;
            }
            let remaining = MAX_RESPONSE_BYTES.saturating_sub(bytes.len() as u64) as usize;
            let retained = count.min(remaining);
            bytes.extend_from_slice(&buffer[..retained]);
            exceeded_limit |= retained < count;
        }
        Ok::<_, std::io::Error>((bytes, exceeded_limit))
    });
    let Some(mut stdin) = child.stdin.take() else {
        let _ = child.kill();
        let _ = child.wait();
        let _ = stdout_reader.join();
        return Err(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "Could not open the local service request channel.".into(),
        });
    };
    if stdin.write_all(&request_bytes).and_then(|()| stdin.write_all(b"\n")).is_err() {
        drop(stdin);
        let _ = child.kill();
        let _ = child.wait();
        let _ = stdout_reader.join();
        return Err(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "Could not send the local search request.".into(),
        });
    }
    drop(stdin);

    let status = match child.wait_timeout(SERVICE_TIMEOUT) {
        Ok(Some(status)) => status,
        Ok(None) => {
            let _ = child.kill();
            let _ = child.wait();
            let _ = stdout_reader.join();
            return Err(RpcError {
                code: "INTERNAL_ERROR".into(),
                message: "The local search service timed out after 30 seconds.".into(),
            });
        }
        Err(_) => {
            let _ = child.kill();
            let _ = child.wait();
            let _ = stdout_reader.join();
            return Err(RpcError {
                code: "INTERNAL_ERROR".into(),
                message: "Could not wait for the local search service.".into(),
            });
        }
    };
    let (response_bytes, response_exceeded_limit) = stdout_reader.join().map_err(|_| RpcError {
        code: "INTERNAL_ERROR".into(),
        message: "The local search response channel failed.".into(),
    })?.map_err(|_| RpcError {
        code: "INTERNAL_ERROR".into(),
        message: "Could not read the local search response.".into(),
    })?;
    if response_exceeded_limit {
        return Err(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "The local search service response exceeded the size limit.".into(),
        });
    }
    if !status.success() {
        return Err(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "The local search service exited unexpectedly.".into(),
        });
    }
    let response: RpcResponse = serde_json::from_slice(&response_bytes).map_err(|_| RpcError {
        code: "INTERNAL_ERROR".into(),
        message: "The local search service returned an invalid response.".into(),
    })?;
    if response.version != 1 || response.id != request.id {
        return Err(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "The local search service returned a mismatched response.".into(),
        });
    }
    if response.ok {
        Ok(response.data.unwrap_or(Value::Null))
    } else {
        Err(response.error.unwrap_or(RpcError {
            code: "INTERNAL_ERROR".into(),
            message: "The local search service could not complete the request.".into(),
        }))
    }
}

fn uuid() -> String {
    // Request IDs are correlation labels, not credentials or authorization tokens.
    format!("{}-{}", std::process::id(), std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos())
}

#[tauri::command]
fn service_health() -> Result<Value, RpcError> {
    invoke_service("health", Value::Object(Default::default()))
}

#[tauri::command]
fn search(request: Value) -> Result<Value, RpcError> {
    invoke_service("search", request)
}

#[tauri::command]
fn taxonomy() -> Result<Value, RpcError> {
    invoke_service("taxonomy", Value::Object(Default::default()))
}

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![service_health, search, taxonomy])
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                window.set_title("ResearchOS")?;
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running ResearchOS desktop");
}
