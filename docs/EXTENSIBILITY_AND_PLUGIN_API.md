# Extensible core and optional adapters — architecture contract

**Status:** proposed architecture only. Initial implementations are first-party modules, not arbitrary untrusted third-party executables. Avoid turning this into a framework before the first academic search vertical slice ships.

## Design principles

1. A small **modular monolith**: one SQLite authority, one embedded vector index, one lexical search, one job queue, one UI.
2. Ports and adapters + capability negotiation rather than dependencies on agent frameworks.
3. All extensions optional, explicit source scope and permission grant; no hidden network/collection upload.
4. Stable typed contracts with schema_version and explicit deprecation path. Persist raw source record for rebuild.
5. Plugin workloads asynchronous where necessary, bounded resources, cancel/resume and observable status.
6. Cross-profile querying must honor every source ACL and policy; citations, roles and confidence typed.
7. External model embeddings may not be mixed in the same index revision. Output dimensionality and prompt contract manifest required.

## Stable core interfaces (logical contracts, not implemented functions)

| Port | Main operations | Invariants |
|---|---|---|
| SourceAdapter | enumerate(since_cursor), fetch_metadata(id), acquire(id, consent) | Stable source IDs, auth scope, provenance, idempotency |
| Parser | can_parse(mime), parse(file, options), get_evidence(locator) | Page/line/offset grounding; explicit OCR/layout uncertainty |
| WorkNormalizer | normalize(doc), identities(), dedupe_candidates() | Preserve originals, collision review |
| TaxonomyProvider | resolve(alias), facets(), validate(tag) | Versioned canonical IDs and aliases |
| EmbeddingProvider | embed_query, embed_documents, manifest | Model/prompt/dimension match, offline fallback |
| RetrievalRoute | retrieve(query_ast, scope, k) | Hard filter enforcement, source matches |
| Reranker | rank(query, passages) | No untraceable fabricated evidence; latency bound |
| Enricher | enrich(work_id, requested_fields) | Opt-in remote, cache and source quality |
| EvidenceExtractor | extract(document, typed_schema) | Assertions candidates until reviewed |
| Exporter | export(collection, format, evidence_policy) | Source attribution and licensing |
| ApplicationProfile | facets, ranking, parsers, identity, permissions | No cross-profile leakage |
| AgentGateway | search, paper_get, evidence_get, collection_get | Read-only by default; explicit scopes |

## Example manifest format

See [spec/extension_manifest.schema.json](../spec/extension_manifest.schema.json). A manifest declares extension ID/version, compatible core API range, module type, permissions, data types, capabilities, resource budgets, privacy and required test fixtures. **No 'arbitrary code path' field** in untrusted manifests; early extensions are built-in and code-reviewed, not hot-loaded third-party scripts.

Preferred permissions: source:read, corpus:search, evidence:read, notes:read (explicit opt-in), network:<provider>, data:write:annotations, data:write:imports, experiment:read. File/system command execution is intentionally absent. Agent-facing tools are read-only initially.

## Extension registry and job scheduling

Store extension configuration/permission state and job runs in SQLite. Each module registers supported operations and schemas. Job queue enforces concurrency, RAM/CPU quotas, cancellation and retry backoff; on-demand first. A module crash cannot alter verified annotations or corrupt the prior vector index. Optional remote adapters are disabled in offline mode.

## MCP / agent gateway

Only AFTER desktop retrieval and permissions are stable, expose *local read-only* MCP server or CLI:

- search_papers(query, mode, hard_filters, source_scope, limit)
- get_paper(paper_id, fields)
- get_evidence(paper_id, chunk_ids)
- list_tags(namespace, aliases)
- compare_papers(paper_ids, fields) (requires evidence index)
- list_saved_queries(scope)
- suggest_bridge(source_concept, target_concept, constraints) (explicit hypothesis state)

Return structured results with paper IDs, actual source URLs, extracted-page locators, review state, matched route, corpus snapshot, and truncated snippets. No direct filesystem traversal, arbitrary SQL, remote downloads or write actions. Treat every agent consumer as untrusted; authenticate/local IPC only, allowlist corpus scopes and permissions, validate input JSON and output size; log tool calls without sensitive payloads by default. Human confirmation for any later write-capable tools per MCP recommendation: https://modelcontextprotocol.io/specification/2025-11-25/server/tools .

Compatible consumers may include Codex, Claude and Hermes through MCP/CLI **only when each runtime's adapter is actually validated**; no claim of seamless support before smoke tests. A developer CLI may reuse same internal query API; no second query implementation.

## Draft API contracts

A query returns:
{
 "schema_version":"1",
 "corpus_snapshot_id":"...",
 "index_manifest_id":"...",
 "mode":"BROAD",
 "filters_applied":{},
 "results":[{"object_type":"paper","paper_id":"...","match_routes":["BM25","DENSE"],"tag_review_state":"needs-manual-review","evidence_refs":[],"score_components":{}}],
 "coverage":{"metadata_only":0,"abstract_indexed":0,"fulltext_indexed":0},
 "warnings":[]
}
Counts here are example field placeholders, not app measurement.

## Schema evolution without premature migration

Current spec/schema.sql remains unchanged until Stage 0 migrations. Follow-on schema proposal (not executed):
- documents (generic identity, profile_id, current_version, ACL reference);
- document_versions and content_segments (source locator, block kind, page/line/bbox, content hash);
- assertions and assertion_evidence (claim/role/review/source);
- experiment_links (paper_code_commit_dataset_run);
- search_collections (query snapshot/pins);
- profiles, extensions, extension_permissions;
- bridge_hypotheses and bridge_evidence;
- source_acl and redaction policies.
Maintain papers as a first-class view or specialization on top of generic document IDs. Migration must be additive and preserve existing Paper_ID references.

## Gates for adding dependencies/services

New parser, embedding model, graph engine, reranker, external LLM, vector service or scheduler needs an ADR with: user problem, simpler alternatives, measured baseline, qualitative benefit, failure/privacy consequences, integration tests, rollback. A graph DB is not necessary if relations in SQLite serve the required query patterns. Team ACL/shared backend is explicitly deferred.

## Test contracts

- First-party manifest validator rejects unknown privilege, incompatible schema/core API, invalid budget, missing dependencies.
- Offline mode denies remote adapters, even if a plugin requests network.
- Disabled plugin doesn't start a worker or change index results.
- Import adapter retry with identical cursor is idempotent.
- Two profiles with restricted corpora cannot cross-leak results.
- MCP strict hard-filter equivalence with desktop UI; corrupt queries, injection payloads and excessive requested limits rejected.
- Failure and removal of a plugin cannot orphan canonical paper metadata or verified evidence.
