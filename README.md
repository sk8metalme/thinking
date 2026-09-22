# thinking

日々考えたことを、雑多な思考メモとして読める形で残していく場所です。

公開サイト: https://sk8metalme.github.io/thinking/

## 構成

```
docs/                     GitHub Pages の公開ルート（main ブランチの /docs から配信）
├── .nojekyll             Jekyll 処理を無効化し、HTML をそのまま配信する
├── index.html            トップページ（各ページへの一覧）
└── testing/              テスト戦略カテゴリ
    ├── ai-coding-test-strategy.html
    └── jev-test-strategy.html
```

## ページの追加手順

1. `docs/<カテゴリ>/<ページ名>.html` に単一ファイルの HTML を置く（CSS/JS はファイル内にインライン）
2. ページのフッターに `<a href="../">thinking トップに戻る</a>` を入れる
3. `docs/index.html` の該当カテゴリの `<ul class="pages">` に `<li>` を1件追加する（新カテゴリなら `<section>` ごと追加）
4. main に push すると数分で公開サイトに反映される

## 命名ルール

- ファイル名・ディレクトリ名は小文字の英数字とハイフン（例: `ai-coding-test-strategy.html`）
- 公開 URL が変わるとリンク切れになるため、公開後のファイル名変更は避ける

## ローカル確認

```sh
python3 -m http.server -d docs 8000
# http://localhost:8000/ を開く
```
