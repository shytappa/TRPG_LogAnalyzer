systems/coc/
│
├── app_coc.py                  # 👑 CoC解析の司令塔（ページのメイン処理）
│
├── layouts/                    # 🖼️ 画面の大枠・骨組み（レイアウト）
│   ├── dashboard_coc.py        # メイン画面（4つのタブ）の枠組み
│   └── sidebar_coc.py          # CoC専用フィルターを並べるサイドバーの枠組み
│
├── components/                 # 🧩 CoC専用の細かいUI部品
│   ├── badges_coc.py           # キャラクター名のバッジ生成
│   ├── filters_coc.py          # CoC独自の絞り込みUI（B/Pダイス除外など）
│   ├── export_coc.py           # 画像保存ボタン等のUI
│   └── styles_coc.py           # CoC専用のカラーパレットやCSS
│
├── features/                   # 🚀 各機能の具体的な描画・集計ロジック
│   │
│   ├── summary/                # 総合サマリー機能
│   │   ├── ui_sum.py           # 画面操作・設定UI
│   │   ├── logic_sum.py        # データ集計・計算
│   │   └── html_sum.py         # html文字列の構築
│   │
│   ├── probability/            # 確率集計機能
│   │   ├── ui_prob.py
│   │   ├── logic_prob.py
│   │   └── html_prob.py
│   │
│   ├── growth/                 # 成長チェック機能
│   │   ├── ui_grow.py
│   │   ├── logic_grow.py
│   │   ├── html_grow.py
│   │   └── copy_grow.py        # クリップボードコピー用機能
│   │
│   ├── raw_log/                # 生ログ表示機能
│   │   ├── ui_log.py
│   │   ├── logic_log.py
│   │   └── html_log.py
│   │
│   └── manual/                 # 使い方・マニュアル表示
│       └── manual_coc.py
│
└── core/                       # 🧠 純粋なデータ処理（※UIは一切含めない）
    ├── logic_coc.py            # クトゥルフ独自の成功度判定・集計ロジック
    ├── utils_coc.py            # 文字列クリーニング等の便利ツール群
    ├── parser_coc.py           # ログテキストをデータフレームに変換する処理
    └── data_coc.py             # 6版/7版の技能初期値やソート用辞書データ


