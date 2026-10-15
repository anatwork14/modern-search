# PDF acquisition

The optional acquisition command reads the catalog SQLite database in read-only mode and writes private transfer state outside Git. It never changes catalog rows, eligibility decisions, embedding data, or source workbook files.

Install the optional parser separately from the core app environment:

```sh
python -m pip install -r backend/acquisition-requirements.txt
python -m backend.acquisition \
  --db /absolute/path/to/catalog-final.sqlite \
  --output /absolute/path/to/work/paper-transfer
```

Use `--retry-terminal` only to retry previously recorded unavailable or failed attempts. Successful records whose local PDF still matches its SHA-256 are resumed without another download. `--max-items N` bounds an initial run. Each Paper_ID has one atomically written `records/<Paper_ID>.json`; a parsed and identity-checked PDF also receives an atomically written `ready/<Paper_ID>.json` after the complete PDF has been moved into `pdfs/`. A ready record includes absolute path, SHA-256, byte size, page count, source and final URLs, fetch timestamp, parser, and identity evidence. The receiving uploader must independently recheck these values before upload.

The downloader allows three simultaneous transfers globally and one at a time per host, follows only HTTPS redirects to an allowlisted publisher host with public DNS, pins the resolved public address for each TLS-verified request, and caps each response at 64 MiB and 45 seconds. Nature's verified anonymous cookie bootstrap is a narrowly scoped exception: a request starting at an exact `www.nature.com/articles/...pdf` path may follow HTTPS redirects only between `www.nature.com` and `idp.nature.com` at `/authorize` or `/transit`, then return to that same publisher PDF path. It uses a private per-paper cookie jar, deletes it when the request ends, and does not log cookie values. No credentials, login, challenge solving, or cross-host publisher redirect is used. A source must be an exact HTTPS URL from the catalog or a deterministic PDF endpoint derived from its publisher landing URL or arXiv identifier. The resolver never searches by broad title terms. Responses must have a PDF signature, parse successfully with at least one page, and match a title in the first-page article header (before abstract/body/references). DOI and arXiv identifiers in that header can corroborate a title match, but cannot qualify a PDF alone. Generic JMLR issue mastheads are not paper identities: the resolver reads the official JMLR article page, checks its canonical title and exact PDF link, and preserves the original source title in the private transfer record when correction is required.

Paywall, 403, 429, missing-source, captcha/HTML, identity mismatch, TLS, DNS, timeout, parser, and size-limit outcomes remain visible per paper. Failed candidates never enter `ready/`. PDFs are downloaded only from listed or deterministic public endpoints; no login, paywall, CAPTCHA, or access-control bypass is attempted. Downloaded bytes and per-paper records are private user data and must stay outside the public repository.
