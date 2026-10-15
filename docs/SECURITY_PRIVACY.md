# Security, privacy, source integrity and threat model

## Assets and boundaries

Sensitive assets: private PDFs, local annotations, search history, OAuth credentials, remote-provider tokens, SQLite data, Zotero attachments, model files, external download cache. Trusted components: signed desktop app and intentionally installed dependencies. Untrusted inputs: PDFs, OCR text, abstracts, publisher HTML, metadata, tagged aliases, GitHub repos and external model responses.

## Baseline commitments

- Offline-first: local query and index do not require network after explicit model and data acquisition. Online discovery is opt-in and visible.
- No cloud LLM or external telemetry receives local queries/documents/notes by default.
- OS Keychain for OAuth/API secrets. Avoid logging headers, tokens, private filenames/notes when possible; provide redaction and log export controls.
- Minimize Google permissions to read-only scoped resources for V1. No two-way editing or automatic backup upload by default.
- SQLite and index stored under OS app-data directory; prevent symlink traversal, path injection and broad filesystem access.
- Restrict local sidecar to authenticated loopback/stdio IPC, forbid wildcard binding and unsafe CORS; validate message schemas and maximum payloads.
- Treat all retrieved text as data, **never instructions**. Do not execute a paper's README, arbitrary shell snippets or model-suggested package install during import.
- Parsing: size/page/time limits, safe subprocess isolation, PDF format+magic check, ZIP bomb defenses, file type allowlists and error visibility.
- Remote requests: https URLs by default; defend against localhost/internal-address SSRF and redirects when user imports a URL; respect robots/ToS/provider limits and licensing.
- Artifacts: hash downloads, track provenance, allow user-directed deletion, protect backup encryption keys. No redistribution of PDFs without permission.
- Before running model weights, evaluate provenance, checkpoint pinning and unsafe serialization paths; favor safetensors and library-supported safe loading.
- Dependencies pinned/locked; audit supply chain, licenses, vulnerability status and dependency updates with CI.
- GitHub repository is public: no private Drive contents, PDFs, personally sensitive notes or credentials may be committed.

## Trust-sensitive correctness

Misrepresentation is also a product security issue:
- Candidate lexical matches must not become trusted method-use claims.
- No unverified venue rank or publication evidence presented as confirmed.
- No citation graph edges without provider/extracted support.
- No invented page or snippet; citations require stored source, hash and exact page/extraction offsets.
- If online AI query expansion is implemented later, require user opt-in before sending query text outside the machine.

## Privacy settings

One screen shows: offline mode, sources connected, network permissions by provider, local storage size, model cache, log retention, imported attachments, backup/export, remove/delete workflow. Deleting an index does not necessarily delete an original PDF; user can specify each operation.

## Required tests

- Malicious PDF with prompt-injection wording does not cause tool invocation or network activity.
- Fake DOI, PDF HTML response, malformed archive and duplicate paths cannot corrupt main DB.
- Sidecar denies unauthenticated cross-origin/remote requests.
- API credential not exposed in logs, UI snapshots, crash reports or repo.
- Queries in offline mode emit no external request; model loads from local cache.
- Version/revision mismatches cannot route queries to incompatible embeddings.
