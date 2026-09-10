"""A failed Chrome run must never succeed because an older PDF exists."""
import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('topdf', pathlib.Path(__file__).parents[1] / 'sync/topdf.py')
topdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(topdf)


class ExportFailureTest(unittest.TestCase):
    def test_failed_chrome_preserves_existing_pdf_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source, output = root/'input.html', root/'existing.pdf'
            source.write_text('<html><body>원문</body></html>')
            output.write_bytes(b'older PDF')
            class LocalStage:
                work, port = directory, 9
                def __init__(self, repo): pass
                def local_fonts(self): return ''
                def close(self): pass
            with patch.object(topdf, 'Prober', LocalStage), patch.object(topdf, 'CHROME', '/usr/bin/false'), patch.object(sys, 'argv', ['topdf.py',str(source),str(output)]):
                with self.assertRaises(SystemExit):
                    topdf.main()
            self.assertEqual(output.read_bytes(), b'older PDF')


if __name__ == '__main__':
    unittest.main()
