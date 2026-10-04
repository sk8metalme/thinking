#!/usr/bin/env python3
"""Build the PJCS2027 guide as a flowing book from its Markdown manuscript."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_PATH = ROOT / "output/pjcs2027-book/manuscript.md"
PAGE_WIDTH = 498.898
PAGE_HEIGHT = 708.661
MARGIN_LEFT = 48
MARGIN_RIGHT = 48
MARGIN_TOP = 48
MARGIN_BOTTOM = 46
MINIMUM_BOOK_PAGES = 300
TARGET_BOOK_PAGES = 300
EXPECTED_CHAPTER_COUNT = 32
MINIMUM_UNIT_INSTRUCTION_CHARS = 800
DAILY_LESSON_PART_MINIMUM_CHARS = {
    "目的：": 20,
    "解説：": 120,
    "実習：": 65,
    "振り返り：": 30,
    "対戦できない場合：": 20,
}
EVIDENCE = [
    (
        "E-001",
        "official",
        "『Pokémon Champions』チャンピオンシップシリーズ「2027シーズン」について",
        "PJCS2027の対象ルート、居住国とゲーム内設定、日本の各カテゴリ上位120名、複数アカウントの注意、権利獲得アカウント、年齢区分、Global Challenge I〜VIと5月予選の案内。",
        "https://champions-news.pokemon-home.com/ja/page/833.html",
    ),
    (
        "E-002",
        "official",
        "「グローバルチャレンジ2027 I」開催！",
        "第I回の登録期間・開催期間・登録時のチーム情報の扱い・M-Cダブル・参加条件。第II回の個別条件を確定する資料としては使わない。",
        "https://champions-news.pokemon-home.com/ja/page/825.html",
    ),
    (
        "E-003",
        "official",
        "Pokémon Champions: Assembling Your Ideal Team",
        "Pokémon HOMEからの訪問、Roster Ranch、トライアル採用、VP・チケット、育成の公式案内。",
        "https://champions.pokemon.com/en-us/pokemon/",
    ),
    (
        "E-004",
        "official",
        "Play! Pokémon VGC Tournament Handbook",
        "対戦チーム、提出情報、イベント運営などの公式Handbook。確認した版は2026年5月21日改訂。大会固有の告知が優先。",
        "https://mcdn.pokemon.com/pokemon-prod/raw/upload/v1/live/static-assets/content-assets/cms2/pdf/play-pokemon/rules/play-pokemon-vgc-tournament-handbook-en.pdf",
    ),
    (
        "E-005",
        "official",
        "Global Challenge 2027 I announcement",
        "公式英語告知。地域・大会ごとの案内を照合する補助資料。日本向けの参加条件はE-001を優先。",
        "https://www.pokemon.com/us/news/take-on-the-2027-global-challenge-i",
    ),
    (
        "E-006",
        "official",
        "Regulation Set M-C (Updated on September 9)",
        "M-Cの期間、対象ポケモン参照先、メガシンカ、持ち物制限、タイマー。開催時点のゲーム内表示で再確認。",
        "https://champions-news.pokemon-home.com/en/page/816.html",
    ),
    (
        "E-007",
        "official",
        "The 2027 Global Challenge I & II Special Roster",
        "Global Challenge I・II向けの特別スカウト対象例。対象リスト全体ではなく、M-Cの全合法性を証明するものでもない。",
        "https://champions-news.pokemon-home.com/en/page/834.html",
    ),
    (
        "E-008",
        "official",
        "Get Ready for Regulation Set M-C in Pokémon Champions",
        "公式ニュース一覧に掲載されたM-C告知。詳細な大会条件はゲーム内規則と個別告知を優先。",
        "https://www.pokemon.com/us/news/get-ready-for-regulation-set-m-c-in-pokemon-champions",
    ),
    (
        "E-009",
        "official strategy",
        "Pokémon Champions: How to Build a Mega Emboar Team",
        "公式の構築解説。記事掲載時のルール・セットを学ぶ歴史的な教材例であり、M-Cの大会用チームとして再利用しない。",
        "https://www.pokemon.com/us/strategy/pokemon-champions-how-to-build-a-mega-emboar-team",
    ),
    (
        "E-010",
        "official strategy",
        "Pokémon Champions: How to Build a Mega Malamar Team",
        "公式の構築解説。能力変化と補助役の読み方を学ぶ教材例であり、M-Cの合法性を保証しない。",
        "https://www.pokemon.com/uk/features/pokemon-champions-how-to-build-a-mega-malamar-team",
    ),
    (
        "E-011",
        "secondary",
        "GameWith: Global Challenge 2027 I results and rewards",
        "2026-10-03更新の結果・報酬・画面導線。本文のGC I開催年に公式告知との不一致があるため、開催条件・上位120名は公式告知を優先する。",
        "https://gamewith.jp/pokemon-champions/575795",
    ),
    (
        "E-012",
        "official",
        "Pokémon Champions official news archive",
        "規則・イベント・更新の公式ニュース一覧。基準日後の変更を調べる入口。",
        "https://champions.pokemon.com/en-us/news/",
    ),
    (
        "E-013",
        "official",
        "2027 Pokémon Brisbane Regional Championships Event Results",
        "Brisbane Regionalの公式順位と参加カテゴリ・参加人数。チームの技セットの根拠にはしない。",
        "https://www.pokemon.com/uk/play-pokemon/regionals/2027/brisbane/event-results",
    ),
    (
        "E-014",
        "secondary",
        "Limitless VGC: Regional Brisbane — Teams",
        "2026-09-26 M-C大会の上位選手が公開したチームの種族・技・特性・持ち物・性格。公式出典ではなく、能力値配分や日本のオンライン大会での成績を保証しない。",
        "https://limitlessvgc.com/tournaments/442/teams",
    ),
    (
        "E-015",
        "official",
        "Pokémon Champions: September 9, 2026 Update Notice",
        "バトル中の行動履歴を確認する『ログを見る』と、バトルデータを元に選出画面へ情報を表示する『選出サポート』の追加。",
        "https://champions-news.pokemon-home.com/ja/page/817.html",
    ),
    (
        "E-016",
        "official",
        "Pokémon Champions Version 1.0.3 Update Notice",
        "特性の発動順へ持ち物による素早さ変化が反映されない不具合の修正など、過去の更新記録。現行挙動の説明には使わない。",
        "https://champions-news.pokemon-home.com/ja/page/764.html",
    ),
    (
        "E-017",
        "official",
        "「スタンダードセレクトM-C」について",
        "2026年9月9日〜12月2日の開催期間、このセレクトで新たに紹介されるポケモン、ゲーム内の紹介対象一覧への案内。掲載種族だけをM-C全体の対象リストとはみなさない。",
        "https://champions-news.pokemon-home.com/ja/page/821.html",
    ),
    (
        "E-018",
        "official",
        "Pokémon Champions | Gameplay",
        "ランク・カジュアル・プライベートの各対戦モード、シングル・ダブル、ランク変動とVP、シーズンごとのルール更新についての公式概要。",
        "https://champions.pokemon.com/en-us/gameplay/",
    ),
    (
        "E-019",
        "official interview",
        "Champion’s Spotlight: Paul Chua’s Consistency Reigns True",
        "2026年6月の公式選手インタビュー。VPによる育成、同種族間で個体の強さが異ならない設計、HOME連携への選手コメント。個人の発言を全プレイヤーの勝率・最適構築の根拠にはしない。",
        "https://www.pokemon.com/uk/features/champions-spotlight-paul-chuas-consistency-reigns-true",
    ),
    (
        "E-020",
        "official basics",
        "Pokémon RPGs 101",
        "ポケモンシリーズ全般の基本用語（六つの能力値、物理・特殊・状態技）の入門説明。Pokémon Champions固有の技効果・表示・大会条件の根拠にはせず、現行ゲーム内の説明を優先。",
        "https://www.pokemon.com/us/strategy/pokemon-rpgs-101/",
    ),
    (
        "E-021",
        "official video",
        "2026 Pokémon World Championships VGC Masters Final — Japanese official broadcast",
        "第1ゲーム序盤の行動を映像で確認する一次資料。配信時刻6:12前後（動画位置約6:12:01〜6:15:30）。選出や行動理由を全て確定する対戦ログではないため、画面・実況で確認できる範囲と解釈を分ける。",
        "https://www.youtube.com/watch?v=K7Io6JvtB1Y&t=22321s",
    ),
    (
        "E-022",
        "official",
        "2026 Pokémon World Championships VGC Masters Division",
        "WCS 2026 Mastersの規則セットがM-Bで、対戦にPokémon Championsを使用したこと、決勝進出者と公開チームを確認する公式ページ。E-021の映像を歴史的大会事例として位置づける根拠。",
        "https://www.pokemon.com/uk/play-pokemon/worlds/2026/vgc-masters",
    ),
    (
        "E-023",
        "secondary",
        "GameWith: Pokémon Champions double team ranking",
        "GameWith編集部による二次評価。2026-10-01更新、10-04確認。掲載Tierは編集上の比較で、公式大会順位・使用率統計・初心者向け最適解を意味しない。",
        "https://gamewith.jp/pokemon-champions/558167",
    ),
    (
        "E-024",
        "secondary",
        "GameWith: Mega Golisopod build and counters",
        "2026-10-03更新。M-6ダブルの集計日は10-02。技・持ち物の個別割合であり、同時採用・勝率を示さず、参照箇所に分母・母集団の説明はない。",
        "https://gamewith.jp/pokemon-champions/575652",
    ),
    (
        "E-025",
        "community self-report",
        "KEIBO: Dual Weather Psycho Beat (self-reported 110th place)",
        "2026-09-29公開の本人執筆note。順位・対戦経験は自己申告。雨・天候・選出案・苦手対面の説明を、構築仮説と反証の学習例として要約する。公式順位確認とは別の根拠。",
        "https://note.com/keibo_poke/n/nbbdf60b8f705",
    ),
    (
        "E-026",
        "community self-report",
        "Beiri: Global Challenge 2027 I reflection",
        "2026-09-28公開の本人執筆note。構築変更、対面理解、練習量、本人の結果認識を振り返るケース。順位・因果関係は独立検証されておらず、本人の評価として扱う。",
        "https://note.com/beiry_note/n/n656ddd3b9eac",
    ),
    (
        "E-027",
        "community video",
        "CybertronVGC: Mega Salamence is BACK & ALREADY WON a tournament",
        "2026-09-13公開の英語動画。構築の使い方・弱点の説明と対戦映像を教材にする。動画内の大会実績・制作者説明は公式結果で照合できた範囲以外、投稿者の説明として扱う。",
        "https://www.youtube.com/watch?v=mo-qCv7wfD4",
    ),
    (
        "E-028",
        "community self-report",
        "k-moou: Global Challenge 2027 I reflection",
        "2026-09-29公開の本人執筆note。上位配信者の構築観察を重視した準備、採用構築、自己申告の結果を読む。観察情報の偏りと本人の経験を区別する教材。",
        "https://note.com/k_moou/n/nc29d78e63fef",
    ),
    (
        "E-029",
        "official",
        "『Pokémon Champions』バトルについて",
        "ランク・カジュアル・プライベートの3モード、各モードのシングル・ダブル、シーズン・レギュレーション、VPについての日本語公式概要。",
        "https://www.pokemonchampions.jp/ja/battle/",
    ),
    (
        "E-030",
        "community self-report",
        "りべら: はじめてのグローバルチャレンジ！",
        "2026-09-29公開。初めての競技対戦からGC Iへ参加した経験、本人申告の45戦27勝18敗・約12,000位／約336,000人、チーム変更の理由と反省。大会条件は本人も曖昧と記しているため、公式情報の根拠にしない。",
        "https://note.com/libera44/n/n65ad9318b3ea",
    ),
    (
        "E-031",
        "community self-report",
        "あんせむ: グローバルチャレンジ2027 I 166位 最終レート1806 フラエッテスタン",
        "2026-09-29公開。構築の準備・選出・反省を扱う本人執筆記事。タイトルと前半は166位、終盤は日本人116位と記載が食い違うため、順位は自己申告の不整合を含む未確認情報としてのみ教材にする。",
        "https://note.com/4n__7hem/n/n4d2892c7842c",
    ),
    (
        "E-032",
        "community video",
        "TheBattleRoom: This World Champion’s Mega Salamence Team is BUSTED",
        "2026-09公開の英語動画。チーム解説と複数の対戦映像を、役割・説明・画面上の事実を分けて読む教材。動画の評価や大会実績を独立した公式結果として扱わない。",
        "https://www.youtube.com/watch?v=WT0IArOek0s",
    ),
    (
        "E-033",
        "official",
        "Pokémon HOME: Special Select Global Challenge 2027 I & II",
        "2026-09-18〜09-28 10:59の公式特別セレクト告知。対象ポケモン例と開催期間を示す。終了後の入手可能性、M-C全体の対象一覧、次回大会の合法性は示さない。",
        "https://news.pokemon-home.com/ja/page/834.html",
    ),
    (
        "E-034",
        "secondary compilation",
        "Liberty Note: Global Challenge 2027 I Top 150",
        "2026-09-28公開、10-02更新。マスターカテゴリ上位として掲載した順位と一部の6体を集約する二次資料。公式順位の確定、掲載の完全性、技・特性・持ち物・選出・採用理由を保証しない。",
        "https://liberty-note.com/2026/09/28/gc2027-i-top150/",
    ),
    (
        "E-035",
        "community self-report",
        "らむじゃがー: Global Challenge 2027 I 雨滅びパ アブソルを添えて",
        "2026-09-28公開の本人構築記事。45戦30勝15敗・最終1491位を本人申告し、雨・滅び軸の構築変更、選出、技選択の反省を記す。順位・成績は公式確認ではなく、変更と結果の因果も証明しない。",
        "https://note.com/brave_snipe6636/n/nb48c2fbc77d4",
    ),
    (
        "E-036",
        "community self-report",
        "直線: Global Challenge 2027 I 62位・最終レート1816.742",
        "本人の構築変更・相手別選出・苦手対面の説明。順位・予選進出は独立確認されず、変更との因果や環境全体の分布も示さない。",
        "https://note.com/gostraightvgc/n/n6e1611b3a6ec",
    ),
]
EVIDENCE_BY_ID = {item[0]: item for item in EVIDENCE}
CITATION_RE = re.compile(r"[\[［]((?:E-\d{3})(?:\s*[,、〜～\-]\s*E-\d{3})*)[\]］]")
EVIDENCE_TOKEN_RE = re.compile(r"E-\d{3}")
HEADING_RE = re.compile(r"^(#{2,5})\s+(.+?)\s*$")
DAILY_HEADING_RE = re.compile(r"^第(\d{3})日　(\d{4}-\d{2}-\d{2})（([月火水木金土日])）　(.+)$")
CHAPTER_HEADING_RE = re.compile(r"^(?:第\d+章(?:　|\s|[:：])|Chapter\s+\d+\b)", re.IGNORECASE)
LIST_RE = re.compile(r"^\s*(?:(\d+[.)])|[-*+])\s+(.+)$")


@dataclass(frozen=True)
class Block:
    kind: str
    text: str = ""
    level: int = 0
    rows: tuple[tuple[str, ...], ...] = ()
    marker: str = ""


@dataclass(frozen=True)
class Manuscript:
    title: str
    subtitle: str
    blocks: tuple[Block, ...]
    citations: frozenset[str]
    body_text: str


def daily_dates(start: date = date(2026, 10, 4), count: int = 240) -> list[date]:
    """Return the agreed daily study dates, inclusive of both endpoints."""
    if count < 0:
        raise ValueError("count must not be negative")
    return [start + timedelta(days=index) for index in range(count)]


def normalize(text: str) -> str:
    """Normalize Japanese whitespace and punctuation for duplicate checks."""
    return re.sub(r"[\s　、。・:：,.!?！？]+", "", text)


def _table_cells(line: str) -> tuple[str, ...]:
    if not line.strip().startswith("|") or not line.strip().endswith("|"):
        raise ValueError(f"malformed table row: {line}")
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _citation_ids(text: str) -> set[str]:
    identifiers: set[str] = set()
    for match in CITATION_RE.finditer(text):
        identifiers.update(_expand_citation_group(match.group(1)))
    return identifiers


def _expand_citation_group(group: str) -> tuple[str, ...]:
    identifiers: list[str] = []
    for segment in re.split(r"\s*[,、]\s*", group):
        tokens = EVIDENCE_TOKEN_RE.findall(segment)
        if not tokens:
            continue
        if re.search(r"[〜～]", segment):
            if len(tokens) != 2:
                raise ValueError(f"malformed evidence range: {segment}")
            first = int(tokens[0].split("-")[1])
            last = int(tokens[1].split("-")[1])
            if last < first:
                raise ValueError(f"evidence range is reversed: {segment}")
            identifiers.extend(f"E-{number:03d}" for number in range(first, last + 1))
        else:
            identifiers.extend(tokens)
    return tuple(dict.fromkeys(identifiers))


def parse_markdown_text(source: str, evidence_ids: Iterable[str] | None = None) -> Manuscript:
    """Parse the deliberately small Markdown subset used by the manuscript."""
    lines = source.splitlines()
    first = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first is None or not lines[first].startswith("# "):
        raise ValueError("manuscript must begin with a level-one title")
    title = lines[first][2:].strip()
    cursor = first + 1
    subtitle = ""
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    if cursor < len(lines) and lines[cursor].startswith("> "):
        subtitle = lines[cursor][2:].strip()
        cursor += 1

    blocks: list[Block] = []
    paragraph: list[str] = []
    citations: set[str] = set()

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(part.strip() for part in paragraph).strip()
            if text:
                blocks.append(Block("paragraph", text=text))
                citations.update(_citation_ids(text))
            paragraph.clear()

    while cursor < len(lines):
        line = lines[cursor]
        if not line.strip():
            flush_paragraph()
            cursor += 1
            continue
        heading = HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            blocks.append(Block("heading", text=heading.group(2), level=len(heading.group(1)) - 1))
            cursor += 1
            continue
        if line.strip() == "---":
            flush_paragraph()
            blocks.append(Block("rule"))
            cursor += 1
            continue
        if line.lstrip().startswith("|"):
            flush_paragraph()
            table_lines: list[str] = []
            while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
                table_lines.append(lines[cursor])
                cursor += 1
            if len(table_lines) < 2:
                raise ValueError("table needs a header and a separator row")
            parsed_rows = [_table_cells(row) for row in table_lines]
            if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in parsed_rows[1]):
                raise ValueError("table separator row is malformed")
            if len(parsed_rows[0]) != len(parsed_rows[1]):
                raise ValueError("table header and separator must have the same number of columns")
            data_rows = (parsed_rows[0], *parsed_rows[2:])
            if not data_rows[0] or any(len(row) != len(data_rows[0]) for row in data_rows):
                raise ValueError("table rows must have the same number of columns")
            blocks.append(Block("table", rows=tuple(data_rows)))
            for row in data_rows:
                for cell in row:
                    citations.update(_citation_ids(cell))
            continue
        list_item = LIST_RE.match(line)
        if list_item:
            flush_paragraph()
            marker = list_item.group(1) or ""
            item_text = list_item.group(2).strip()
            blocks.append(Block("list_item", text=item_text, marker=marker))
            citations.update(_citation_ids(item_text))
            cursor += 1
            continue
        if line.startswith("> "):
            flush_paragraph()
            quote = line[2:].strip()
            blocks.append(Block("quote", text=quote))
            citations.update(_citation_ids(quote))
            cursor += 1
            continue
        if line.lstrip().startswith("<"):
            raise ValueError("raw HTML is not supported in the Markdown manuscript")
        paragraph.append(line)
        cursor += 1
    flush_paragraph()

    known_ids = set(evidence_ids) if evidence_ids is not None else set(EVIDENCE_BY_ID)
    unknown = sorted(citations - known_ids)
    if unknown:
        raise ValueError(f"unknown evidence ID(s): {', '.join(unknown)}")
    body_text = "\n".join(
        [block.text for block in blocks if block.text]
        + [cell for block in blocks if block.kind == "table" for row in block.rows for cell in row]
    )
    return Manuscript(title, subtitle, tuple(blocks), frozenset(citations), body_text)


def _section_text(blocks: tuple[Block, ...], start: int, stop_level: int = 2) -> str:
    collected: list[str] = []
    for block in blocks[start + 1 :]:
        if block.kind == "heading" and block.level <= stop_level:
            break
        if block.text:
            collected.append(block.text)
        if block.kind == "table":
            collected.extend(cell for row in block.rows for cell in row)
    return " ".join(collected)


def _daily_lesson_part_lengths(text: str) -> dict[str, int]:
    """Measure instructional components, not a page-filling total character quota."""
    starts = {label: text.find(label) for label in DAILY_LESSON_PART_MINIMUM_CHARS}
    lengths: dict[str, int] = {}
    for label, start in starts.items():
        if start < 0:
            continue
        content_start = start + len(label)
        following = [candidate for candidate in starts.values() if candidate > start]
        content_end = min(following, default=len(text))
        lengths[label] = len(normalize(text[content_start:content_end]))
    return lengths


def is_substantive_chapter(title: str) -> bool:
    """Distinguish numbered book chapters from same-level case-study headings."""
    return bool(CHAPTER_HEADING_RE.match(title))


def validate_source(path: Path = MANUSCRIPT_PATH) -> Manuscript:
    """Validate editorial substance, evidence references, and schedule shape."""
    manuscript = parse_markdown_text(path.read_text(encoding="utf-8"))
    if not manuscript.subtitle:
        raise ValueError("manuscript subtitle is required")
    chapters = [
        (index, block)
        for index, block in enumerate(manuscript.blocks)
        if block.kind == "heading" and block.level == 2 and is_substantive_chapter(block.text)
    ]
    if len(chapters) != EXPECTED_CHAPTER_COUNT:
        raise ValueError(
            f"expected exactly {EXPECTED_CHAPTER_COUNT} substantive chapters, got {len(chapters)}"
        )
    if len(manuscript.body_text) < 30_000:
        raise ValueError(f"manuscript is too short to meet the agreed depth: {len(manuscript.body_text)} characters")
    for index, chapter in chapters:
        if len(normalize(_section_text(manuscript.blocks, index))) < 500:
            raise ValueError(f"chapter lacks explanatory substance: {chapter.text}")
    curriculum_units = [
        (index, block)
        for index, block in enumerate(manuscript.blocks)
        if block.kind == "heading" and block.level == 3 and block.text.startswith("学習ユニット")
    ]
    if len(curriculum_units) != 35:
        raise ValueError(f"expected 35 instructional units, got {len(curriculum_units)}")
    for index, unit in curriculum_units:
        if len(_section_text(manuscript.blocks, index, stop_level=4)) < MINIMUM_UNIT_INSTRUCTION_CHARS:
            raise ValueError(f"curriculum unit lacks explanatory substance: {unit.text}")
    heading_titles = [block.text for block in manuscript.blocks if block.kind == "heading"]
    if len(heading_titles) != len(set(heading_titles)):
        raise ValueError("heading titles must be unique")
    if len(EVIDENCE_BY_ID) != len(EVIDENCE):
        raise ValueError("evidence IDs must be unique")
    for evidence_id, _kind, title, _scope, url in EVIDENCE:
        if not evidence_id or not title or not url.startswith("https://"):
            raise ValueError(f"incomplete evidence record: {evidence_id}")
    daily_sections = []
    for block_index, block in enumerate(manuscript.blocks):
        if block.kind != "heading" or block.level != 4:
            continue
        match = DAILY_HEADING_RE.fullmatch(block.text)
        if match:
            daily_sections.append((block_index, match))
    expected_dates = daily_dates()
    if len(daily_sections) != len(expected_dates):
        raise ValueError(f"expected {len(expected_dates)} daily sessions, got {len(daily_sections)}")
    day_titles: set[str] = set()
    normalized_sessions: set[str] = set()
    weekday_names = "月火水木金土日"
    for expected_index, ((block_index, match), expected_date) in enumerate(
        zip(daily_sections, expected_dates),
        start=1,
    ):
        day_number, date_text, weekday_text, title = match.groups()
        if int(day_number) != expected_index or date_text != expected_date.isoformat():
            raise ValueError(f"daily session {expected_index} does not match {expected_date.isoformat()}")
        if weekday_text != weekday_names[expected_date.weekday()]:
            raise ValueError(f"daily session {expected_index} has an incorrect weekday")
        if title in day_titles:
            raise ValueError(f"daily session titles must be unique: {title}")
        day_titles.add(title)
        raw_session_text = _section_text(manuscript.blocks, block_index, stop_level=4)
        required_lesson_parts = ("目的：", "解説：", "実習：", "振り返り：", "対戦できない場合：")
        if not all(part in raw_session_text for part in required_lesson_parts):
            raise ValueError(f"daily session must state its objective, exercise, reflection, and fallback: {day_number}")
        session_text = normalize(raw_session_text)
        part_lengths = _daily_lesson_part_lengths(raw_session_text)
        for label, minimum in DAILY_LESSON_PART_MINIMUM_CHARS.items():
            if part_lengths.get(label, 0) < minimum:
                raise ValueError(
                    f"daily session lacks instructional substance: {day_number} ({label})"
                )
        if session_text in normalized_sessions:
            raise ValueError(f"daily session content is duplicated: {day_number}")
        normalized_sessions.add(session_text)
    required_sources = {
        "E-001", "E-003", "E-006", "E-009", "E-010",
        "E-023", "E-024", "E-025", "E-026", "E-027", "E-028",
        "E-029", "E-030", "E-031", "E-032", "E-033", "E-034", "E-035", "E-036",
    }
    if not required_sources.issubset(manuscript.citations):
        missing_sources = ", ".join(sorted(required_sources - manuscript.citations))
        raise ValueError(f"required official and case-study sources are not cited: {missing_sources}")
    return manuscript


def find_font() -> str:
    result = subprocess.run(
        ["fc-match", "-f", "%{file}", "BIZ UDGothic"],
        check=True,
        capture_output=True,
        text=True,
    )
    path = result.stdout.strip()
    if not path or not Path(path).exists():
        raise RuntimeError("BIZ UDGothic is required for Japanese PDF output")
    return path


def _citation_targets(text: str) -> tuple[str, ...]:
    targets: list[str] = []
    for match in CITATION_RE.finditer(text):
        targets.extend(_expand_citation_group(match.group(1)))
    return tuple(dict.fromkeys(targets))


def _without_citations(text: str) -> str:
    return CITATION_RE.sub("", text).strip()


def _plain_inline(text: str) -> str:
    """Escape source text and retain only the small inline syntax used here."""
    escaped = escape(text.replace("**", "").replace("`", ""))

    def link_citations(match: re.Match[str]) -> str:
        links = (
            f'<link href="{escape(EVIDENCE_BY_ID[item][4])}" color="#176b8a">[{item}]</link>'
            for item in _expand_citation_group(match.group(1))
        )
        return "　".join(links)

    return CITATION_RE.sub(link_citations, escaped)


def _append_citations(story: list, text: str, note_style) -> None:
    targets = _citation_targets(text)
    if not targets:
        return
    from reportlab.platypus import Paragraph

    links = "　".join(
        f'<link href="{escape(EVIDENCE_BY_ID[item][4])}" color="#176b8a">[{item}]</link>'
        for item in targets
    )
    story.append(Paragraph(f"参照：{links}", note_style))


def _table_flowable(rows: tuple[tuple[str, ...], ...], available_width: float, body_style):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Table, TableStyle

    column_count = len(rows[0])
    col_widths = [available_width / column_count] * column_count
    header_style = ParagraphStyle(
        "BookTableHeader",
        parent=body_style,
        textColor=HexColor("#ffffff"),
    )
    data = [
        [Paragraph(_plain_inline(cell), header_style if row_index == 0 else body_style) for cell in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#173c58")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#f5f8fa")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f8fa"), HexColor("#ffffff")]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cbd6de")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    table.spaceBefore = 5
    table.spaceAfter = 12
    return table


def _source_index_flowable(available_width: float, font_name: str):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Table, TableStyle

    index_style = ParagraphStyle(
        "EvidenceIndex",
        fontName=font_name,
        fontSize=7.5,
        leading=10.5,
        textColor=HexColor("#17232d"),
        splitLongWords=1,
    )
    header_style = ParagraphStyle(
        "EvidenceIndexHeader",
        parent=index_style,
        textColor=HexColor("#ffffff"),
    )
    link_width = available_width * 0.70
    data = [[Paragraph("ID・区分", header_style), Paragraph("出典名・参照範囲（出典名から正規URLへ移動）", header_style)]]
    for evidence_id, kind, title, scope, url in EVIDENCE:
        link = f'<link href="{escape(url)}" color="#176b8a">{escape(title)}</link>'
        details = f"{link}<br/>{escape(scope)}"
        data.append([
            Paragraph(f"{evidence_id}<br/>{escape(kind)}", index_style),
            Paragraph(details, index_style),
        ])
    table = Table(data, colWidths=[available_width - link_width, link_width], repeatRows=1, splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#173c58")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#f5f8fa")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f5f8fa"), HexColor("#ffffff")]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cbd6de")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _make_styles(font_name: str):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    common = {"fontName": font_name, "wordWrap": "CJK"}
    styles = {
        "title": ParagraphStyle("BookTitle", **common, fontSize=26, leading=37, alignment=1, spaceAfter=18),
        "subtitle": ParagraphStyle("BookSubtitle", **common, fontSize=13, leading=22, alignment=1, textColor=colors.HexColor("#426070"), spaceAfter=20),
        "meta": ParagraphStyle("BookMeta", **common, fontSize=9.2, leading=15, alignment=1, textColor=colors.HexColor("#52636f")),
        "part": ParagraphStyle("PartHeading", **common, fontSize=20, leading=29, textColor=colors.HexColor("#173c58"), spaceBefore=6, spaceAfter=16, keepWithNext=1),
        "chapter": ParagraphStyle("ChapterHeading", **common, fontSize=15, leading=23, textColor=colors.HexColor("#176b8a"), spaceBefore=14, spaceAfter=9, keepWithNext=1),
        "section": ParagraphStyle("SectionHeading", **common, fontSize=11.5, leading=18, textColor=colors.HexColor("#245c70"), spaceBefore=10, spaceAfter=5, keepWithNext=1),
        "daily_heading": ParagraphStyle("DailyHeading", **common, fontSize=10.5, leading=14.5, textColor=colors.HexColor("#245c70"), spaceBefore=4, spaceAfter=3, keepWithNext=1),
        "body": ParagraphStyle("Body", **common, fontSize=10.5, leading=17.5, textColor=colors.HexColor("#17232d"), spaceAfter=8, allowWidows=0, allowOrphans=0, splitLongWords=1),
        "daily_body": ParagraphStyle("DailyBody", **common, fontSize=10, leading=15, textColor=colors.HexColor("#17232d"), spaceAfter=3, allowWidows=0, allowOrphans=0, splitLongWords=1),
        "note": ParagraphStyle("EvidenceNote", fontName=font_name, fontSize=7.7, leading=11, textColor=colors.HexColor("#176b8a"), spaceBefore=-3, spaceAfter=8, splitLongWords=1),
        "daily_note": ParagraphStyle("DailyEvidenceNote", fontName=font_name, fontSize=7.2, leading=9, textColor=colors.HexColor("#176b8a"), spaceBefore=-2, spaceAfter=3, splitLongWords=1),
        "list": ParagraphStyle("ListItem", **common, fontSize=10.2, leading=17, leftIndent=14, firstLineIndent=-10, bulletIndent=0, spaceAfter=4, splitLongWords=1),
        "quote": ParagraphStyle("Quote", **common, fontSize=9.2, leading=15, leftIndent=12, rightIndent=10, borderColor=colors.HexColor("#6fa6b6"), borderWidth=1, borderPadding=8, backColor=colors.HexColor("#f1f7f8"), spaceBefore=4, spaceAfter=9, splitLongWords=1),
        "toc_title": ParagraphStyle("TOCTitle", **common, fontSize=19, leading=27, textColor=colors.HexColor("#173c58"), spaceAfter=16),
        "toc_part": ParagraphStyle("TOCPart", fontName=font_name, fontSize=9.4, leading=15, leftIndent=0, firstLineIndent=0, spaceBefore=2, wordWrap="CJK", textColor=colors.HexColor("#173c58")),
        "toc_chapter": ParagraphStyle("TOCChapter", fontName=font_name, fontSize=8.4, leading=12.5, leftIndent=15, firstLineIndent=0, wordWrap="CJK", textColor=colors.HexColor("#29414f")),
    }
    return styles


def _outline_count(items) -> int:
    total = 0
    for item in items:
        if isinstance(item, list):
            total += _outline_count(item)
        else:
            total += 1
    return total


def extract_pdf_text(path: Path) -> str:
    result = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], check=True, capture_output=True, text=True)
    return result.stdout


def count_pdf_links(path: Path) -> int:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    count = 0
    for page in reader.pages:
        for annotation in page.get("/Annots", []):
            item = annotation.get_object()
            if item.get("/Subtype") == "/Link" and item.get("/A", {}).get("/URI"):
                count += 1
    return count


def count_pdf_outlines(path: Path) -> int:
    from pypdf import PdfReader

    return _outline_count(PdfReader(str(path)).outline)


class BookDocTemplate:
    """Small wrapper factory kept local to avoid importing ReportLab at module load."""


def _document_class():
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

    class JapaneseBookDocTemplate(BaseDocTemplate):
        def __init__(self, filename: str, title: str):
            super().__init__(
                filename,
                pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
                leftMargin=MARGIN_LEFT,
                rightMargin=MARGIN_RIGHT,
                topMargin=MARGIN_TOP,
                bottomMargin=MARGIN_BOTTOM,
                title=title,
                author="thinking-publication",
                subject="初心者向けダブルバトルとPJCS2027準備。ISO B5, 176 x 250 mm",
                pageCompression=1,
            )
            frame = Frame(
                MARGIN_LEFT,
                MARGIN_BOTTOM,
                PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT,
                PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM,
                id="book-frame",
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )
            self.addPageTemplates(PageTemplate(id="book", frames=[frame], onPage=self._draw_page))

        def _draw_page(self, canvas, doc):
            canvas.saveState()
            if doc.page > 1:
                canvas.setStrokeColor(HexColor("#d4dee4"))
                canvas.setLineWidth(0.5)
                canvas.line(MARGIN_LEFT, 31, PAGE_WIDTH - MARGIN_RIGHT, 31)
                canvas.setFont("JP", 7.3)
                canvas.setFillColor(HexColor("#60717a"))
                canvas.drawString(MARGIN_LEFT, 18, "Pokémon ChampionsからPJCS2027へ")
                canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, 18, str(doc.page))
            canvas.restoreState()

        def afterFlowable(self, flowable):
            if not hasattr(flowable, "_book_heading_level"):
                return
            heading_level = flowable._book_heading_level
            text = flowable.getPlainText()
            is_course_unit = heading_level == 3 and text.startswith("学習ユニット")
            if heading_level not in (1, 2) and not is_course_unit:
                return
            key = flowable._book_heading_key
            self.canv.bookmarkPage(key)
            outline_level = heading_level - 1
            self.canv.addOutlineEntry(text, key, level=outline_level, closed=is_course_unit)
            if heading_level in (1, 2):
                self.notify("TOCEntry", (outline_level, text, self.page, key))

    return JapaneseBookDocTemplate


def _make_story(manuscript: Manuscript, styles):
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import PageBreak, Paragraph, Spacer
    from reportlab.platypus.tableofcontents import TableOfContents

    story = [
        Spacer(1, 100),
        Paragraph(_plain_inline(manuscript.title).replace("からPJCS2027へ", "から<br/>PJCS2027へ"), styles["title"]),
        Paragraph(_plain_inline(manuscript.subtitle), styles["subtitle"]),
        Paragraph("基準日：2026年10月4日<br/>初心者向け・マスターカテゴリ・毎日60分×240日＋大会日追加枠", styles["meta"]),
        Spacer(1, 26),
        Paragraph("大会結果を約束する本ではなく、判断を更新する手順を身につける本", styles["meta"]),
        PageBreak(),
        Paragraph("目次", styles["toc_title"]),
    ]
    toc = TableOfContents()
    toc.levelStyles = [styles["toc_part"], styles["toc_chapter"]]
    toc.dotsMinLevel = 0
    story.extend([toc, PageBreak()])
    width = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    heading_index = 0
    in_daily_session = False
    for block in manuscript.blocks:
        if block.kind == "heading":
            is_daily_heading = block.level == 4 and DAILY_HEADING_RE.fullmatch(block.text)
            in_daily_session = bool(is_daily_heading)
            if is_daily_heading:
                style = styles["daily_heading"]
            elif block.level == 1:
                style = styles["part"]
            elif block.level == 2:
                style = styles["chapter"]
            else:
                style = styles["section"]
            heading = Paragraph(_plain_inline(block.text), style)
            heading._book_heading_level = block.level
            heading_index += 1
            heading._book_heading_key = f"heading-{heading_index}"
            story.append(heading)
        elif block.kind == "paragraph":
            paragraph = _without_citations(block.text)
            if paragraph:
                body_style = styles["daily_body"] if in_daily_session else styles["body"]
                story.append(Paragraph(_plain_inline(paragraph), body_style))
            note_style = styles["daily_note"] if in_daily_session else styles["note"]
            _append_citations(story, block.text, note_style)
        elif block.kind == "list_item":
            marker = f"{block.marker} " if block.marker else "・"
            story.append(Paragraph(f"{marker}{_plain_inline(_without_citations(block.text))}", styles["list"]))
            _append_citations(story, block.text, styles["note"])
        elif block.kind == "quote":
            story.append(Paragraph(_plain_inline(_without_citations(block.text)), styles["quote"]))
            _append_citations(story, block.text, styles["note"])
        elif block.kind == "table":
            story.append(_table_flowable(block.rows, width, styles["body"]))
        elif block.kind == "rule":
            story.append(Spacer(1, 5))
        else:
            raise ValueError(f"unsupported manuscript block: {block.kind}")
    story.append(PageBreak())
    source_heading = Paragraph("出典・エビデンス台帳", styles["part"])
    source_heading._book_heading_level = 1
    heading_index += 1
    source_heading._book_heading_key = f"heading-{heading_index}"
    story.append(source_heading)
    story.append(Paragraph(
        "各出典名は正規URLへのクリック可能リンクです。公開日やルールが更新された場合は、大会直前に元ページとゲーム内表示を再確認してください。",
        styles["body"],
    ))
    story.append(_source_index_flowable(width, styles["body"].fontName))
    return story


def build_pdf(output: Path, manuscript_path: Path = MANUSCRIPT_PATH) -> int:
    """Render one selectable, linked PDF using natural paragraph flow."""
    manuscript = validate_source(manuscript_path)
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen.canvas import Canvas
    except ImportError as exc:
        raise RuntimeError("install reportlab with: uv run --with 'reportlab==5.0.1' python tools/build_pjcs2027_playbook.py") from exc

    font_path = find_font()
    if "JP" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("JP", font_path, subfontIndex=0))
    styles = _make_styles("JP")
    output.parent.mkdir(parents=True, exist_ok=True)
    doc_class = _document_class()
    doc = doc_class(str(output), manuscript.title)
    story = _make_story(manuscript, styles)

    def stable_canvas(*args, **kwargs):
        kwargs["invariant"] = 1
        return Canvas(*args, **kwargs)

    doc.multiBuild(story, maxPasses=5, canvasmaker=stable_canvas)
    if doc.page < MINIMUM_BOOK_PAGES:
        raise ValueError(
            f"book output has {doc.page} pages; the agreed minimum is {MINIMUM_BOOK_PAGES}"
        )
    return doc.page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/pdf/pokemon-champions-pjcs2027-practice-book.pdf"),
    )
    parser.add_argument("--manuscript", type=Path, default=MANUSCRIPT_PATH)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    manuscript = validate_source(args.manuscript)
    chapters = sum(
        block.kind == "heading" and block.level == 2 and is_substantive_chapter(block.text)
        for block in manuscript.blocks
    )
    if args.validate_only:
        print(
            f"source-ok chapters={chapters} characters={len(manuscript.body_text)} "
            f"citations={len(manuscript.citations)} sessions={len(daily_dates())} "
            f"target-pages={TARGET_BOOK_PAGES} minimum-pages={MINIMUM_BOOK_PAGES}"
        )
        return 0
    pages = build_pdf(args.output, args.manuscript)
    print(f"built {args.output} pages={pages} characters={len(manuscript.body_text)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
