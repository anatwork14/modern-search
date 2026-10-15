"""Resumable, provenance-preserving acquisition of catalog-linked PDFs.

The downloader does not mutate the catalog. Each paper gets an atomic private
record; only a parsed, identity-matched PDF gets a ready/<Paper_ID>.json file.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
import os
import re
import shutil
import sqlite3
import socket
import tempfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import fitz

MAX_PDF_BYTES = 64 * 1024 * 1024
MIN_FREE_BYTES = 5 * 1024 * 1024 * 1024
TOTAL_WORKERS = 3
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 45
DNS_TIMEOUT_SECONDS = 8
USER_AGENT = "ResearchOS-PaperAcquisition/1.0 (local user-directed transfer)"
_PUBLIC_IP_CACHE: dict[str, str] = {}
ALLOWED_HOSTS = {
    "raw.githubusercontent.com", "proceedings.mlr.press", "aclanthology.org",
    "arxiv.org", "www.arxiv.org", "proceedings.neurips.cc", "papers.nips.cc",
    "jmlr.org", "www.jmlr.org", "www.nature.com", "link.springer.com",
}


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_text(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _doi(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"10\.\d{4,9}/[^\s<>\]})]+", value, re.I)
    return match.group(0).rstrip(".,;:").casefold() if match else None


def _arxiv(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(?:arxiv\s*:\s*)?(\d{4}\.\d{4,5}(?:v\d+)?)", value, re.I)
    return match.group(1).casefold() if match else None


def _arxiv_base(value: str | None) -> str | None:
    normalized = _arxiv(value)
    return re.sub(r"v\d+$", "", normalized) if normalized else None


def _is_generic_title(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized.startswith("journal of machine learning research ") or normalized in {"untitled", "manuscript", "preprint"}


def _identity_check(path: Path, paper: dict[str, Any]) -> dict[str, Any]:
    with path.open("rb") as stream:
        signature = stream.read(4096)
        if not signature.startswith(b"%PDF-"):
            if re.search(rb"<(?:!doctype\s+html|html|form)\b", signature, re.I):
                raise ValueError("html_or_captcha_response")
            raise ValueError("invalid_pdf_magic")
    doc = fitz.open(path)
    try:
        if doc.is_encrypted and not doc.authenticate(""):
            raise ValueError("encrypted_pdf")
        if doc.page_count < 1:
            raise ValueError("pdf_has_no_pages")
        first_page = doc.load_page(0).get_text()
        header_text = _article_header(first_page)
        expected_doi = _doi(paper.get("doi"))
        expected_arxiv = _arxiv_base(paper.get("arxiv_id"))
        if _is_generic_title(paper["title"]):
            raise ValueError("identity_catalog_title_is_generic")
        identity_title = _identity_title(paper)
        expected_title = _normalize_text(identity_title)
        candidates = _title_windows(header_text[:2400])
        scored = [(SequenceMatcher(None, expected_title, candidate).ratio(), candidate) for candidate in candidates if candidate]
        score, best_candidate = max(scored, default=(0.0, ""))
        expected_tokens = set(expected_title.split())
        candidate_tokens = set(best_candidate.split())
        token_recall = len(expected_tokens & candidate_tokens) / max(1, len(expected_tokens))
        token_precision = len(expected_tokens & candidate_tokens) / max(1, len(candidate_tokens))
        header_normalized = _normalize_text(header_text)
        # IDs corroborate title identity; they never qualify a PDF alone.
        header_dois = {_doi(match) for match in re.findall(r"10\.\d{4,9}/[^\s<>\]})]+", header_text, re.I)}
        header_dois.discard(None)
        header_arxivs = {_arxiv(match) for match in re.findall(r"\d{4}\.\d{4,5}(?:v\d+)?", header_text, re.I)}
        header_arxivs.discard(None)
        if expected_doi and header_dois and expected_doi not in header_dois:
            raise ValueError("identity_doi_mismatch")
        if expected_arxiv and header_arxivs and expected_arxiv not in {_arxiv_base(item) for item in header_arxivs}:
            raise ValueError("identity_arxiv_mismatch")
        title_contiguous = len(expected_tokens) >= 4 and expected_title in header_normalized
        if title_contiguous or (score >= 0.78 and token_recall >= 0.85 and token_precision >= 0.72):
            basis = {"kind": "title", "normalized_value": expected_title, "matched_title": identity_title, "title_similarity": round(score, 4), "title_token_recall": round(token_recall, 4), "title_token_precision": round(token_precision, 4), "page_count": doc.page_count, "evidence_excerpt": header_text[:500].strip()}
            if expected_doi and expected_doi in header_dois:
                basis["corroborating_doi"] = expected_doi
            if expected_arxiv:
                basis["corroborating_arxiv"] = next((item for item in header_arxivs if _arxiv_base(item) == expected_arxiv), None)
            if identity_title != paper["title"]:
                basis.update({"original_title": paper["title"], "title_normalization": "removed catalog venue suffix"})
            return basis
        raise ValueError("identity_not_verified")
    finally:
        doc.close()


def _title_windows(text: str) -> list[str]:
    lines = [_normalize_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    windows: list[str] = []
    for start in range(min(len(lines), 40)):
        for width in range(1, 7):
            candidate = " ".join(lines[start:start + width]).strip()
            if candidate:
                windows.append(candidate)
    return windows


def _article_header(first_page: str) -> str:
    """Return first-page title/author block, excluding abstract/body/references."""
    stop = re.compile(r"^(?:abstract|summary|keywords?\b|\d+(?:\.\d+)*\s+introduction\b|introduction\b|references\b|bibliography\b|1\s+background\b)", re.I)
    selected: list[str] = []
    for line in first_page.splitlines():
        if stop.match(line.strip()):
            break
        if line.strip() and len([item for item in selected if item.strip()]) >= 12:
            break
        if sum(len(item) + 1 for item in selected) >= 800:
            break
        selected.append(line)
    return "\n".join(selected)


def _verify_ready_record(paper: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any] | None:
    """Revalidate cached bytes under current title rules before resuming them."""
    try:
        path = Path(prior["pdf_path"])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != prior.get("sha256"):
            return None
        identity_paper = paper
        resolution = prior.get("identity_resolution") or {}
        if resolution.get("resolved_title"):
            exact = urlparse(resolution.get("exact_pdf_link", ""))
            final = urlparse(prior.get("final_url", ""))
            if exact.scheme != "https" or final.scheme != "https" or exact.path != final.path:
                return None
            if {exact.hostname, final.hostname} - {"jmlr.org", "www.jmlr.org"}:
                return None
            identity_paper = {**paper, "title": resolution["resolved_title"]}
        identity = _identity_check(path, identity_paper)
        if prior.get("page_count") != identity.get("page_count"):
            return None
        return identity
    except (OSError, KeyError, TypeError, ValueError):
        return None


def _identity_title(paper: dict[str, Any]) -> str:
    title = str(paper["title"]).strip()
    venue = str(paper.get("venue") or "").strip()
    if venue and "|" in title:
        prefix, suffix = title.rsplit("|", 1)
        if suffix.strip().casefold() == venue.casefold():
            return prefix.strip()
    if title.casefold().endswith(" - acl anthology"):
        return title[:-len(" - ACL Anthology")].strip()
    return title


def load_catalog(db_path: Path) -> list[dict[str, Any]]:
    """Read paper identities and direct PDF URLs without modifying SQLite."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        query = """
        SELECT p.paper_id, p.title, p.venue_name, p.doi, p.source_url, p.authors_json,
               (SELECT normalized_value FROM paper_identifiers i
                WHERE i.paper_id=p.paper_id AND i.kind='arxiv' LIMIT 1) AS arxiv_id,
               (SELECT remote_url FROM artifacts a
                WHERE a.paper_id=p.paper_id AND a.kind='pdf' AND a.remote_url IS NOT NULL
                ORDER BY a.artifact_id LIMIT 1) AS pdf_url
        FROM papers p ORDER BY p.paper_id
        """
        rows = []
        for row in connection.execute(query):
            rows.append({"paper_id": row["paper_id"], "title": row["title"], "venue": row["venue_name"], "doi": row["doi"],
                         "arxiv_id": row["arxiv_id"], "source_url": row["source_url"],
                         "authors": json.loads(row["authors_json"]), "pdf_url": row["pdf_url"]})
        return rows
    finally:
        connection.close()


def _valid_source(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    try:
        standard_port = parsed.port in (None, 443)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and standard_port and parsed.username is None and parsed.password is None


def _public_ip_for_host(host: str, resolver=socket.getaddrinfo, *, allow_nature_idp: bool = False) -> str:
    if host.casefold() == "idp.nature.com" and not allow_nature_idp:
        raise ValueError("access_gate_redirect")
    if host.casefold() not in ALLOWED_HOSTS and not (allow_nature_idp and host.casefold() == "idp.nature.com"):
        raise ValueError("host_not_allowlisted")
    if resolver is socket.getaddrinfo and host in _PUBLIC_IP_CACHE:
        return _PUBLIC_IP_CACHE[host]
    try:
        addresses = resolver(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("host_resolution_failed") from exc
    for result in addresses:
        address = result[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip.is_global:
            result_ip = str(ip)
            if resolver is socket.getaddrinfo:
                _PUBLIC_IP_CACHE[host] = result_ip
            return result_ip
    raise ValueError("host_has_no_public_address")


async def _public_ip_for_host_async(host: str, *, allow_nature_idp: bool = False) -> str:
    try:
        return await asyncio.wait_for(asyncio.to_thread(_public_ip_for_host, host, allow_nature_idp=allow_nature_idp), timeout=DNS_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise ValueError("host_resolution_timeout") from exc


async def _curl_download(url: str, tmp_path: Path, host_locks: dict[str, asyncio.Lock],
                        global_semaphore: asyncio.Semaphore | None = None,
                        max_bytes: int = MAX_PDF_BYTES) -> tuple[int, str, str]:
    """Fetch with TLS on and validate each redirect before following it."""
    current = url
    original = urlparse(url)
    nature_flow = original.hostname == "www.nature.com"
    nature_cookiejar: Path | None = None
    if nature_flow:
        fd, cookie_name = tempfile.mkstemp(prefix=".nature-cookies-", dir=tmp_path.parent)
        os.close(fd)
        nature_cookiejar = Path(cookie_name)
    visited: set[str] = set()
    try:
        for _ in range(8 if nature_flow else 6):
            if not _valid_source(current):
                raise ValueError("invalid_or_cyclic_redirect")
            parsed = urlparse(current)
            host = parsed.hostname.casefold()
            if nature_flow:
                if host not in {"www.nature.com", "idp.nature.com"}:
                    raise ValueError("nature_redirect_out_of_scope")
                if host == "www.nature.com" and parsed.path != original.path:
                    raise ValueError("nature_redirect_out_of_scope")
                if host == "idp.nature.com" and not parsed.path.startswith(("/authorize", "/transit")):
                    raise ValueError("nature_redirect_out_of_scope")
                if host == "www.nature.com" and current in visited:
                    # The only permitted URL cycle is publisher -> IDP cookies -> same PDF URL.
                    if len(visited) < 3:
                        raise ValueError("nature_redirect_cycle_without_bootstrap")
                elif current in visited:
                    raise ValueError("invalid_or_cyclic_redirect")
            elif current in visited:
                raise ValueError("invalid_or_cyclic_redirect")
            visited.add(current)
            ip = await _public_ip_for_host_async(host, allow_nature_idp=nature_flow and host == "idp.nature.com")
            host_lock = host_locks.setdefault(host, asyncio.Lock())
            async with host_lock:
              header_path = tmp_path.with_suffix(tmp_path.suffix + ".headers")
              async def transfer() -> tuple[bytes, bytes, int, str]:
                command = [
                    "curl", "-q", "--silent", "--show-error", "--fail", "--max-redirs", "0",
                    "--proto", "=https", "--proto-redir", "=https", "--noproxy", "*",
                    "--connect-timeout", "15", "--max-time", str(REQUEST_TIMEOUT_SECONDS),
                    "--max-filesize", str(max_bytes), "--resolve",
                    f"{host}:443:{f'[{ip}]' if ':' in ip else ip}", "--user-agent", USER_AGENT,
                    "--header", "Accept: application/pdf,application/octet-stream;q=0.8,*/*;q=0.1",
                ]
                if nature_cookiejar is not None:
                    command.extend(["--cookie", str(nature_cookiejar), "--cookie-jar", str(nature_cookiejar)])
                command.extend(["--dump-header", str(header_path), "--output", str(tmp_path),
                    "--write-out", "%{http_code}\\n%{content_type}\\n%{url_effective}", current])
                process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=REQUEST_TIMEOUT_SECONDS + 5)
                    try:
                        headers = header_path.read_text(encoding="iso-8859-1", errors="replace")
                    except OSError:
                        headers = ""
                    return stdout, stderr, process.returncode, headers
                except BaseException:
                    if process.returncode is None:
                        process.kill()
                    try:
                        await process.communicate()
                    except BaseException:
                        pass
                    raise
              try:
                if global_semaphore is None:
                    stdout, stderr, returncode, headers = await transfer()
                else:
                    async with global_semaphore:
                        stdout, stderr, returncode, headers = await transfer()
              finally:
                header_path.unlink(missing_ok=True)
            lines = stdout.decode("utf-8", errors="replace").splitlines()
            status = int(lines[0]) if lines and lines[0].isdigit() else 0
            content_type = lines[1].split(";", 1)[0].strip().casefold() if len(lines) > 1 else ""
            header_blocks = re.split(r"\r?\n\r?\n", headers)
            response_headers = header_blocks[-2] if len(header_blocks) > 1 else headers
            location_match = re.search(r"^location:\s*(.+)$", response_headers, re.I | re.M)
            header_status = re.search(r"^HTTP/\S+\s+(\d{3})", response_headers, re.I | re.M)
            if header_status:
                status = int(header_status.group(1))
            if 300 <= status < 400:
                if not location_match:
                    raise RuntimeError(f"http_{status}_without_location")
                next_url = urljoin(current, location_match.group(1).strip())
                if not _valid_source(next_url):
                    raise ValueError("redirect_to_non_https_url")
                next_host = urlparse(next_url).hostname.casefold()
                if nature_flow:
                    if next_host not in {"www.nature.com", "idp.nature.com"}:
                        raise ValueError("nature_redirect_out_of_scope")
                    if next_host == "www.nature.com" and urlparse(next_url).path != original.path:
                        raise ValueError("nature_redirect_out_of_scope")
                    if next_host == "idp.nature.com" and not urlparse(next_url).path.startswith(("/authorize", "/transit")):
                        raise ValueError("nature_redirect_out_of_scope")
                elif next_host == "idp.nature.com":
                    raise ValueError("access_gate_redirect")
                await _public_ip_for_host_async(next_host, allow_nature_idp=nature_flow and next_host == "idp.nature.com")
                tmp_path.unlink(missing_ok=True)
                header_path.unlink(missing_ok=True)
                current = next_url
                continue
            if returncode:
                message = stderr.decode("utf-8", errors="replace")[-500:].strip() or f"curl_exit_{returncode}"
                raise RuntimeError(f"http_{status}: {message}")
            return status, content_type, current
        raise ValueError("redirect_limit_exceeded")
    finally:
        if nature_cookiejar is not None:
            nature_cookiejar.unlink(missing_ok=True)


def source_url_candidates(paper: dict[str, Any]) -> list[tuple[str, str]]:
    """Derive only deterministic PDF endpoints from a catalog URL/identifier."""
    candidates: list[tuple[str, str]] = []
    direct = paper.get("pdf_url")
    if _valid_source(direct):
        candidates.append((direct, "catalog_pdf_url"))
    source = paper.get("source_url") or ""
    parsed = urlparse(source)
    host = (parsed.hostname or "").casefold()
    path = unquote(parsed.path)
    if host.endswith("aclanthology.org"):
        item = path.strip("/")
        if item and not item.endswith(".pdf"):
            candidates.append((f"https://aclanthology.org/{item}.pdf", "acl_anthology_landing_url"))
    elif host == "proceedings.mlr.press":
        if path.casefold().endswith(".pdf"):
            candidates.append((source, "catalog_paper_url_direct_pdf"))
        match = re.search(r"/(?:abs/)?(v\d+)/([^/]+?)(?:\.html)?/?$", path)
        if match:
            volume, slug = match.groups()
            candidates.append((f"https://proceedings.mlr.press/{volume}/{slug}/{slug}.pdf", "pmlr_landing_url"))
    elif host in {"proceedings.neurips.cc", "papers.nips.cc"}:
        if re.search(r"-Abstract(?:-Conference)?\.html$", path, re.I):
            pdf_path = re.sub(r"-Abstract(?:-Conference)?\.html$", "-Paper.pdf", path, flags=re.I)
            candidates.append((f"https://{host}{pdf_path}", "neurips_landing_url"))
    elif host in {"jmlr.org", "www.jmlr.org"} and path.casefold().endswith(".html"):
        match = re.search(r"/papers/v(\d+)/([^/]+)\.html$", path, re.I)
        if match:
            volume, slug = match.groups()
            candidates.append((f"https://{host}/papers/volume{volume}/{slug}/{slug}.pdf", "jmlr_landing_url"))
        else:
            candidates.append((f"https://{host}{path[:-5]}.pdf", "jmlr_landing_url"))
    elif host == "www.nature.com" and path.startswith("/articles/") and not path.casefold().endswith(".pdf"):
        candidates.append((f"https://www.nature.com{path}.pdf", "nature_landing_url"))
    doi = _doi(paper.get("doi"))
    if doi and host == "link.springer.com":
        candidates.append((f"https://link.springer.com/content/pdf/{doi}.pdf", "springer_doi"))
    arxiv_id = _arxiv(paper.get("arxiv_id"))
    if arxiv_id:
        candidates.append((f"https://arxiv.org/pdf/{arxiv_id}.pdf", "arxiv_identifier"))
    seen: set[str] = set()
    return [(u, basis) for u, basis in candidates if _valid_source(u) and not (u in seen or seen.add(u))]


class _JmlrPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.pdf_hrefs: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "title":
            self.in_title = True
        if tag.casefold() == "a":
            href = dict(attrs).get("href") or ""
            if href.casefold().endswith(".pdf"):
                self.pdf_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


class _PdfLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "a":
            href = dict(attrs).get("href") or ""
            if urlparse(href).path.casefold().endswith(".pdf"):
                self.links.append(href)


def jmlr_landing_url(pdf_url: str) -> str | None:
    parsed = urlparse(pdf_url)
    if (parsed.hostname or "").casefold() not in {"jmlr.org", "www.jmlr.org"}:
        return None
    match = re.search(r"/papers/volume(\d+)/([^/]+)/[^/]+\.pdf$", parsed.path, re.I)
    if not match:
        return None
    volume, slug = match.groups()
    return f"https://www.jmlr.org/papers/v{volume}/{slug}.html"


def select_official_pdf_link(source_url: str, landing_url: str, hrefs: list[str]) -> str | None:
    source = urlparse(source_url)
    host = (source.hostname or "").casefold()
    links = [urljoin(landing_url, href) for href in hrefs]
    links = [link for link in links if _valid_source(link) and (urlparse(link).hostname or "").casefold() in ALLOWED_HOSTS]
    if host == "proceedings.mlr.press":
        match = re.search(r"/v\d+/([^/]+?)(?:\.html)?/?$", source.path, re.I)
        if not match:
            return None
        slug = match.group(1)
        links = [link for link in links if Path(urlparse(link).path).name.casefold() == f"{slug}.pdf".casefold()]
    elif host in {"proceedings.neurips.cc", "papers.nips.cc"}:
        stem = Path(source.path).name
        paper_key = re.sub(r"-Abstract(?:-Conference)?\.html$", "", stem, flags=re.I)
        matching = [link for link in links if paper_key in Path(urlparse(link).path).name and "paper" in Path(urlparse(link).path).name.casefold()]
        conference = [link for link in matching if "-paper-conference.pdf" in urlparse(link).path.casefold()]
        links = conference or [link for link in matching if "-paper.pdf" in urlparse(link).path.casefold()]
    else:
        return None
    unique = list(dict.fromkeys(links))
    return unique[0] if len(unique) == 1 else None


async def resolve_jmlr_identity(pdf_url: str, scratch_path: Path,
                                host_locks: dict[str, asyncio.Lock],
                                global_semaphore: asyncio.Semaphore | None = None) -> dict[str, str] | None:
    landing = jmlr_landing_url(pdf_url)
    if not landing:
        return None
    try:
      status, content_type, final_page_url = await _curl_download(landing, scratch_path, host_locks, global_semaphore, max_bytes=2 * 1024 * 1024)
      if status < 200 or status >= 300 or content_type not in {"text/html", "application/xhtml+xml"}:
        return None
      body = scratch_path.read_bytes()
    finally:
        scratch_path.unlink(missing_ok=True)
    parser = _JmlrPageParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    title = " ".join(" ".join(parser.title_parts).split())
    pdf_links = [urljoin(final_page_url, href) for href in parser.pdf_hrefs]
    expected_path = urlparse(pdf_url).path.rstrip("/")
    exact_link = next((link for link in pdf_links if urlparse(link).path.rstrip("/") == expected_path), None)
    if not title or _is_generic_title(title) or not exact_link:
        return None
    if not _valid_source(exact_link) or (urlparse(exact_link).hostname or "").casefold() not in {"jmlr.org", "www.jmlr.org"}:
        return None
    return {"resolved_title": title, "authoritative_url": final_page_url, "exact_pdf_link": exact_link}


async def resolve_official_pdf_link(source_url: str, scratch_path: Path,
                                    host_locks: dict[str, asyncio.Lock],
                                    global_semaphore: asyncio.Semaphore) -> dict[str, str] | None:
    """Read PDF hrefs from a known official proceedings landing page."""
    source = urlparse(source_url)
    host = (source.hostname or "").casefold()
    if host not in {"proceedings.mlr.press", "proceedings.neurips.cc", "papers.nips.cc"}:
        return None
    status, content_type, final_page_url = await _curl_download(
        source_url, scratch_path, host_locks, global_semaphore, max_bytes=2 * 1024 * 1024
    )
    try:
        if status < 200 or status >= 300 or content_type not in {"text/html", "application/xhtml+xml"}:
            return None
        parser = _PdfLinkParser()
        parser.feed(scratch_path.read_text(encoding="utf-8", errors="replace"))
    finally:
        scratch_path.unlink(missing_ok=True)
    exact_link = select_official_pdf_link(source_url, final_page_url, parser.links)
    if exact_link is None:
        return None
    await _public_ip_for_host_async(urlparse(exact_link).hostname or "")
    return {"authoritative_url": final_page_url, "exact_pdf_link": exact_link, "provenance": "official_proceedings_landing_anchor"}


async def _fetch_one(session_semaphore: asyncio.Semaphore, paper: dict[str, Any], root: Path,
                     host_locks: dict[str, asyncio.Lock], retry_terminal: bool = False,
                     source_resolution: dict[str, str] | None = None) -> dict[str, Any]:
    paper_id = paper["paper_id"]
    records_dir, ready_dir, pdf_dir, partial_dir = (root / name for name in ("records", "ready", "pdfs", ".partial"))
    record_path = records_dir / f"{paper_id}.json"
    ready_path = ready_dir / f"{paper_id}.json"
    if not retry_terminal and record_path.exists():
        try:
            previous = json.loads(record_path.read_text(encoding="utf-8"))
            if previous.get("status") in {"unavailable", "failure"}:
                return {"paper_id": paper_id, "status": previous["status"], "resumed": True}
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    if ready_path.exists():
        try:
            prior = json.loads(ready_path.read_text(encoding="utf-8"))
            current_identity = _verify_ready_record(paper, prior)
            if current_identity:
                prior["identity_basis"] = {"resolver": prior.get("identity_basis", {}).get("resolver", "resumed_verified_pdf"), **current_identity}
                prior["identity_validator"] = "firstpage-header-title-v2"
                _atomic_json(ready_path, prior)
                _atomic_json(record_path, {**prior, "attempts": []})
                return {"paper_id": paper_id, "status": "ready", "resumed": True}
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass
        if ready_path.exists():
            stale_dir = root / "quarantine" / "stale-ready"
            stale_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(ready_path, stale_dir / f"{paper_id}.json")
            except OSError:
                pass
        ready_path.unlink(missing_ok=True)

    candidates = source_url_candidates(paper)
    if not candidates:
        result = {"paper_id": paper_id, "status": "needs_resolution", "reason": "no_catalog_pdf_url_or_deterministic_resolver", "source_url": paper.get("source_url"), "resolution_attempts": [], "attempted_at_utc": _utc_now()}
        _atomic_json(record_path, result)
        return result
    attempts: list[dict[str, Any]] = []
    failure_reasons: list[str] = []
    for url, identity_basis in candidates:
        for attempt in range(1, MAX_ATTEMPTS + 1):
          tmp_path: Path | None = None
          identity_resolution: dict[str, str] | None = None
          try:
                free_bytes = shutil.disk_usage(root).free
                if free_bytes < MIN_FREE_BYTES:
                    raise RuntimeError(f"disk_floor_reached:{free_bytes}")
                partial_dir.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(prefix=f"{paper_id}.", suffix=".part", dir=partial_dir)
                os.close(fd)
                tmp_path = Path(name)
                status_code, content_type, final_url = await _curl_download(url, tmp_path, host_locks, session_semaphore)
                if not _valid_source(final_url):
                    raise ValueError("redirect_to_non_https_url")
                if not tmp_path.is_file() or tmp_path.stat().st_size < 8:
                    raise ValueError("empty_or_truncated_download")
                size = tmp_path.stat().st_size
                if size > MAX_PDF_BYTES:
                    raise ValueError("pdf_size_limit_exceeded")
                digest = hashlib.sha256()
                with tmp_path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                try:
                    identity = _identity_check(tmp_path, paper)
                except ValueError as exc:
                    if str(exc) not in {"identity_catalog_title_is_generic", "identity_not_verified"}:
                        raise
                    identity_resolution = await resolve_jmlr_identity(
                        final_url, tmp_path.with_suffix(".source.html"), host_locks, session_semaphore
                    )
                    if not identity_resolution:
                        raise
                    identity = _identity_check(tmp_path, {**paper, "title": identity_resolution["resolved_title"]})
                    identity.update({"original_title": paper["title"], **identity_resolution, "provenance": "official_jmlr_landing_page"})
                pdf_dir.mkdir(parents=True, exist_ok=True)
                final_path = pdf_dir / f"{paper_id}.pdf"
                os.replace(tmp_path, final_path)
                tmp_path = None
                ready_record = {
                    "paper_id": paper_id, "status": "ready", "pdf_path": str(final_path.resolve()),
                    "sha256": digest.hexdigest(), "size_bytes": size, "page_count": identity.pop("page_count"),
                    "source_url": url, "final_url": final_url, "fetched_at_utc": _utc_now(),
                    "content_type": content_type, "parser": "pymupdf", "identity_basis": {"resolver": identity_basis, **identity},
                }
                if source_resolution:
                    ready_record["source_resolution"] = source_resolution
                if identity_resolution:
                    ready_record["identity_resolution"] = identity_resolution
                _atomic_json(ready_path, ready_record)
                result = {**ready_record, "attempts": attempts}
                _atomic_json(record_path, result)
                return result
          except (asyncio.TimeoutError, ValueError, OSError, RuntimeError) as exc:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)
            message = str(exc)[:300]
            status_match = re.search(r"http_(\d{3})", message, re.I)
            attempts.append({"source_url": url, "identity_basis": identity_basis, "attempt": attempt, "http_status": int(status_match.group(1)) if status_match else None, "error": type(exc).__name__, "message": message})
            failure_reasons.append(f"http_{status_match.group(1)}" if status_match else message)
            if status_match and status_match.group(1) in {"403", "404", "410", "451"}:
                break
            if message.startswith("disk_floor_reached:"):
                break
            if isinstance(exc, ValueError) or attempt >= MAX_ATTEMPTS:
                break
            await asyncio.sleep(min(2 ** (attempt - 1), 8))
          except asyncio.CancelledError:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)
            raise
    if not source_resolution and paper.get("source_url"):
        scratch_path = partial_dir / f"{paper_id}.landing.part"
        try:
            resolution = await resolve_official_pdf_link(paper["source_url"], scratch_path, host_locks, session_semaphore)
        except (OSError, RuntimeError, ValueError, asyncio.TimeoutError):
            resolution = None
        if resolution:
            return await _fetch_one(
                session_semaphore, {**paper, "pdf_url": resolution["exact_pdf_link"]}, root,
                host_locks, retry_terminal=True, source_resolution=resolution
            )
    if failure_reasons and all(reason.startswith("access_gate_redirect") for reason in failure_reasons):
        status = "needs_resolution"
        reason = "access_gate_redirect_pending_bounded_anonymous_flow_review"
        result = {"paper_id": paper_id, "status": status, "reason": reason, "source_url": paper.get("source_url"), "attempts": attempts, "attempted_at_utc": _utc_now()}
        _atomic_json(record_path, result)
        return result
    unavailable_prefixes = ("http_403", "http_404", "http_410", "http_451")
    status = "unavailable" if failure_reasons and all(r.startswith(unavailable_prefixes) for r in failure_reasons) else "failure"
    reason = failure_reasons[-1] if failure_reasons else "no_successful_pdf_endpoint"
    result = {"paper_id": paper_id, "status": status, "reason": reason, "source_url": paper.get("source_url"), "attempts": attempts, "attempted_at_utc": _utc_now()}
    _atomic_json(record_path, result)
    return result


async def acquire(papers: list[dict[str, Any]], root: Path, max_items: int | None = None, retry_terminal: bool = False) -> dict[str, int]:
    root.mkdir(parents=True, exist_ok=True)
    host_locks: dict[str, asyncio.Lock] = {}
    selected = papers[:max_items] if max_items is not None else papers
    semaphore = asyncio.Semaphore(TOTAL_WORKERS)
    results = await asyncio.gather(*(_fetch_one(semaphore, paper, root, host_locks, retry_terminal) for paper in selected))
    counts = {status: 0 for status in ("ready", "unavailable", "failure", "needs_resolution")}
    for result in results:
        counts[result["status"]] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True, help="private catalog SQLite path (opened read-only)")
    parser.add_argument("--output", type=Path, required=True, help="private transfer directory outside Git")
    parser.add_argument("--max-items", type=int, help="bounded slice for an initial run")
    parser.add_argument("--retry-terminal", action="store_true", help="retry prior terminal failures (records are replaced atomically)")
    args = parser.parse_args()
    papers = load_catalog(args.db)
    counts = asyncio.run(acquire(papers, args.output, args.max_items, args.retry_terminal))
    print(json.dumps({"catalog_count": len(papers), "processed_count": sum(counts.values()), "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
