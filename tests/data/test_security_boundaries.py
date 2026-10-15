import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

from backend.ingest import import_catalog
from backend.ingest.workbook import load_workbook_catalog
from backend.persistence import connect, migrate


class ImportBoundsTests(unittest.TestCase):
    def test_compression_bomb_and_traversal_are_rejected_before_xml(self):
        for name, content in [('xl/bomb.xml', b'a' * 100000), ('../escape.xml', b'x')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'bad.xlsx'
                with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(name, content)
                with self.assertRaises(ValueError):
                    load_workbook_catalog(path)

    def test_missing_required_headers_fail(self):
        sheets = {'TAG_DICTIONARY': [['Canonical tag']], 'PAPER_LIBRARY': [['Paper_ID']],
                  'PAPER_TAGS': [['Paper_ID']]}
        with patch('backend.ingest.workbook._xlsx_sheets', return_value=sheets):
            with self.assertRaisesRegex(ValueError, 'headers'):
                load_workbook_catalog('synthetic.xlsx')

    def test_failed_migration_rolls_back_and_backup_restores_source(self):
        db = connect(':memory:')
        with tempfile.TemporaryDirectory() as folder:
            migration = Path(folder) / '0001_bad.sql'
            migration.write_text('CREATE TABLE partial (id INTEGER); INSERT INTO absent VALUES(1);')
            with patch('backend.persistence._MIGRATIONS', Path(folder)):
                with self.assertRaises(Exception):
                    migrate(db)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='partial'").fetchone())
        migrate(db)
        import_catalog(db, {'papers': [{'paper_id':'P','title':'Source'}]}, 'source', 'r1')
        backup = connect(':memory:')
        db.backup(backup)
        db.execute("UPDATE papers SET title='Changed'"); db.commit()
        backup.backup(db)
        self.assertEqual(db.execute('SELECT title FROM papers').fetchone()[0], 'Source')
        backup.close(); db.close()
