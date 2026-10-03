import tempfile
import unittest
from datetime import date
from pathlib import Path

from tools import build_pjcs2027_playbook as book


class PlaybookSourceTest(unittest.TestCase):
    def test_source_contract(self):
        book.validate_source()
        self.assertEqual(len(book.MODULES), 35)
        self.assertEqual(len(book.PLANS), 4)
        self.assertEqual(len(book.WEEKLY_FOCUS), 35)
        self.assertEqual(len(book.APPENDIX_PAGES), 25)

    def test_dates_cover_the_agreed_period(self):
        dates = book.weekly_dates()
        self.assertEqual(dates[0], date(2026, 10, 3))
        self.assertEqual(dates[-1], date(2027, 5, 29))
        self.assertEqual(len(dates), 35)

    def test_normalize_supports_duplicate_audit(self):
        self.assertEqual(book.normalize(" A　B。\n"), "AB")

    def test_build_pdf_from_source(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "playbook.pdf"
            pages = book.build_pdf(output)
            self.assertEqual(pages, 324)
            self.assertGreater(output.stat().st_size, 100_000)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
