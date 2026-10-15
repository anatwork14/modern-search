"""Read a sanitized catalog from XLSX using only the Python standard library."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def _column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref).group(0)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def _xlsx_sheets(path: str | Path) -> dict[str, list[list[str]]]:
    """Return workbook sheet rows, resolving shared and inline strings."""
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships.findall("pkg:Relationship", _NS)}
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//main:t", _NS)) for item in root.findall("main:si", _NS)]
        sheets: dict[str, list[list[str]]] = {}
        for sheet in workbook.findall("main:sheets/main:sheet", _NS):
            name = sheet.attrib["name"]
            target = targets[sheet.attrib[f"{{{_NS['rel']}}}id"]]
            if target.startswith("/"):
                member = target.lstrip("/")
            elif target.startswith("xl/"):
                member = target
            else:
                member = f"xl/{target}"
            root = ET.fromstring(archive.read(member))
            rows: list[list[str]] = []
            for row_node in root.findall("main:sheetData/main:row", _NS):
                cells: dict[int, str] = {}
                for cell in row_node.findall("main:c", _NS):
                    ref = cell.attrib.get("r", "A1")
                    idx = _column_index(ref)
                    value = cell.find("main:v", _NS)
                    if cell.attrib.get("t") == "s" and value is not None:
                        text = shared[int(value.text or 0)]
                    elif cell.attrib.get("t") == "inlineStr":
                        text = "".join(node.text or "" for node in cell.findall(".//main:t", _NS))
                    elif value is not None:
                        text = value.text or ""
                    else:
                        text = ""
                    cells[idx] = text
                if cells:
                    row = [""] * (max(cells) + 1)
                    for idx, value in cells.items():
                        row[idx] = value
                    rows.append(row)
                else:
                    rows.append([])
            sheets[name] = rows
        return sheets


def _records(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    header_row = next((row for row in rows if any(value.strip() for value in row)), [])
    headers = [value.strip() for value in header_row]
    result = []
    for row in rows[rows.index(header_row) + 1:]:
        if not any(value.strip() for value in row):
            continue
        result.append({header: row[index].strip() if index < len(row) else "" for index, header in enumerate(headers) if header})
    return result


def load_workbook_catalog(path: str | Path) -> dict:
    """Map source workbook headers into the versioned persistence import shape.

    Raw ``Personal notes`` are deliberately excluded. Full source rows are retained
    in the user's local snapshot separately when desired; source_records store only
    the mapped fields passed to ``import_catalog``.
    """
    sheets = _xlsx_sheets(path)
    table_names = {"TAG_DICTIONARY", "PAPER_LIBRARY", "PAPER_TAGS"}
    if not table_names.issubset(sheets):
        raise ValueError(f"workbook lacks required sheets: {', '.join(sorted(table_names - sheets.keys()))}")
    tag_rows = _records(sheets["TAG_DICTIONARY"])
    paper_rows = _records(sheets["PAPER_LIBRARY"])
    edge_rows = _records(sheets["PAPER_TAGS"])
    tags = []
    for row in tag_rows:
        tag_id = row.get("Canonical tag", "")
        if not tag_id:
            continue
        tags.append({
            "tag_id": tag_id,
            "namespace": row.get("Namespace", ""),
            "subgroup": row.get("Nhóm con", "") or None,
            "label": row.get("English label", "") or tag_id.rsplit("/", 1)[-1],
            "description": row.get("Ý nghĩa / Khi dùng", "") or None,
            "aliases": [alias.strip() for alias in re.split(r"[;,]", row.get("Aliases / Search synonyms", "")) if alias.strip()],
            "active": row.get("State", "Active").casefold() == "active",
        })
    papers = []
    for row in paper_rows:
        paper_id = row.get("Paper_ID", "")
        if not paper_id:
            continue
        year = row.get("Year", "")
        try:
            year_value = int(float(year)) if year else None
        except ValueError:
            year_value = None
        link = row.get("PDF / Drive link", "")
        # Source rows say venue-qualified, but topical/validity checks remain open.
        # Keep eligibility unknown until a trusted evidence review promotes it.
        papers.append({
            "paper_id": paper_id,
            "title": row.get("Title", ""),
            "authors": [author.strip() for author in row.get("Authors", "").split(";") if author.strip()],
            "year": year_value,
            "venue": row.get("Venue / Journal", "") or None,
            "doi": row.get("DOI", "") or None,
            "source_url": row.get("Paper URL", "") or None,
            "pdf_url": link or None,
            "pdf_state": "REMOTE_ONLY" if link else "UNAVAILABLE",
            "review_state": "discovered",
            "eligibility": "unknown",
            "venue_evidence": {
                "venue_type": row.get("Venue type", "") or None,
                "core_rank": row.get("CORE rank", "") or None,
                "sjr_quartile": row.get("SJR quartile", "") or None,
                "ranking_system": row.get("Ranking system", "") or None,
                "ranking_year": int(row["Ranking year"]) if row.get("Ranking year", "").isdigit() else None,
                "ranking_category": row.get("Ranking category / basis", "") or None,
                "ranking_source_url": row.get("Ranking source URL", "") or None,
                "publication_evidence_url": row.get("Publication evidence URL", "") or None,
            },
        })
    tag_ids = {row["tag_id"] for row in tags}
    paper_ids = {row["paper_id"] for row in papers}
    paper_tags = []
    for row in edge_rows:
        paper_id, tag_id = row.get("Paper_ID", ""), row.get("Canonical tag", "")
        if paper_id not in paper_ids or tag_id not in tag_ids:
            continue
        qa = row.get("Manual QA status", "").casefold()
        review_state = qa if qa in {"needs-manual-review", "verified", "rejected"} else "needs-manual-review"
        paper_tags.append({
            "paper_id": paper_id,
            "tag_id": tag_id,
            "role": "candidate",
            "asserted_from": "lexical_discovery",
            "review_state": review_state,
            "evidence": row.get("Evidence in paper", "") or None,
        })
    return {"tags": tags, "papers": papers, "paper_tags": paper_tags}


__all__ = ["load_workbook_catalog"]
