import hashlib
import re
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tools import build_pjcs2027_playbook as book


class ManuscriptParserTest(unittest.TestCase):
    def test_parser_preserves_reading_structure_and_inline_evidence(self):
        source = """# 本の題名
> 副題

## 第I部　入口

### 1章　確認する

最初の段落。 [E-001]

#### 事実と判断

- 一つ目
- 二つ目

| 見る | 理由 |
| --- | --- |
| 日付 | 更新される |
"""
        parsed = book.parse_markdown_text(source)
        self.assertEqual(parsed.title, "本の題名")
        self.assertEqual(parsed.subtitle, "副題")
        self.assertEqual(
            [(block.kind, block.level, block.text) for block in parsed.blocks if block.kind == "heading"],
            [("heading", 1, "第I部　入口"), ("heading", 2, "1章　確認する"), ("heading", 3, "事実と判断")],
        )
        self.assertEqual(sum(block.kind == "list_item" for block in parsed.blocks), 2)
        self.assertEqual(sum(block.kind == "table" for block in parsed.blocks), 1)
        self.assertIn("E-001", parsed.citations)

    def test_parser_rejects_unknown_evidence_ids(self):
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            book.parse_markdown_text("# Title\n\n本文 [E-999]", evidence_ids={"E-001"})

    def test_parser_expands_evidence_ranges(self):
        parsed = book.parse_markdown_text("# Title\n\n本文 ［E-001〜E-003］")
        self.assertEqual(parsed.citations, frozenset({"E-001", "E-002", "E-003"}))

    def test_parser_rejects_unclosed_or_malformed_table(self):
        with self.assertRaisesRegex(ValueError, "table"):
            book.parse_markdown_text("# Title\n\n| A | B |\n| --- |")

    def test_parser_rejects_invalid_markdown_edges(self):
        with self.assertRaisesRegex(ValueError, "level-one title"):
            book.parse_markdown_text("## Not a title")
        with self.assertRaisesRegex(ValueError, "raw HTML"):
            book.parse_markdown_text("# Title\n\n<div>raw</div>")
        with self.assertRaisesRegex(ValueError, "table needs"):
            book.parse_markdown_text("# Title\n\n| only one row |")
        with self.assertRaisesRegex(ValueError, "separator row"):
            book.parse_markdown_text("# Title\n\n| A | B |\n| no |")
        with self.assertRaisesRegex(ValueError, "same number of columns"):
            book.parse_markdown_text("# Title\n\n| A | B |\n| --- | --- |\n| only one |")
        with self.assertRaisesRegex(ValueError, "malformed table row"):
            book.parse_markdown_text("# Title\n\n| A | B |\n| --- | --- |\n| no closing bar")
        with self.assertRaisesRegex(ValueError, "reversed"):
            book.parse_markdown_text("# Title\n\n本文 ［E-003〜E-001］")
        self.assertEqual(book._expand_citation_group("no ID"), ())
        with self.assertRaisesRegex(ValueError, "count must not be negative"):
            book.weekly_dates(count=-1)

    def test_parser_preserves_quote_rule_and_list_blocks(self):
        parsed = book.parse_markdown_text("# Title\n> Subtitle\n\n> Quote\n\n---\n\n- List item")
        self.assertEqual([block.kind for block in parsed.blocks], ["quote", "rule", "list_item"])

    def test_story_builder_handles_quote_rule_and_unknown_block(self):
        parsed = book.parse_markdown_text("# Title\n> Subtitle\n\n> Quote [E-001]\n\n---")
        styles = book._make_styles("Helvetica")
        story = book._make_story(parsed, styles)
        self.assertGreater(len(story), 8)
        invalid = book.Manuscript("T", "S", (book.Block("unknown"),), frozenset(), "")
        with self.assertRaisesRegex(ValueError, "unsupported manuscript block"):
            book._make_story(invalid, styles)


class PlaybookSourceTest(unittest.TestCase):
    def test_source_contract_is_a_sequential_book_not_a_page_template_set(self):
        manuscript = book.validate_source()
        chapters = [
            block for block in manuscript.blocks
            if block.kind == "heading" and block.level == 2
        ]
        self.assertGreaterEqual(len(chapters), 14)
        self.assertGreaterEqual(len(manuscript.body_text), 30_000)
        self.assertGreaterEqual(len(book.EVIDENCE), 8)
        self.assertEqual(len({item[0] for item in book.EVIDENCE}), len(book.EVIDENCE))
        self.assertIn("E-001", manuscript.citations)
        self.assertIn("E-010", manuscript.citations)
        self.assertIn("E-013", manuscript.citations)
        self.assertIn("E-014", manuscript.citations)
        self.assertIn("E-015", manuscript.citations)
        self.assertIn("E-015", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-016", manuscript.citations)
        self.assertIn("E-016", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-017", manuscript.citations)
        self.assertIn("E-017", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-018", manuscript.citations)
        self.assertIn("E-018", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-019", manuscript.citations)
        self.assertIn("E-019", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-020", manuscript.citations)
        self.assertIn("E-020", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-021", manuscript.citations)
        self.assertIn("E-021", {item[0] for item in book.EVIDENCE})
        self.assertIn("E-022", manuscript.citations)
        self.assertIn("E-022", {item[0] for item in book.EVIDENCE})
        self.assertIn("実戦の再生", manuscript.body_text)
        self.assertIn("映像で確認できる事実", manuscript.body_text)
        self.assertIn("ここから導く解釈", manuscript.body_text)
        self.assertIn("反実仮想", manuscript.body_text)
        self.assertIn("アクアジェット", manuscript.body_text)
        self.assertIn("ふいうち", manuscript.body_text)
        self.assertIn("M-Bの歴史的な対戦読解", manuscript.body_text)
        self.assertIn("M-Cの推奨としては使わない", manuscript.body_text)
        for case_heading in (
            "実例の再生――一体が倒れても、残HPと勝ち筋を数える",
            "実例の再生――優先度と速度を分けて読む",
            "一つの盤面で比べる――守る・交代・攻撃",
            "三ターンの仮想対戦を、勝敗ではなく選択肢から追う",
            "低速計画の再生――T0からT2へ",
            "条件案の再生――準備を止める分岐",
        ):
            self.assertIn(case_heading, manuscript.body_text)
        self.assertIn("［E-001〜E-022］", manuscript.body_text)
        for proposal in "ABCD":
            self.assertIn(f"練習用4体選出{proposal}", manuscript.body_text)
            self.assertIn(f"{proposal}案の切替条件", manuscript.body_text)
        self.assertIn("2026年9月28日に終了", manuscript.body_text)
        weekly_headings = re.findall(
            r"^#### 第(\d{2})週　(.+)$",
            book.MANUSCRIPT_PATH.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        self.assertEqual([int(week) for week, _ in weekly_headings], list(range(1, 36)))

    def test_pdf_table_headers_have_explicit_high_contrast_paragraph_color(self):
        styles = book._make_styles("Helvetica")
        table = book._table_flowable(
            (("Header", "Value"), ("Row", "Detail")),
            240,
            styles["body"],
        )
        header = table._cellvalues[0][0].style.textColor
        self.assertEqual((header.red, header.green, header.blue), (1, 1, 1))

    def test_dates_cover_the_agreed_learning_period(self):
        dates = book.weekly_dates()
        self.assertEqual(dates[0], date(2026, 10, 3))
        self.assertEqual(dates[-1], date(2027, 5, 29))
        self.assertEqual(len(dates), 35)

    def test_rendered_pdf_contains_links_outline_and_extractable_japanese(self):
        book.validate_source()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "playbook.pdf"
            pages = book.build_pdf(output)
            self.assertGreater(pages, 40)
            self.assertGreater(output.stat().st_size, 50_000)
            extracted = book.extract_pdf_text(output)
            cover = extracted.split("\f")[0]
            self.assertIn("Pokémon ChampionsからPJCS2027へ", extracted)
            self.assertIn("基準日：2026年10月4日", cover)
            self.assertIn("第I部", extracted)
            self.assertIn("E-001", extracted)
            self.assertGreaterEqual(book.count_pdf_links(output), 8)
            self.assertGreaterEqual(book.count_pdf_outlines(output), 14)

    def test_pdf_build_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.pdf"
            second = Path(directory) / "second.pdf"
            book.build_pdf(first)
            book.build_pdf(second)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )

    def test_evidence_index_keeps_clickable_sources_without_orphaning_final_rows(self):
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "book.pdf"
            book.build_pdf(output)
            pages = [page for page in book.extract_pdf_text(output).split("\f") if page.strip()]
            final_page_ids = set(re.findall(r"E-\d{3}", pages[-1]))
            self.assertGreaterEqual(len(final_page_ids), 4)

            reader = PdfReader(str(output))
            linked_urls = {
                annotation.get_object().get("/A", {}).get("/URI")
                for page in reader.pages
                for annotation in page.get("/Annots", [])
                if annotation.get_object().get("/Subtype") == "/Link"
            }
            self.assertTrue({item[4] for item in book.EVIDENCE}.issubset(linked_urls))

    def test_validate_only_cli_reports_real_source_measurements(self):
        with patch("sys.argv", ["build_pjcs2027_playbook.py", "--validate-only"]):
            with patch("builtins.print") as printed:
                self.assertEqual(book.main(), 0)
        self.assertIn("chapters=", printed.call_args.args[0])
        self.assertIn("characters=", printed.call_args.args[0])

    def test_story_only_forces_cover_and_toc_page_breaks(self):
        parsed = book.parse_markdown_text(
            "# Title\n> Subtitle\n\n## 第I部\n\n### 第一章\n本文\n\n## 第II部\n\n### 第二章\n続き"
        )
        story = book._make_story(parsed, book._make_styles("Helvetica"))
        page_breaks = [item for item in story if item.__class__.__name__ == "PageBreak"]
        self.assertEqual(len(page_breaks), 3)

    def test_validator_rejects_missing_context_and_thin_chapters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manuscript.md"
            path.write_text("# Title\n本文", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "subtitle"):
                book.validate_source(path)

            path.write_text("# Title\n> Subtitle\n\n### One\n" + ("text" * 40), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "at least 14"):
                book.validate_source(path)

            sparse = "# Title\n> Subtitle\n\n" + "\n".join(
                f"### Chapter {index}\nshort" for index in range(14)
            )
            path.write_text(sparse, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "too short"):
                book.validate_source(path)

            thin_chapter = "# Title\n> Subtitle\n\n### Chapter 1\n" + ("long text " * 3200)
            thin_chapter += "\n".join(f"\n### Chapter {index}\nshort" for index in range(2, 15))
            path.write_text(thin_chapter, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lacks explanatory substance"):
                book.validate_source(path)

            duplicate = "# Title\n> Subtitle\n\n" + "\n".join(
                "### Repeated\n" + ("explanatory text " * 180) for _ in range(14)
            )
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "heading titles must be unique"):
                book.validate_source(path)

    def test_validator_rejects_bad_schedule_and_evidence_ledgers(self):
        manuscript = book.validate_source()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manuscript.md"
            path.write_text(book.MANUSCRIPT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            tables = [block for block in manuscript.blocks if block.kind == "table"]
            weekly = next(block for block in tables if block.rows[0][0] == "週・日付")

            missing_table = replace(
                manuscript,
                blocks=tuple(block for block in manuscript.blocks if block is not weekly),
            )
            with patch.object(book, "parse_markdown_text", return_value=missing_table):
                with self.assertRaisesRegex(ValueError, "exactly one 35-week"):
                    book.validate_source(path)

            short_weekly = replace(weekly, rows=weekly.rows[:-1])
            short_schedule = replace(
                manuscript,
                blocks=tuple(short_weekly if block is weekly else block for block in manuscript.blocks),
            )
            with patch.object(book, "parse_markdown_text", return_value=short_schedule):
                with self.assertRaisesRegex(ValueError, "expected 35 weekly"):
                    book.validate_source(path)

            bad_first = (weekly.rows[1][0].replace("10/03", "10/04"), *weekly.rows[1][1:])
            bad_rows = (weekly.rows[0], bad_first, *weekly.rows[2:])
            bad_schedule = replace(
                manuscript,
                blocks=tuple(replace(weekly, rows=bad_rows) if block is weekly else block for block in manuscript.blocks),
            )
            with patch.object(book, "parse_markdown_text", return_value=bad_schedule):
                with self.assertRaisesRegex(ValueError, "schedule row 1"):
                    book.validate_source(path)

            missing_core_source = replace(manuscript, citations=manuscript.citations - {"E-003"})
            with patch.object(book, "parse_markdown_text", return_value=missing_core_source):
                with self.assertRaisesRegex(ValueError, "core official sources"):
                    book.validate_source(path)

            with patch.object(book, "EVIDENCE", book.EVIDENCE + [book.EVIDENCE[0]]):
                with self.assertRaisesRegex(ValueError, "evidence IDs must be unique"):
                    book.validate_source(path)

            invalid_entry = (*book.EVIDENCE[0][:-1], "http://not-secure.example")
            with patch.object(book, "EVIDENCE", [invalid_entry, *book.EVIDENCE[1:]]):
                with self.assertRaisesRegex(ValueError, "incomplete evidence record"):
                    book.validate_source(path)

    def test_missing_reportlab_has_a_useful_error(self):
        import builtins

        original_import = builtins.__import__

        def without_reportlab(name, *args, **kwargs):
            if name.startswith("reportlab"):
                raise ImportError("test: unavailable")
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            with patch("builtins.__import__", side_effect=without_reportlab):
                with self.assertRaisesRegex(RuntimeError, "install reportlab"):
                    book.build_pdf(Path(directory) / "unused.pdf")

    def test_build_cli_writes_the_requested_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cli.pdf"
            with patch("sys.argv", ["build_pjcs2027_playbook.py", "--output", str(output)]):
                with patch("builtins.print") as printed:
                    self.assertEqual(book.main(), 0)
            self.assertTrue(output.exists())
            self.assertIn("built", printed.call_args.args[0])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
