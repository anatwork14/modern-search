# MVP integration agreement v1

Lead owns this document, spec/ipc-v1.schema.json, backend/service.py, root Python package configuration and progress.md. Workers ACK via agent message before implementation; propose changes to lead. Python 3.11+, standard library unittest baseline; modules import from repository root as backend.*. No shared backend/__init__.py edits. Heavy model jobs reserved for C alone.

- A (#2) owns backend/persistence/, backend/ingest/, tests/data/, docs/audits/. Expose connect(path), migrate(connection), import_catalog(connection, catalog, source_id, source_revision), export_papers(connection), export_tags(connection). Catalog JSON has tags, papers, paper_tags arrays. Export dictionaries; report schema before freezing it. Workbook adapter maps actual headers after audit. Never publish private source contents.
- B (#3) owns apps/desktop/ including nested src-tauri, its package/lockfiles and UI tests. Tauri invokes Python using stdio, no listening server. Root/backend service integration belongs to lead. Desktop can begin with explicit mock mode, then switch to service. Send one JSON request per process stdin and receive one JSON response stdout. Python executable defaults python3, configurable locally. Arguments use an argv array, never a shell. Service path must be anchored to repository/application resources, no renderer-supplied executable/path. Native packaging can remain a declared blocker until bundle resources validated.
- C (#4) owns backend/embeddings/, backend/vector/, tests/embeddings/, docs/benchmarks/. Expose encode_query(text), encode_titled_documents([{title,text}]), model_manifest(); typed unavailable failure. No automatic network/download at search time. Manifest records exact checkpoint/revision/tokenizer/prompt_version/dimension/normalized/corpus_revision. Model absence preserves lexical search. Verify official model claims before loading.
- D (#5) owns backend/retrieval/, tests/retrieval/. Expose search(papers, tags, request, dense=None) returning response data. Implement pure independent fixtures first; coordinate export dictionary with A. Exact ANY/ALL/NOT within facets, AND across facets, unknown tags rejected, zero remains zero. Parameterized SQL if used. Pagination is offset encoded as decimal cursor, bound to request/index fingerprint before release; deterministic paper_id ties.
- E (#6) owns .github/workflows/, tests/contracts/, tests/security/, docs/qa/. Independent acceptance and negative fixtures; do not edit runtime modules. Lead owns root .gitignore and test package glue.

## Wire request

`{"version":1,"id":"request-id","command":"health|search|taxonomy","payload":{}}`.
Search payload: query string; mode STRICT or BROAD (BRIDGE rejected until implemented); scope LOCAL_ONLY; hard_filters {eligibility:[],review_state:[],facets:[{namespace,operator:ANY|ALL|NOT,tags:[],review_state?:verified|needs-manual-review}],exclude_paper_ids:[]}; limit 1..100 default 20; cursor null or opaque string. Default eligibility [verified-qualified]; exploratory must be explicitly selected. Empty query permitted for filter browsing. No SQL or filesystem paths accepted from renderer.

## Wire response

`{"version":1,"id":"request-id","ok":true,"data":{...}}` or `{"version":1,"id":"request-id","ok":false,"error":{"code":"INVALID_REQUEST|MODEL_UNAVAILABLE|INDEX_MISMATCH|INTERNAL_ERROR","message":"safe text"}}`.
Search data: results array, total integer, next_cursor nullable, index_version string, dense_status unavailable|ready, warnings array. Each result carries paper_id, title, abstract nullable, authors array, year nullable, doi nullable, source_url nullable, review_state, eligibility, tags array of {tag_id,review_state,role}, pdf_state REMOTE_ONLY|UNAVAILABLE|VERIFIED_LOCAL, match_routes array, score number. Metadata/abstract matches never yield invented pages or fulltext verification. Source URLs restricted to https/http safe rendering; renderer uses text escaping.

Tag dictionary: [{tag_id,namespace,label,aliases:[]}]. Paper review_state uses discovered|abstract-screened|fulltext-indexed|manually-verified|experiment-reproduced. Tag review_state uses needs-manual-review|verified|rejected. Paper IDs and canonical namespaced tag IDs preserve source identity; no silent alias collision merge. Revision and provenance retained in SQLite even when UI omits raw source rows.

## Integration gates

Each worker supplies executed test commands, commit and PR targeting integration/researchos-mvp. Lead reviews and reruns tests before merging. No main merge or release implied. Drive audit and native launch are separate gates from synthetic fixture tests. Private archives, model weights and databases stay outside Git.

## Implemented additive metadata and host configuration

Paper exports retain `identifiers: list[str]` and add identifier provenance records, `venue`, and source-asserted `venue_evidence`. UI venue assertions do not confer qualification. The host alone selects `RESEARCHOS_DB_PATH`, optional `RESEARCHOS_INDEX_PATH`, and `MODERN_SEARCH_PYTHON`; renderer requests cannot supply them. An index is tied to the complete exported corpus digest, so metadata refresh may require rebuilding it. BROAD dense enumeration covers the whole small catalog before strict filtering; semantic candidate count is not a relevance metric. One model reservation at a time applies to all workers.
