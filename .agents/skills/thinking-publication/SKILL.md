---
name: thinking-publication
description: "Create and revise evidence-backed Japanese pages and long-form PDF books for the thinking repository, with preflight outlines, page budgets, traceable source links, and format-specific quality checks."
metadata:
  short-description: "考察・分析・長編PDFを根拠付きで高品質に制作"
---

# thinking-publication

`thinking` リポジトリで、読者向けの考察ページ、分析レポート、比較・意思決定ページ、手順書、長編PDFを設計・執筆・検証する。本文を書く前に、読者・目的・範囲・出力形式・文量・目次・エビデンス計画を確定する。

## 適用範囲

次のいずれかを作成・改稿するときに使う。

- `consideration`：論点を整理し、考察・判断材料を示すページ
- `source-explanation`：一次情報や既存記事を、出典との境界を保って解説するページ
- `analysis-report`：指標・データ・図表に基づく結論先出しのレポート
- `comparison-decision`：複数案を基準で比較し、条件付きの推奨を示すページ
- `tutorial-playbook`：読者が手順を実行し、結果を検証できる実践ガイド

PDFの短いレポートや本は、本文モードとは別に配信面とボリュームプロファイルを選ぶ。目次、ページ配分、出典台帳が必要な長編では、全体を一度に書かず章単位で進める。

次の依頼は主目的が異なるため、このSkillだけで完結させない。

- 数値分析そのもの：適切な `data-analytics` 分析Skillを先に使う
- PDFの抽出・結合・フォーム入力だけ：`pdf:pdf` を使う
- GitHub Pagesの公開準備だけ：`publish-github-pages` を使う
- Siteへの公開だけ：分析成果物なら `data-analytics:publish-artifact-to-sites` を使う
- 一時的なチャット回答や短い要約：記事化しない

## 必須の成果物

各実行では、次のどちらかを残す。

1. 完成した読者向け成果物と検証結果
2. 具体的なブロッカー、未確認事項、追加で必要な資料

長編では、本文以外に次を管理する。

- 出版計画：読者、目的、範囲、出力形式、用紙、文量
- 目次案：章・節、目的、ページ配分、図表、主な出典
- エビデンス台帳：本文の主張から一次情報へ辿れる対応表
- 検証記録：章ごとの確認、リンク、図表、レンダリング、残課題

## フェーズ

### Research

1. `AGENTS.md`、`README.md`、`docs/index.html`、対象カテゴリの既存記事、`git status --short --branch` を読む。
2. 読者の目的に必要な一次情報、公式文書、原論文、データセット、元記事を列挙する。
3. URL、タイトル、組織・著者、公開日、版・コミット、参照箇所、最終確認日を出典台帳に記録する。
4. 現在性が必要な事実、専門的な事実、確信が低い事実はWebで確認する。記憶だけで出典を作らない。

### Plan

1. `references/modes.md` で本文モードと配信面を選ぶ。
2. `references/outline-and-volume.md` で文量プロファイルを選び、目次案とページ配分を作る。
3. `references/evidence.md` で、主張・出典・引用範囲・未検証事項の対応を設計する。
4. 次の出版計画をユーザーに提示する。

```text
想定読者：
ページ／本の目的：
読後に期待する理解・判断・行動：
本文モード：
配信面：
用紙・文字サイズ（PDFの場合）：
目標文量・ページ数：
目次案と章ごとのページ配分：
図表・付録の計画：
主要な一次情報：
未確認事項・範囲外：
```

5. 目次案、ページ配分、主要出典、表現方針が未確定で、結果が大きく変わる場合は執筆を始めず確認する。`book-100-200` 以上は、ユーザーが目次案を確認してから本文へ進む。`book-300-plus-exhaustive` は、少なくとも最初の章または数ページを試作・レンダリングしてから全体へ進む。

### Implement

1. 承認された目次とページ予算を変更せずに骨格として使う。必要な変更は、理由とページ差分を計画へ戻す。
2. 主張、解釈、図表、推奨、限界を読者が追える順番に配置する。
3. 事実の直後にエビデンスIDを置き、IDから正規URLへ辿れるようにする。
4. 数値を含むレポートは `$data-analytics:build-report`、検証は `$data-analytics:validate-data`、図表は `$data-analytics:visualize-data` に委譲する。
5. 図解が必要な場合は `$diagram-design` を使い、図だけで主張を伝えようとしない。
6. `docs/` のHTML記事は `$publish-github-pages` の単一HTML・相対リンク・一覧登録の規約に従う。公開設定変更、commit、pushは明示依頼なしに行わない。
7. PDFは静的な入力から生成し、ページ数、文字の選択性、リンク注釈、図表の欠落、改ページを確認する。

### Review

`references/quality-gates.md` を使い、本文だけでなく生成物そのものを確認する。

- 目次と実際の構成が一致している
- 目標ページ数の範囲に収まり、無意味な水増しがない
- すべての出典リンクが存在し、主張から辿れる
- 出典のない内容が事実として紛れ込んでいない
- 図表に本文の読み方、出典、限界がある
- HTMLの見出し、表、リンク、キーボード、モバイル、ダークモード、縮小モーションを確認した
- PDFの全ページで文字・図表・脚注・リンク・改ページを確認した
- 未解決のTODO、ローカルパス、秘密情報、認証情報を公開成果物に残していない

`book-300-plus-exhaustive` では、章ごとの引用監査、用語・相互参照の統一、図表番号、参考文献、ページ単位の視覚確認を完了しない限り完成扱いにしない。

## 出力と引き渡し

最終報告は次の順にする。

1. 成果物の種類、タイトル、実測ページ数・文字数
2. 目次と計画からの主な差分
3. エビデンス台帳とリンク検証の結果
4. 実行した検証と残っている手動確認
5. 変更ファイル、commit・push・公開の有無
6. 次にできるタスク候補

ページ数はPDFのレンダリング結果で実測する。HTMLでは文字数、主要セクション数、図表数、読了時間、必要ならPDF換算ページ数を報告する。

詳細なモード定義は [references/modes.md](references/modes.md)、文量と目次案は [references/outline-and-volume.md](references/outline-and-volume.md)、出典管理は [references/evidence.md](references/evidence.md)、最終検証は [references/quality-gates.md](references/quality-gates.md) を参照する。
