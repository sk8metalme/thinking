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
    def test_chapter_heading_classifier_ignores_case_studies_in_appendices(self):
        self.assertTrue(book.is_substantive_chapter("第1章　大会条件を読む"))
        self.assertTrue(book.is_substantive_chapter("Chapter 2 — Practice"))
        self.assertFalse(book.is_substantive_chapter("ケース1　主役を守る"))

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

    def test_parser_expands_a_range_when_it_is_combined_with_other_citations(self):
        parsed = book.parse_markdown_text("# Title\n\n本文 ［E-001〜E-003,E-005］")
        self.assertEqual(
            parsed.citations,
            frozenset({"E-001", "E-002", "E-003", "E-005"}),
        )

    def test_parser_retains_ordered_list_numbers(self):
        parsed = book.parse_markdown_text(
            "# Title\n> Subtitle\n\n1. First action\n2) Second action"
        )
        items = [block for block in parsed.blocks if block.kind == "list_item"]
        self.assertEqual([(item.marker, item.text) for item in items], [("1.", "First action"), ("2)", "Second action")])

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
        with self.assertRaisesRegex(ValueError, "malformed evidence range"):
            book._expand_citation_group("E-001〜not-an-id")
        self.assertEqual(book._expand_citation_group("no ID"), ())
        with self.assertRaisesRegex(ValueError, "count must not be negative"):
            book.daily_dates(count=-1)

    def test_parser_preserves_quote_rule_and_list_blocks(self):
        parsed = book.parse_markdown_text("# Title\n> Subtitle\n\n> Quote\n\n---\n\n- List item")
        self.assertEqual([block.kind for block in parsed.blocks], ["quote", "rule", "list_item"])

    def test_parser_supports_daily_lessons_nested_under_curriculum_units(self):
        parsed = book.parse_markdown_text(
            "# Title\n\n## Part\n\n### Chapter\n\n#### Unit\n\n"
            "##### 第001日 2026-10-04（日） Lesson\n\nFirst session.\n\n"
            "##### 第002日 2026-10-05（月） Next lesson\n\nSecond session."
        )
        daily = [block for block in parsed.blocks if block.kind == "heading" and block.text.startswith("第00")]
        self.assertEqual([block.level for block in daily], [4, 4])
        self.assertEqual(
            book._section_text(parsed.blocks, parsed.blocks.index(daily[0]), stop_level=4),
            "First session.",
        )

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
            if block.kind == "heading" and block.level == 2 and book.is_substantive_chapter(block.text)
        ]
        self.assertEqual(len(chapters), 32)
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
        for source in (
            "E-023", "E-024", "E-025", "E-026", "E-027", "E-028",
            "E-029", "E-030", "E-031", "E-032", "E-033", "E-034", "E-035", "E-036",
        ):
            self.assertIn(source, manuscript.citations)
            self.assertIn(source, {item[0] for item in book.EVIDENCE})
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
        self.assertIn("［E-001〜E-036］", manuscript.body_text)
        self.assertIn(
            "https://news.pokemon-home.com/ja/page/834.html",
            {item[4] for item in book.EVIDENCE if item[0] == "E-033"},
        )
        self.assertIn(
            "https://liberty-note.com/2026/09/28/gc2027-i-top150/",
            {item[4] for item in book.EVIDENCE if item[0] == "E-034"},
        )
        self.assertIn(
            "https://note.com/brave_snipe6636/n/nb48c2fbc77d4",
            {item[4] for item in book.EVIDENCE if item[0] == "E-035"},
        )
        self.assertIn(
            "https://note.com/gostraightvgc/n/n6e1611b3a6ec",
            {item[4] for item in book.EVIDENCE if item[0] == "E-036"},
        )
        self.assertIn("高順位の記事を「実績コピー」でなく、選出理由の設計図にする", manuscript.body_text)
        self.assertIn("GameWithの集計と、構築者の一件を同じ証拠にしない", manuscript.body_text)
        self.assertIn("完成例――「この候補を入れるべきか」を、答えられる問いに狭める", manuscript.body_text)
        self.assertIn("六つの対面を、出典の選出理由から練習手順へ変換する", manuscript.body_text)
        self.assertIn("候補がそろわない時――役割を保つ置換と、勝ち筋を変える置換", manuscript.body_text)
        self.assertIn("比較例――メガ枠を置換する前に、同じ課題へ二つの答えを作る", manuscript.body_text)
        for matchup in ("基本選出", "ライチュウ＋ニンフィア", "砂", "雨", "瞑想フラエッテ", "トリックルーム"):
            self.assertIn(matchup, manuscript.body_text)
        for proposal in "ABCD":
            self.assertIn(f"練習用4体選出{proposal}", manuscript.body_text)
            self.assertIn(f"{proposal}案の切替条件", manuscript.body_text)
        self.assertIn("2026年9月28日に終了", manuscript.body_text)
        daily_headings = re.findall(
            r"^##### 第(\d{3})日　(\d{4}-\d{2}-\d{2})（[月火水木金土日]）　(.+)$",
            book.MANUSCRIPT_PATH.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        self.assertEqual([int(day) for day, _, _ in daily_headings], list(range(1, 241)))
        self.assertEqual(
            [date.fromisoformat(day) for _, day, _ in daily_headings],
            book.daily_dates(),
        )
        self.assertEqual(len({title for _, _, title in daily_headings}), 240)
        daily_sections = [
            book._section_text(manuscript.blocks, index, stop_level=4)
            for index, block in enumerate(manuscript.blocks)
            if block.kind == "heading" and block.level == 4 and book.DAILY_HEADING_RE.fullmatch(block.text)
        ]
        self.assertEqual(len(daily_sections), 240)
        self.assertTrue(all("解説：" in section for section in daily_sections))
        for section in daily_sections:
            lengths = book._daily_lesson_part_lengths(section)
            for label, minimum in book.DAILY_LESSON_PART_MINIMUM_CHARS.items():
                self.assertGreaterEqual(lengths[label], minimum, label)
        units = [
            (index, block)
            for index, block in enumerate(manuscript.blocks)
            if block.kind == "heading" and block.level == 3 and block.text.startswith("学習ユニット")
        ]
        unit_texts = [book._section_text(manuscript.blocks, index, stop_level=4) for index, _ in units]
        self.assertEqual(len(units), 35)
        self.assertGreaterEqual(min(map(len, unit_texts)), 800)

    def test_validator_rejects_a_manuscript_missing_an_advertised_chapter(self):
        source = book.MANUSCRIPT_PATH.read_text(encoding="utf-8")
        heading = re.search(r"^### 第\d+章[^\n]*\n", source, flags=re.MULTILINE)
        self.assertIsNotNone(heading)
        shortened = source[:heading.start()] + source[heading.end():]
        with tempfile.TemporaryDirectory() as directory:
            manuscript_path = Path(directory) / "missing-chapter.md"
            manuscript_path.write_text(shortened, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected exactly 32 substantive chapters"):
                book.validate_source(manuscript_path)

    def test_validator_rejects_an_unexpected_curriculum_unit_count(self):
        source = book.MANUSCRIPT_PATH.read_text(encoding="utf-8")
        source = re.sub(r"^#### 学習ユニット35[^\n]*\n", "", source, count=1, flags=re.MULTILINE)
        with tempfile.TemporaryDirectory() as directory:
            manuscript_path = Path(directory) / "missing-unit.md"
            manuscript_path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected 35 instructional units"):
                book.validate_source(manuscript_path)

    def test_daily_lesson_measurement_skips_missing_parts_without_fabricating_length(self):
        lengths = book._daily_lesson_part_lengths("解説：一つの条件を観察する。")
        self.assertEqual(lengths, {"解説：": len(book.normalize("一つの条件を観察する。"))})

    def test_validator_rejects_duplicate_daily_titles(self):
        source = book.MANUSCRIPT_PATH.read_text(encoding="utf-8")
        headings = list(re.finditer(r"^##### 第\d{3}日[^\n]*$", source, flags=re.MULTILINE))
        first_title = headings[0].group(0).rsplit("　", 1)[1]
        second = headings[1]
        duplicate_heading = second.group(0).rsplit("　", 1)[0] + "　" + first_title
        source = source[:second.start()] + duplicate_heading + source[second.end():]
        with tempfile.TemporaryDirectory() as directory:
            manuscript_path = Path(directory) / "duplicate-session-title.md"
            manuscript_path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "daily session titles must be unique"):
                book.validate_source(manuscript_path)

    def test_validator_requires_all_named_daily_lesson_parts(self):
        source = book.MANUSCRIPT_PATH.read_text(encoding="utf-8")
        session = re.search(r"(?ms)(^##### 第001日[^\n]*\n)(.*?)(?=^##### 第002日)", source)
        self.assertIsNotNone(session)
        body = session.group(2).replace("目的：", "準備：", 1)
        source = source[:session.start(2)] + body + source[session.end(2):]
        with tempfile.TemporaryDirectory() as directory:
            manuscript_path = Path(directory) / "missing-session-part.md"
            manuscript_path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must state its objective"):
                book.validate_source(manuscript_path)

    def test_validator_rejects_duplicate_daily_session_content(self):
        source = book.MANUSCRIPT_PATH.read_text(encoding="utf-8")
        headings = list(re.finditer(r"^##### 第\d{3}日[^\n]*\n", source, flags=re.MULTILINE))
        first, second, third = headings[:3]
        first_body = source[first.end():second.start()]
        source = source[:second.end()] + first_body + source[third.start():]
        with tempfile.TemporaryDirectory() as directory:
            manuscript_path = Path(directory) / "duplicate-session.md"
            manuscript_path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "daily session content is duplicated"):
                book.validate_source(manuscript_path)

    def test_context_ledger_tables_have_consistent_column_counts(self):
        source = (book.ROOT / "output/pjcs2027-book/context-ledger.md").read_text(encoding="utf-8")
        tables = []
        current = []
        for line in source.splitlines() + [""]:
            if line.lstrip().startswith("|"):
                current.append(book._table_cells(line))
            elif current:
                tables.append(current)
                current = []
        self.assertTrue(tables)
        for table in tables:
            self.assertEqual(len({len(row) for row in table}), 1)

    def test_evidence_ledger_keeps_every_source_in_one_table(self):
        source = (book.ROOT / "output/pjcs2027-book/evidence-ledger.md").read_text(encoding="utf-8")
        start = source.index("| ID | 種別 |")
        lines = source[start:].splitlines()
        table_lines = []
        for line in lines:
            if not line.lstrip().startswith("|"):
                break
            table_lines.append(line)
        rows = [book._table_cells(line) for line in table_lines]
        self.assertEqual(len({len(row) for row in rows}), 1)
        identifiers = [row[0] for row in rows[2:]]
        self.assertEqual(identifiers, [f"E-{number:03d}" for number in range(1, 37)])

    def test_validator_accepts_a_concise_session_with_substantive_parts(self):
        manuscript = book.validate_source()
        blocks = list(manuscript.blocks)
        first_index = next(
            index for index, block in enumerate(blocks)
            if block.kind == "heading" and block.level == 4 and book.DAILY_HEADING_RE.fullmatch(block.text)
        )
        next_index = next(
            index for index in range(first_index + 1, len(blocks))
            if blocks[index].kind == "heading"
            and blocks[index].level == 4
            and book.DAILY_HEADING_RE.fullmatch(blocks[index].text)
        )
        compact_lesson = (
            "目的：二つの候補を比べ、判断に使う観察点を一つ定める。 "
            "解説：見えた事実と、自分が加えた予想は別々に扱う。結論だけを記録すると、条件が変わった時に判断を再現できない。"
            "何を比べるか先に決め、同じ条件を保ってから結果を読む。画面だけで分からない情報は未確認として残す。"
            "一回の結果を一般化せず、別の条件でも同じ問いを確かめる。 "
            "実習：二つの盤面を一つの条件だけ変えて比べ、予想、選んだ行動、その根拠を一文ずつ書く。"
            "相手の応答を二通り試し、どの観察で結論が変わるか残す。最後に判断を再現する手順を声に出して説明する。 "
            "振り返り：結果と判断理由を別欄に残し、次に検証する条件を一つ決め、その理由も記す。 "
            "対戦できない場合：画面や記録を使い、仮説と事実を分けて説明する。"
        )
        shortened = replace(
            manuscript,
            blocks=tuple(blocks[:first_index + 1] + [book.Block("paragraph", text=compact_lesson)] + blocks[next_index:]),
        )
        self.assertLess(len(book.normalize(compact_lesson)), 500)
        with patch.object(book, "parse_markdown_text", return_value=shortened):
            checked = book.validate_source()
        self.assertEqual(len(checked.blocks), len(shortened.blocks))

    def test_pdf_table_headers_have_explicit_high_contrast_paragraph_color(self):
        styles = book._make_styles("Helvetica")
        table = book._table_flowable(
            (("Header", "Value"), ("Row", "Detail")),
            240,
            styles["body"],
        )
        header = table._cellvalues[0][0].style.textColor
        self.assertEqual((header.red, header.green, header.blue), (1, 1, 1))

    def test_pdf_table_citations_are_clickable_links(self):
        styles = book._make_styles("Helvetica")
        table = book._table_flowable(
            (("Evidence",), ("Primary source [E-001]",)),
            240,
            styles["body"],
        )
        rendered_cell = table._cellvalues[1][0].text
        self.assertIn('<link href="https://champions-news.pokemon-home.com/ja/page/833.html"', rendered_cell)
        self.assertIn(">[E-001]</link>", rendered_cell)

    def test_pdf_story_keeps_ordered_list_markers(self):
        from reportlab.platypus import Paragraph

        manuscript = book.parse_markdown_text(
            "# Title\n> Subtitle\n\n## Part\n\n### Chapter\n\n1. First action\n2. Second action"
        )
        story = book._make_story(manuscript, book._make_styles("Helvetica"))
        rendered = [item.getPlainText() for item in story if isinstance(item, Paragraph)]
        self.assertIn("1. First action", rendered)
        self.assertIn("2. Second action", rendered)

    def test_pdf_story_keeps_evidence_when_paragraph_has_no_body_text(self):
        from reportlab.platypus import Paragraph

        manuscript = book.Manuscript(
            "Title",
            "Subtitle",
            (book.Block("paragraph", text="［E-001］"),),
            frozenset({"E-001"}),
            "E-001",
        )
        story = book._make_story(manuscript, book._make_styles("Helvetica"))
        rendered = [item.getPlainText() for item in story if isinstance(item, Paragraph)]
        self.assertIn("[E-001]", " ".join(rendered))

    def test_missing_japanese_font_has_an_actionable_error(self):
        from types import SimpleNamespace

        with patch.object(book.subprocess, "run", return_value=SimpleNamespace(stdout="")):
            with self.assertRaisesRegex(RuntimeError, "BIZ UDGothic is required"):
                book.find_font()

    def test_dates_cover_the_agreed_learning_period(self):
        dates = book.daily_dates()
        self.assertEqual(dates[0], date(2026, 10, 4))
        self.assertEqual(dates[-1], date(2027, 5, 31))
        self.assertEqual(len(dates), 240)
        self.assertTrue(all((right - left).days == 1 for left, right in zip(dates, dates[1:])))

    def test_build_rejects_a_pdf_below_the_user_requested_minimum(self):
        small = book.parse_markdown_text(
            "# Small book\n> Sample\n\n## Part\n\n### Chapter\n" + ("本文。" * 200)
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "too-short.pdf"
            with patch.object(book, "validate_source", return_value=small):
                with self.assertRaisesRegex(ValueError, "agreed minimum is 300"):
                    book.build_pdf(output)
            self.assertTrue(output.exists())

    def test_rendered_pdf_contains_links_outline_and_extractable_japanese(self):
        from pypdf import PdfReader

        book.validate_source()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "playbook.pdf"
            pages = book.build_pdf(output)
            self.assertGreaterEqual(pages, book.MINIMUM_BOOK_PAGES)
            self.assertGreater(output.stat().st_size, 50_000)
            extracted = book.extract_pdf_text(output)
            cover = extracted.split("\f")[0]
            self.assertIn("Pokémon ChampionsからPJCS2027へ", extracted)
            self.assertIn("基準日：2026年10月4日", cover)
            self.assertIn("第I部", extracted)
            self.assertIn("E-001", extracted)
            reader = PdfReader(str(output))
            self.assertIn("ISO B5, 176 x 250 mm", reader.metadata.subject)
            mediabox = reader.pages[0].mediabox
            self.assertAlmostEqual(float(mediabox.width), book.PAGE_WIDTH, places=2)
            self.assertAlmostEqual(float(mediabox.height), book.PAGE_HEIGHT, places=2)
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
        self.assertIn("chapters=32", printed.call_args.args[0])
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
            with self.assertRaisesRegex(ValueError, "exactly 32 substantive chapters"):
                book.validate_source(path)

            sparse = "# Title\n> Subtitle\n\n" + "\n".join(
                f"### Chapter {index}\nshort" for index in range(32)
            )
            path.write_text(sparse, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "too short"):
                book.validate_source(path)

            thin_chapter = "# Title\n> Subtitle\n\n### Chapter 1\n" + ("long text " * 3200)
            thin_chapter += "\n".join(f"\n### Chapter {index}\nshort" for index in range(2, 33))
            path.write_text(thin_chapter, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lacks explanatory substance"):
                book.validate_source(path)

            units = "\n".join(
                f"#### 学習ユニット{index:02d} テスト\n" + ("instructional text " * 90)
                for index in range(1, 36)
            )
            explanatory_text = "explanatory text " * 180
            duplicate_chapters = ["### Chapter 1\n" + explanatory_text] * 2
            duplicate_chapters += [
                f"### Chapter {index}\n" + explanatory_text
                for index in range(2, 32)
            ]
            duplicate = "# Title\n> Subtitle\n\n" + units + "\n" + "\n".join(duplicate_chapters)
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "heading titles must be unique"):
                book.validate_source(path)

    def test_validator_rejects_a_curriculum_unit_without_teaching_text(self):
        source = book.MANUSCRIPT_PATH.read_text(encoding="utf-8")
        unit_heading = "#### 学習ユニット01　資格条件を操作へ落とす\n"
        unit_start = source.index(unit_heading) + len(unit_heading)
        first_lesson = source.index("##### 第001日　", unit_start)
        source = source[:unit_start] + "\n短い説明だけ。\n\n" + source[first_lesson:]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manuscript.md"
            path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "curriculum unit lacks explanatory substance"):
                book.validate_source(path)

    def test_validator_rejects_bad_daily_schedule_and_evidence_ledgers(self):
        manuscript = book.validate_source()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manuscript.md"
            path.write_text(book.MANUSCRIPT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            last_daily = next(
                block for block in manuscript.blocks
                if block.kind == "heading" and block.level == 4 and block.text.startswith("第240日　")
            )
            missing_day = replace(
                manuscript,
                blocks=tuple(block for block in manuscript.blocks if block is not last_daily),
            )
            with patch.object(book, "parse_markdown_text", return_value=missing_day):
                with self.assertRaisesRegex(ValueError, "expected 240 daily sessions"):
                    book.validate_source(path)

            first_daily = next(
                block for block in manuscript.blocks
                if block.kind == "heading" and block.level == 4 and block.text.startswith("第001日　")
            )
            bad_first = replace(first_daily, text=first_daily.text.replace("2026-10-04", "2026-10-05"))
            bad_schedule = replace(
                manuscript,
                blocks=tuple(bad_first if block is first_daily else block for block in manuscript.blocks),
            )
            with patch.object(book, "parse_markdown_text", return_value=bad_schedule):
                with self.assertRaisesRegex(ValueError, "daily session 1 does not match"):
                    book.validate_source(path)

            bad_weekday = replace(first_daily, text=first_daily.text.replace("（日）", "（月）"))
            wrong_weekday_schedule = replace(
                manuscript,
                blocks=tuple(bad_weekday if block is first_daily else block for block in manuscript.blocks),
            )
            with patch.object(book, "parse_markdown_text", return_value=wrong_weekday_schedule):
                with self.assertRaisesRegex(ValueError, "incorrect weekday"):
                    book.validate_source(path)

            first_index = manuscript.blocks.index(first_daily)
            body_index = next(
                index for index in range(first_index + 1, len(manuscript.blocks))
                if manuscript.blocks[index].kind in {"paragraph", "list_item"}
            )
            thin_blocks = list(manuscript.blocks)
            thin_blocks[body_index] = replace(
                thin_blocks[body_index],
                text="目的：短い。解説：短い。実習：短い。振り返り：短い。対戦できない場合：短い。",
            )
            thin_session = replace(manuscript, blocks=tuple(thin_blocks))
            with patch.object(book, "parse_markdown_text", return_value=thin_session):
                with self.assertRaisesRegex(ValueError, "daily session lacks instructional substance"):
                    book.validate_source(path)

            missing_core_source = replace(manuscript, citations=manuscript.citations - {"E-003"})
            with patch.object(book, "parse_markdown_text", return_value=missing_core_source):
                with self.assertRaisesRegex(ValueError, "required official and case-study sources"):
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
