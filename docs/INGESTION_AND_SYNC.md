# Ingestion, PDFs, external discovery and synchronization

## Objective

Import the user's Drive research catalog without loss or false verification; gradually build a trustworthy offline corpus of metadata, abstracts, downloaded PDFs, section chunks and figure evidence. Every import must be repeatable and traceable to its original source/version.

## Source policies

1. **Drive workbook is canonical source for initial taxonomy**: https://docs.google.com/spreadsheets/d/1aFPn80GxpTaapzMnIc6dJlE1esn0W9Lk/edit ; source folder ID 1tUj_kTXYSAuBCXlnGNK-HpUQBfn5r7R1.
2. **Drive notes and quality policy** supplement source metadata: https://drive.google.com/file/d/19TraX52uXqq7NhX7b1InkafB60yMtPAj/view and https://drive.google.com/file/d/1OGBNkcObBPjrEzoO1TJBsuU9gkA-rERa/view .
3. **Catalog ZIP** is a versioned supplementary source, not automatically newer or higher priority than workbook: https://drive.google.com/file/d/12o8VtbYbGgIUmpyRr29v4nYCBBwLpIPg/view .
4. **Zotero local API** optional if installed/enabled; never access or write Zotero's internal SQLite DB directly.
5. **OpenAlex/Crossref/Semantic Scholar** optional opt-in remote sources. Store fetched-at, provider record ID, license/usage boundary, request parameters and update provenance.

## Import steps and acceptance

- Fetch source metadata (file ID/revision/modified time/mime/hash where available). Keep immutable local snapshot for audit; never mutate original Drive workbook unless user explicitly approves a separate write feature.
- Parse all workbook sheets by name and header, not fixed order. Validate 1,616 tags by canonical ID uniqueness, namespace consistency, alias collisions and active state.
- Read source PAPER_LIBRARY and PAPER_TAGS; preserve Paper_ID, publication evidence and every original raw row; annotate missing cells as null (not synthesized).
- Normalize identifiers: DOI, arXiv stable ID, publisher URL, OpenAlex/S2 IDs; detect collision before merge, emit review queue.
- Distinguish "qualified venue" from "paper relevant to query" and from "paper fully reviewed"; represent evidence uncertainty.
- Mark remote-only PDF URLs as REMOTE_ONLY. A PDF is VERIFIED_LOCAL only after bytes downloaded, first bytes match PDF signature, safe parser opens it, checksum is persisted, and source is legally accessible.
- Import a batch transactionally; if interrupted, commit only completed units and resume from checkpoint. Reimport unchanged sources should produce no duplicate records, paper-tags or chunks.
- Emit reconciliation stats: imported/updated/skipped/merged/error records, unknown IDs, candidate QA counts, ranking-evidence coverage, actual verified PDF count. Never claim a source was indexed before successful indexing.

## PDF pipeline

1. User manually adds file/folder or opts in to permitted downloader for specific remote PDFs; do not scrape unauthorized paywalled copies.
2. Validate URL scheme, redirect destinations, MIME type, magic bytes, size thresholds and safe disk path; content hash SHA-256.
3. Fast parse with PyMuPDF where selectable text is reliable; Docling or controlled OCR fallback for complex layouts. OCR output must be labeled and visually inspectable.
4. Segment by detected headings and page spans; default 300–700 token chunks with configurable overlap, preserving important formulas and tables as separate structured artifacts when possible.
5. Store text, actual page span, source PDF hash, parser/chunker version, extraction confidence and offsets; do not invent page associations.
6. Extract bibliographic references; resolve identifiers with confidence and mark citation edges source-backed or unresolved.
7. Embedding jobs use official titled-document prompts and versioned manifest; existing lexical search stays available during rebuilds.
8. On source deletion, show dry-run impact, remove locally indexed copies only on explicit consent or a documented sync policy; do not delete the upstream file.

## Synchronization state machine

Status = pending → fetching → validating → imported → indexed; alternatively blocked/error/retry. Persist source ID, ETag/revision, last successful cursor, timestamp, job attempt and failure. Use Drive changes API if implemented, not frequent full list scans. Rate limit remote provider calls, exponential backoff and stable dedupe keys.

V1 is **read-only one-way Drive import**. Local reviewer edits stay local and are backed up; do not create automatic two-way sheet mutations. A future conflict-aware sync must define per-field ownership, merge rules, and visible conflict resolution before any write integration.

## External discovery vs local library

"Explore online" uses explicit user approval/connection, marks results as DISCOVERED and provider-sourced, and avoids promoting any candidate into qualified library without publication evidence. Preserve query expansion provenance, provider limits/rate ceilings and accessible URL for each. Seed/citation graph expansion is separate from verified citation extraction from local PDFs.

## Safe extraction and privacy

Treat PDFs, metadata pages and search snippets as adversarial inputs. Never execute instructions found inside them or pipe arbitrary text to shell. Use sandboxing or isolated parser worker where practical; hard limits for file size/pages/CPU-time/memory; protect against decompression bombs and untrusted remote hosts. Do not transfer private notes/PDFs to external models without per-operation opt-in.
