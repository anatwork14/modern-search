# Read-only Paper_ID lookup v1 for research workspace

**Branch implementation:** `feat/research-workspace-readonly-paper-lookup-20261016`. Adds `get_paper` to the existing **local stdio JSON v1** bridge; not a web API, not an evidence API, and no new services.

## Request
```json
{"version":1,"id":"paper-lookup-01","command":"get_paper","payload":{"paper_id":"P-from-catalog"}}
```
The paper ID must be nonempty string length <=128 without controls, no extra payload keys.

## Response
```json
{"version":1,"id":"paper-lookup-01","ok":true,"data":{"found":false,"paper":null,"evidence_state":"catalog-metadata-only","warnings":["Catalog metadata and source assertions are not verified full-text/page-level evidence"]}}
```
On found, `paper` is the existing exported structured catalog record, including paper_id, title/abstract if actually present, source_url, authors, year, DOI, review_state, pdf_state, tags (with review status/role), eligibility and venue evidence. **No invented PDF content or page anchors.** Unknown IDs return found:false, not a fabricated record.

## Contract boundaries
- Follows existing request-size limits, error-envelope convention, local database permissions and one-request-per-process behavior. Not an HTTP/MCP method.
- Unsupported/malformed commands fail before database creation. A valid command may invoke existing schema migrations; read-only here means it does not mutate paper source records or allow arbitrary queries/paths.
- Must not promote `source_asserted` provenance to independently verified venue/rank or full text.
- Does not claim full-text `get_evidence` or semantic evidence access.
- Future performance improvement should replace the all-paper export for ID lookups with a parameterized indexed single-paper query, benchmarked for performance and consistency.

## Consumer (research repository)
`researchctl paper P-ID` may use this command if installed. Consumers must feature-detect failure rather than assuming every modern-search version supports this.

## Implementation efficiency

The new `get_paper` dispatch calls a parameterized indexed SQLite Paper_ID lookup and only serializes the matching paper's tags, identifiers and venue assertion rows; it does not perform the full-corpus `export_papers` scan required for search. List and lookup share the same serialization helper to prevent schema drift. Latency is NOT benchmarked until a realistic catalog is available.

## Runtime capability discovery (latest branch)

`health` now includes `capabilities: [health, search, taxonomy, get_paper]` and `fulltext_page_evidence: false`. The count uses an SQLite row count rather than serializing every paper; `taxonomy` exports only the tag table. The desktop `HealthData` contract declares these fields optional for backward compatibility. An older backend lacking them must not be presumed to support `get_paper`.

**CI:** [GitHub Actions run 38862245515](https://github.com/anatwork14/modern-search/actions/runs/38862245515) completed successfully for commit `429df4face784b1b161492d7c7602126732ebf11` (desktop, Python contracts, acquisition).
