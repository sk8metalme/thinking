# PJCS2027実践ワークブックの再生成

PDFは手編集せず、`tools/build_pjcs2027_playbook.py` のトピック別データから生成する。

```sh
uv run --with 'reportlab==5.0.1' python tools/build_pjcs2027_playbook.py --validate-only
uv run --with 'reportlab==5.0.1' python tools/build_pjcs2027_playbook.py \
  --output output/pdf/pokemon-champions-pjcs2027-master-playbook.pdf
```

生成器は次を検証してから出力する。

- 35個のトピック別章、35週の練習計画、4つのパーティ案、27ページの付録
- 各章の固有ケース・反例・1時間ラボ
- 公式情報に紐づくE-001〜E-013の出典台帳
- B5サイズ、PDFしおり、目次の内部リンク、一次情報へのリンク注釈
- `invariant=1` と固定したReportLab 5.0.1、同一のBIZ UDGothicフォント環境で、同じ入力からバイト再現できる

フォント環境は `fc-match -f '%{file}' 'BIZ UDGothic'` で確認する。別のフォントやReportLabの版で生成した場合は、ページ数だけでなくSHA-256と目視レンダリングも再確認する。

規則、対象ポケモン、技、特性、持ち物が更新された場合は、`EVIDENCE`、該当章、該当週、パーティ案の合法性ゲートを更新し、再生成後に `pdfinfo`、`pdftotext`、リンク注釈、全ページのレンダリングを再確認する。
