"""Raster fixtures catch footer misclassification without PDF/font dependencies."""
import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('checkpdf', pathlib.Path(__file__).parents[1] / 'sync/checkpdf.py')
checkpdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpdf)


class PageFillsTest(unittest.TestCase):
    def scan(self, dark_rows):
        def rasterize(args, **kwargs):
            # 1 pixel/mm; body occupies y=20..276 inclusive.
            image = bytearray([255]) * (210 * 297)
            for y in dark_rows:
                image[y*210+20:y*210+190] = bytes([0])*170
            pathlib.Path(args[-1] + '-1.pgm').write_bytes(b'P5\n210 297\n255\n'+image)
        with patch.object(checkpdf.subprocess, 'run', side_effect=rasterize):
            return checkpdf.page_fills('fixture.pdf')[0]

    def test_last_body_line_is_not_mistaken_for_a_footer(self):
        pct, _ = self.scan([40, 250])
        self.assertAlmostEqual(pct, (251-20)/257*100, delta=0.5)

    def test_footer_outside_body_does_not_change_fill(self):
        self.assertEqual(self.scan([40,250]), self.scan([40,250,284,285]))

    def test_blank_body_reports_zero(self):
        self.assertEqual(self.scan([284,285])[0], 0)


if __name__ == '__main__':
    unittest.main()
