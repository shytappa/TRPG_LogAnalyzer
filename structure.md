TRPG_Analyzer/
│
├── app.py                      # アプリの起動口
├── requirements.txt            # 必要な外部ライブラリのリスト
│
├── pages/                      # 画面遷移の中継用スクリプト群
│   ├── pages_coc.py            # クトゥルフ神話TRPG画面への遷移ラッパー
│   └── pages_emo.py            # エモクロアTRPG画面への遷移ラッパー
│
├── core/                       # 🧠 全システム共通のデータ処理
│   └── logic_base.py           # ログの絞り込み、キャラ統合処理などの基礎ロジック
│
├── components/                 # 🎨 全システム共通のUI部品
│   ├── styles_base.py          # 全体共通のCSS、カラーパレット、デザイン定義
│   ├── common_ui.py            # 全画面で使い回す汎用UIパーツ
│   └── sidebar_base.py         # サイドバー専用の共通UI
│
└── systems/                    # 🎮 各TRPGシステム専用の実体
    ├── coc/                    # 🐙 クトゥルフ神話TRPG用システム
    │   └── ...
    └── emocroa/                # 🍃 エモクロアTRPG用システム（開発中）
        └── ...