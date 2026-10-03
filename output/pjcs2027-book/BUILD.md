# PJCS2027実践ワークブックの再生成

PDFは手編集せず、`tools/build_pjcs2027_playbook.py` のトピック別データから生成する。

```sh
uv run --with reportlab python tools/build_pjcs2027_playbook.py --validate-only
uv run --with reportlab python tools/build_pjcs2027_playbook.py \
  --output output/pdf/pokemon-champions-pjcs2027-master-playbook.pdf
```

生成器は次を検証してから出力する。

- 35個のトピック別章、35週の練習計画、4つのパーティ案、25ページの付録
- 各章の固有ケース・反例・1時間ラボ
- 公式情報に紐づくE-001〜E-013の出典台帳
- B5サイズ、PDFしおり、目次の内部リンク、一次情報へのリンク注釈

規則、対象ポケモン、技、特性、持ち物が更新された場合は、`EVIDENCE`、該当章、該当週、パーティ案の合法性ゲートを更新し、再生成後に `pdfinfo`、`pdftotext`、リンク注釈、全ページのレンダリングを再確認する。
