import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.ingest.workbook import load_workbook_catalog


WORKBOOK_XML = '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="TAG_DICTIONARY" sheetId="1" r:id="rId1"/><sheet name="PAPER_LIBRARY" sheetId="2" r:id="rId2"/><sheet name="PAPER_TAGS" sheetId="3" r:id="rId3"/></sheets></workbook>'''
RELS_XML = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Target="worksheets/sheet3.xml"/></Relationships>'''


def sheet_xml(rows):
    xml_rows = []
    for row_num, row in enumerate(rows, 1):
        cells = []
        for col_num, value in enumerate(row):
            if not value:
                continue
            col = chr(ord("A") + col_num)
            cells.append(f'<c r="{col}{row_num}" t="inlineStr"><is><t>{value}</t></is></c>')
        xml_rows.append(f'<row r="{row_num}">{"".join(cells)}</row>')
    return f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>'


class WorkbookAdapterTests(unittest.TestCase):
    def test_maps_named_sheets_and_keeps_unreviewed_sources_unqualified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.xlsx"
            tags = [["Canonical tag", "Namespace", "Nhóm con", "English label", "Ý nghĩa / Khi dùng", "Aliases / Search synonyms", "State"],
                    ["method/example", "method", "Group", "Example", "Description", "alias; synonym", "Active"]]
            papers = [["Paper_ID", "Title", "Authors", "Year", "Venue / Journal", "DOI", "Paper URL", "PDF / Drive link", "Venue type", "CORE rank", "SJR quartile", "Ranking system", "Ranking year", "Ranking category / basis", "Ranking source URL", "Publication evidence URL", "Venue eligibility", "Personal notes"],
                      ["P-stable", "Fixture title", "Author One; Author Two", "2024", "Example Journal", "10.1234/FIXTURE", "https://example.org/p", "https://example.org/p.pdf", "journal", "", "Q1", "SJR", "2023", "AI", "https://example.org/rank", "https://example.org/evidence", "venue-qualified", "must not be imported"]]
            edges = [["Paper_ID", "Canonical tag", "Tag type / role", "Evidence in paper", "Manual QA status"],
                     ["P-stable", "method/example", "method", "candidate evidence", "needs-manual-review"]]
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", WORKBOOK_XML)
                archive.writestr("xl/_rels/workbook.xml.rels", RELS_XML)
                for index, rows in enumerate((tags, papers, edges), 1):
                    archive.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml(rows))
            catalog = load_workbook_catalog(path)
        self.assertEqual(catalog["tags"][0]["aliases"], ["alias", "synonym"])
        self.assertEqual(catalog["papers"][0]["paper_id"], "P-stable")
        self.assertEqual(catalog["papers"][0]["eligibility"], "unknown")
        self.assertEqual(catalog["papers"][0]["pdf_state"], "REMOTE_ONLY")
        self.assertEqual(catalog["paper_tags"][0]["review_state"], "needs-manual-review")
        self.assertNotIn("must not be imported", repr(catalog))


if __name__ == "__main__":
    unittest.main()
