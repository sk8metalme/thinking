# EPUB / Kindle 制作・検証ガイド

## 目的と形式

EPUB 3のリフロー型を、Apple BooksやKindle端末・アプリで読みやすい電子書籍の標準形式とする。画面幅や読者の文字設定に合わせて本文が再配置されるため、EPUBのページ数は固定できない。固定ページ数が必要な本はPDFも併行して作成し、PDFをページ数の基準版として扱う。

「Kindle対応」は、Kindleで読み込めるEPUBを作ることを意味し、Amazon KDPで販売・公開することを意味しない。Send to Kindleへの送信、KDP登録、販売設定、著作権・権利表明などを伴う操作は、ユーザーが明示的に依頼した場合にだけ行う。配信条件は変わりうるため、実行時にはAmazonの最新公式案内を再確認する。

## 執筆と組版

- 章・節を意味的なHTML見出しと本文で表し、読書順をOPF spineに正しく登録する。
- 先頭付近にリンク付きHTML目次を置き、EPUBの `nav.xhtml` に目次を用意する。Kindleを対象にする場合はNCXも同梱し、目次を2階層までにする。Apple Booksのみを対象とする場合はNCXを必須にせず、意味構造に沿った必要な階層を保つ。
- 本文の文字サイズ、行間、ページ寸法を強制せず、読者の文字拡大を尊重する。固定レイアウトや装飾的な改ページを避ける。
- Kindleのリフロー型では、本文全体に固定の文字色や背景色を指定しない。読者が背景テーマや文字設定を変えても可読性が保たれるようにし、テーマ色が必要な要素は背景とのコントラストを確認する。
- 端末幅を超える表は分割・再設計する。単純で短い表を使い、データを画像へ焼き付けない。表の読み方・単位・出典は本文でも説明する。
- 出典IDは読者がタップできる内部リンクにし、出典台帳から正規の外部URLへ到達できるようにする。章分割時に相対パスとフラグメントを検証する。
- CSS・画像・フォントなどの同梱資産を最小限にする。本文理解を外部フォント・通信・JavaScriptに依存させない。

## 必須検証

1. EPUBCheckでEPUBパッケージとコンテンツを検査する。
2. Ace by DAISYまたは同等のEPUBアクセシビリティ検査を別に実行し、レポートを確認して修正する。AceがEPUBCheckを代替するわけではない。自動検査が利用できない場合は未実施と明記し、アクセシビリティ確認済みとは報告しない。適合性の表明が必要な場合は、手動評価も行う。
3. ZIP内の `mimetype`、container、OPF manifest/spine、nav、全資産を確認する。Kindleを対象にする場合はNCXも確認する。
4. 本文・目次・出典の内部リンクとフラグメントを全件確認し、外部出典リンクの到達先を記録する。
5. 画面幅約390 CSS px程度と大きな文字サイズを想定してレンダリングし、見出し、表、長いURL、リンク、コード等が読みやすいか確認する。
6. Kindleが対象なら、Kindle Previewerが利用可能な環境でEPUBを開き、スマートフォン相当と電子ペーパー相当の複数表示で、ナビゲーション・画像・表・改ページを確認する。リフロー型は白・黒・ミント・セピアの各背景テーマでも本文とリンクの可読性を確認する。Apple Booksが対象なら、利用可能なMacのApple BooksでBook Proofingを行い、必要に応じてiOS端末へ同期して確認する。対象アプリや端末が利用できないときは未実施と明記し、EPUBCheck合格だけで対象アプリの表示確認済みと主張しない。
7. PDF併行版がある場合は、章構成・本文・出典の一致を確認する。ただし、EPUBの見開きやページ区切りをPDFに合わせて固定しない。

## 公式資料

- W3C, [EPUB 3.3](https://www.w3.org/TR/epub-33/) — パッケージ文書、ナビゲーション文書、EPUB文書の仕様。出版物IDは小改訂で不用意に変更せず、`dcterms:modified` は内容更新ごとにUTCで更新する。
- W3C, [EPUB 3.3 — NCX](https://www.w3.org/TR/epub-33/#sec-opf2-ncx) — NCXはEPUB 2読書システム向けの後方互換機能で、EPUB 3のナビゲーション文書が置き換える。
- W3C, [EPUBCheck](https://github.com/w3c/epubcheck) — EPUB準拠を検証する公式ツール。
- Apple, [EPUB file format](https://help.apple.com/itc/booksassetguide/en.lproj/itcff6dc14a2.html) — Apple Booksで扱うEPUBとリフロー型の案内。
- Apple, [Using the Book Proofing Tool](https://help.apple.com/itc/booksassetguide/en.lproj/itc073460726.html) — Apple Books上でEPUBを校正し、iOS端末と同期して確認する方法。
- Amazon, [Learn About Sending Documents to Your Kindle Library](https://digprjsurvey.amazon.com/csad/help/node/G5WYD9SAF7PGXRNA) — Send to Kindleの利用方法と個人文書の対応形式。
- Amazon KDP, [Supported eBook formats](https://kdp.amazon.com/en_US/help/topic/G200634390/) — KDPが受け付けるeBook原稿形式。Kindle Previewerとは別ページ。
- Amazon KDP, [Kindle Previewer](https://kdp.amazon.com/en_US/help/topic/G202131170) — EPUBを開けるPreviewerと対象デバイスの案内。
- Amazon KDP, [Navigation Guidelines](https://kdp.amazon.com/en_US/help/topic/GY3AD8C6C6GAG42N) — Kindleのナビゲーション、NCX、二階層の目次制限。Kindleを対象にする場合だけ参照し、KDP登録や販売操作の許可とは扱わない。
- Amazon KDP, [QA Standards](https://kdp.amazon.com/en_US/help/topic/GGRXLC5USU4H67YM) — 目次・文字設定・画像・表・白／黒／ミント／セピアの配色とアクセシビリティを含む検品項目。
- Amazon KDP, [Format the text of your Kindle eBook](https://kdp.amazon.com/en_US/help/topic/GH4DRT75GWWAGBTU) — リフロー本文の文字サイズと行間を読者設定に委ねる指針。
- Amazon KDP, [Create a Table of Contents](https://kdp.amazon.com/en_US/help/topic/GY3AD8C6C6GAG42N) — ナビゲーション用目次と階層の推奨。
- Amazon KDP, [Tables in Kindle books](https://kdp.amazon.com/en_US/help/topic/GZ8BAXASXKB5JVML) — 狭い画面を考慮した表の指針。
- DAISY Consortium, [Ace by DAISY](https://kb.daisy.org/publishing/docs/epub/validation/ace.html) — EPUBの自動アクセシビリティ検査とそのレポート。
- DAISY Consortium, [Validation process](https://kb.daisy.org/publishing/docs/epub/validation/overview.html) — EPUBCheck、Ace、手動評価の役割を分けた検証順。

Amazon KDP資料は販売用出版仕様の参考として使う。Kindleで読む個人用EPUB作成を、KDP登録や販売公開へ拡張してはならない。
