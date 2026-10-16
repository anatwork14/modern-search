# Independent paper-acquisition review

**Status:** IN PROGRESS — acquisition and additive Drive transfer are still running. This is a reconciled checkpoint, not campaign completion.
**Reviewer:** upload and QA worker
**Acquisition implementation:** PR #14 merged at integration commit `0f8e3f4`; validator source SHA-256 `caa99d9c0173d816e224cb7c556abbc2dc251a875710dfb340862ef3f20d00d1`.

## Review gate

The uploader independently checks each ready record's stable Paper_ID, local path, PDF signature, byte size, SHA-256, successful parse/page count, and title evidence in the first-page article header. The header comparison applies Unicode NFKC normalization and stops before the abstract/body/references. Catalog identifiers can corroborate a title match; DOI/arXiv mentions, PDF metadata, references, or a body-only title do not qualify a file. JMLR issue mastheads are held unless the article title is matched to the official landing page and exact PDF link.

Before upload, the destination is checked for an existing stable Paper_ID filename and hash receipt. Successful uploads are read back by observed Drive ID; name, MIME type, exact size and destination parent must match before an atomic per-hash receipt is written. Existing files are never overwritten, moved, or deleted. When Drive does not expose downloaded bytes or a remote checksum, the receipt records metadata/size verification and leaves remote hash verification false.

## Current transfer checkpoint — 2026-10-15

The latest folder listing contained **157 catalog-linked PDFs** and the uploaded icon, alongside all five original catalog/scope files. The private receipt ledger contained 157 valid JSON receipts. An independent full-ledger pass reopened all 157 local PDF files and verified local SHA-256, size, PDF signature, page count, and first-page title-header identity against the current ready record or recorded title evidence. A fresh listing reconciled every receipt to the observed Drive name, ID, size and MIME type; the receipt also records the successful metadata readback for the target parent. The independent snapshot reported 157/157 passing, with no missing local bytes, JSON errors, folder/receipt conflicts, or unreceipted folder PDFs. The connector does not expose remote PDF bytes or a content checksum; remote hash verification is therefore unavailable.

Of the 157 transfers, 35 are JMLR papers. Twenty-three used an official JMLR landing-page title and exact PDF-link resolution because the source catalog value included an issue masthead; the other JMLR records matched their actual catalog titles directly against the PDF header. Generic, fused-masthead, or otherwise unresolved identities remain excluded. Eleven transferred papers currently resolve through the bounded public Nature anonymous-cookie bootstrap; this flow uses only a private ephemeral cookie jar, restricts the redirect hosts and paths, and has no login or challenge bypass.

The source qualification rule remains independent: SJR Q1/Q2 journals or CORE A/A* conferences. This transfer does not certify venue rank or scientific quality. The Drive PDFs are additive external files; the application catalog, SQLite database, indexes, and qualification values remain unchanged.

## Acquisition status at the checkpoint

The acquisition worker's latest parsed snapshot had 1,088 catalog records: 897 ready, 131 marked `unavailable`, and 60 marked `failure`, out of 2,478 catalog candidates. The campaign was still running and later ready files may supersede this snapshot. `unavailable` means the attempted endpoints returned blocking or missing responses such as HTTP 403/404; it does not prove that a paper is globally unavailable. `failure` preserves the specific pipeline error. Any remaining or `needs_resolution` rows still require explicit terminal results before the all-paper manifest can be finalized.

The read-only catalog audit found 1,580 records with no direct PDF URL and 184 JMLR masthead-prefix titles, including 151 without an article-title tail in the catalog value. These are catalog-quality limits, not reasons to invent identities or qualify papers. The ZIP archive contained no full-text PDF set. The source catalog and app database have not been changed.

## Acquisition validator review and tests

Independent code review of the merged validator found no blocking issue in the HTTPS-only redirect handling, allowlisted-host DNS pinning, bounded retries/time/size, current-identity revalidation of cached ready files, JMLR exact-link resolution, or scoped Nature bootstrap. The validator's first-page title identity gate rejects DOI/arXiv/reference-only false positives and metadata-only titles.

Executed checks:

- `python3 -m unittest discover -s tests/acquisition -p 'test_acquisition.py' -v` — PASS, 32 tests against validator SHA `caa99d9c0173d816e224cb7c556abbc2dc251a875710dfb340862ef3f20d00d1`.
- `python3 -m unittest discover -s tests/data -v` — PASS, 15 existing core data tests.
- Private synthetic identity fixture runner with `--expected-sha256 caa99d9c0173d816e224cb7c556abbc2dc251a875710dfb340862ef3f20d00d1` — PASS, 11/11 cases.
- `python3 -m unittest discover -s tests/acquisition -v` on this follow-up branch — PASS, 36 tests, including four independent DNS/URL-boundary cases.

The separate hosted acquisition CI job is added in this follow-up so the optional pinned PyMuPDF dependency and acquisition tests remain isolated from the core offline Python job.
