# ResearchOS icon and paper transfer report

**Status:** IN PROGRESS — the current Drive checkpoint is reconciled, but the catalog campaign is not complete.
**Destination:** Google Drive folder `1tUj_kTXYSAuBCXlnGNK-HpUQBfn5r7R1`
**Scope:** catalog-referenced papers, per the user's explicit instruction to follow catalog links and add verified PDFs to this same folder.

## Existing folder contents and icon

Before writing, the destination contained the catalog XLSX, catalog ZIP, `RESEARCH_NOTES.md`, `QUALITY_POLICY.md`, and `Paper collection scope.md`; no PDFs or icon were present. The scope note requests SJR Q1/Q2 journals or CORE A/A* conferences. The source files and their permissions were preserved.

The canonical local `researchos-icon.svg` was uploaded additively and read back:

| Field | Observed value |
|---|---|
| Drive ID | `1UkjXHBdFR1rA4ymw3qc9f3Fh0xkOFAgk` |
| Observed URL | https://drive.google.com/file/d/1UkjXHBdFR1rA4ymw3qc9f3Fh0xkOFAgk/view?usp=drivesdk |
| MIME type / size | `image/svg+xml` / 1,214 bytes |
| Parent | `1tUj_kTXYSAuBCXlnGNK-HpUQBfn5r7R1` |
| Local SHA-256 | `f09e132b435fd3e6347b14b3032758a77257587d21714a7247c9e3df4ba2e630` |

The Drive connector did not expose a remote raw checksum for the SVG; its observed metadata and size match the local artifact. The icon implementation itself was merged through PR #13.

## Paper transfer checkpoint — 2026-10-15

At the latest reconciled snapshot, the folder contained **157 PDFs**, the icon, and the five preserved original files. Every PDF had a valid SHA-256-keyed receipt. An independent audit confirmed 157/157 local source hashes, sizes, PDF signatures, page counts, and current first-page title-header matches. The folder listing reconciled all receipt names, Drive IDs, and sizes; successful per-file metadata readbacks additionally verified `application/pdf` and the destination parent. Google Drive's connector does not expose the uploaded raw PDF bytes or remote checksums, so receipts set `metadata_verified: true` and `hash_verified: false` for the Drive copy.

Thirty-five uploaded PDFs are JMLR papers. Twenty-three masthead-repair cases were resolved using official JMLR landing-page titles and exact PDF links; other JMLR files passed direct title-header matching. Unresolved/generic masthead titles were held. The source catalog/database and application indexes were not modified, and none of the 157 files should be treated as venue-qualified based on this transfer.

## Acquisition and quality status

The acquisition PR #14 is merged at integration commit `0f8e3f4`. At the current parsed campaign snapshot, 1,088 of 2,478 catalog candidates had records: 897 `ready`, 131 `unavailable`, and 60 `failure`. Acquisition and upload continue; later records may update these counts. `unavailable` describes the attempted endpoint responses (for example, 403/404), not a global claim that the paper cannot be obtained. Failures and unresolved sources retain their recorded reasons. The read-only source audit found 1,580 rows without a direct PDF URL and 184 JMLR masthead-prefix titles, 151 without an article-title tail in the catalog value. ZIP inspection found no full-text PDFs.

SJR/CORE qualification is separate from PDF identity and Drive transfer. The source scope note's rank filter has not been independently validated or applied to the database. No qualification values were promoted; do not infer scientific quality or qualification from PDF availability.

## Checkpoint counts

| Outcome | Count / status |
|---|---:|
| PDFs uploaded and reconciled to receipts | 157 |
| Local PDF hash/size/signature/page/title recheck | 157 / 157 PASS |
| Drive name/ID/size receipt reconciliation | 157 / 157 PASS |
| Remote raw PDF checksums exposed | 0 |
| Catalog candidates | 2,478 |
| Parsed acquisition records at snapshot | 1,088 (897 ready, 131 unavailable, 60 failure) |
| Terminal all-paper manifest | Pending; campaign in progress |

Per-hash receipts and paper-level acquisition records remain in the private task work area, not Git. The final aggregate manifest must include every catalog Paper_ID and its actual result, including not-yet-retrieved, unresolved, unavailable-at-attempted-endpoints, and failure cases; upload it to this same Drive folder only after terminal reconciliation. This checkpoint makes no claim that the full catalog has been acquired.
