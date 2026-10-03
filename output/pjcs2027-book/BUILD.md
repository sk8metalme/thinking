# PDF本の再生成

本文の正本は [`manuscript.md`](manuscript.md)。段落・章・表を自然に流し、PDFは手編集しない。

```sh
uv run --with 'reportlab==5.0.1' --with 'pypdf==6.19.0' python tools/build_pjcs2027_playbook.py --validate-only
uv run --with 'reportlab==5.0.1' --with 'pypdf==6.19.0' python tools/build_pjcs2027_playbook.py \
  --output output/pdf/pokemon-champions-pjcs2027-practice-book.pdf
cp output/pdf/pokemon-champions-pjcs2027-practice-book.pdf \
  docs/pokemon-champions/pokemon-champions-pjcs2027-practice-book.pdf
```

生成環境は Python 3.11 以上、ReportLab 5.0.1、pypdf 6.19.0、Poppler（`pdfinfo`・`pdftotext`・`pdftoppm`）、`fc-match`、BIZ UDGothicを想定する。再生成後は次を確認する。

- `--validate-only` が章数、原稿文字数、証拠ID、35週の日付と行数を検証する
- `pdfinfo` でページ数、B5、暗号化、メタデータを確認する
- `pdftotext` で日本語選択・検索、目次、本文、リンクラベルを確認する
- pypdfでPDFしおり、内部リンク、全出典リンクを確認する
- `pdftoppm` で全ページを描画し、サムネイル一覧と代表ページを目視する
- PDFとHTMLに含まれる全URLを開き、出典台帳のID・参照範囲と対応させる

ReportLabの組版は章ごとの固定改ページを行わず、本文・見出し・表の自然な流れでページ数を決める。ページ数が計画の見積もりと異なる場合は、本文を水増しせず、読者課題と不足台帳を再監査して差分を記録する。
