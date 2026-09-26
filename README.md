# thinking

AIコーディング、テスト戦略、開発プロセスについて考えたことを、読者が内容を追えるHTMLページとして残すリポジトリです。

公開サイト: https://sk8metalme.github.io/thinking/

## 構成

```
AGENTS.md                                      エージェント向けの執筆・検証規約
.agents/skills/publish-github-pages/           記事作成・公開準備Skill
.github/workflows/pages.yml                    PR検証とGitHub Pages公開
docs/                                           Pagesに公開する静的HTML
├── .nojekyll                                   Jekyll処理を無効化
├── index.html                                  トップページと記事一覧
├── testing/                                    テスト戦略カテゴリ
│   ├── ai-coding-test-strategy.html
│   └── jev-test-strategy.html
└── jev/                                        Jevカテゴリ
    └── jev-as-a-judge.html
```

公開は、PRでページ構成を検証したあと、`main`へのpushをきっかけにGitHub Actionsが`docs/`をデプロイします。記事の追加や公開準備では、リポジトリ内の `publish-github-pages` Skillを使います。

## ページの追加手順

1. Skillを使い、想定読者・ページの目的・扱う範囲・不明点・方向性を確定する
2. `docs/<カテゴリ>/<ページ名>.html` に単一ファイルのHTMLを置く（CSS/JSはファイル内にインライン）
3. `docs/index.html` の該当カテゴリへ記事へのリンク、説明、日付、タグを追加する
4. 比較は表、関係や工程は必要性を確認したうえで図にし、図だけでは伝わらない前提と説明を本文に書く
5. ローカル確認とリンク・アクセシビリティ確認を行い、PRを作成する
6. PRが通って`main`へ反映されるとActionsが公開する

記事フッターには、配置階層に応じた相対パスで `thinking` トップへのリンクを置きます。

## 命名ルール

- ファイル名・ディレクトリ名は小文字の英数字とハイフン（例: `ai-coding-test-strategy.html`）
- 公開URLが変わるとリンク切れになるため、公開後のファイル名変更は避ける

## ローカル確認

```sh
python3 -m http.server -d docs 8000
# http://localhost:8000/ を開く
```

詳細な品質基準と公開前チェックは [AGENTS.md](AGENTS.md) と `publish-github-pages` Skillを参照してください。
