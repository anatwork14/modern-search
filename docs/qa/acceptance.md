# Local acceptance gates

Run Python suites by directory because standard-library `unittest` does not
recursively find all nested suites from the repository root:

```sh
python3.11 -m pip install 'jsonschema==4.26.0'
python3.11 -m unittest discover -s tests/contracts -v
python3.11 -m unittest discover -s tests/data -v
python3.11 -m unittest discover -s tests/embeddings -v
python3.11 -m unittest discover -s tests/retrieval -v
python3.11 -m unittest discover -s tests/security -v
python3.11 -m unittest discover -s tests/integration -v
```

The quality branch must be rebased or fast-forwarded onto the integration
branch after the owned backend and desktop changes are accepted. These commands
are mandatory and fail when their source directories or imported modules are
missing; missing dependencies are not treated as a passing skip.

## Desktop and native checks

With Node 22 and Rust installed:

```sh
cd apps/desktop
npm ci
npm test
npm run lint
npm run build
cd src-tauri
cargo test --locked
cargo check --locked
```

Then run `npm run tauri dev` from `apps/desktop` on the target macOS machine.
Confirm the window opens, `Local service` health is shown, a local query returns
only the fixture catalog, closing the window exits the child process, and no
listening socket is created. Record each item as `PASS`, `FAIL`, or `NOT RUN`
with the exact host and command. Browser preview, compilation, and mock data do
not prove this native smoke gate.

The current desktop bridge has no release-bundled Python service or database
resources. A release build must not be described as searchable until a bundle
layout, resource resolution, and packaged smoke test are implemented and
executed. The local encoder and exact-cosine index have passed CPU and Apple
MPS compatibility checks on the pinned checkpoint; this establishes loading,
prompt, shape, and normalization compatibility, not semantic ranking quality.
Keep benchmark judgments marked `NOT RUN` until a human-reviewed labeled query
set is evaluated. See `docs/qa/benchmark-protocol.md` for the required protocol.
