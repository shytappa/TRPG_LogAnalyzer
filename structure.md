（🔒 の付いたものは自卓用・開発用で、公開版には含めない（.gitignore で外している）。外しても通常版は動く）

TRPG_Analyzer/
│
├── app.py                      # アプリの起動口（システム選択画面）
├── 🔒 解析ツール起動.bat         # 解析アプリを起動（ポート8501。起動済みならブラウザで開くだけ）
├── 🔒 マッピングツール起動.bat   # マッピングツールを起動（ポート8502。起動済みならブラウザで開くだけ）
├── 🔒 公開版の確認用起動.bat     # 公開サーバーと同じ状態（目印なし・上限30MB）で解析アプリを起動（ポート8503）。
│                               # 公開するファイルだけを一時フォルダに写してから起動する（写し方は tests/public_check.py と共通）
├── 🔒 launch_common.bat         # 上の3つの中身（「自分のPC」の目印 TRPG_LOCAL=1 を付けて起動。公開版の確認用のときは目印を付けず、
│                               # 公開するファイルの写しから起動する。起動の失敗・ポートの使用中を知らせる）。
│                               # Shift-JIS で保存する（UTF-8 だと、日本語の行の途中から読む Windows の不具合が出る）
├── 🔒 .vscode/settings.json      # VS Code で .bat を Shift-JIS として開く・保存する設定
├── 🔒 .claude/launch.json        # 開発用の起動設定（Claude が画面を確かめるときに使う。trpg-analyzer＝目印なし・上限30MB（公開版に近い。
│                               # ただし写しではなくこのフォルダから起動）、trpg-analyzer-local＝目印あり・200MB（解析ツール起動.bat と同じ）、
│                               # mapping-tool＝目印あり（マッピングツール起動.bat と同じ））
├── .gitignore                  # 公開しないもの（先頭の / はプロジェクトの直下だけの意味）
├── 🔒 公開の手順.md              # 公開サーバーに置くときの手順と、自分のPCとの違い
├── 🔒 レビュー結果_*.md          # レビューの結果と、決めた仕様・作業のルール（最新の仕様は レビュー結果_20261107.md）
├── requirements.txt            # 必要な外部ライブラリ（動作確認済みの版に固定。Python 3.12 以上）
├── .streamlit/config.toml      # Streamlit の設定（ライトテーマに固定、左上のページ一覧を隠す、エラーの詳細を出さない、static/ を配る、
│                               # アップロードの上限30MB（公開サーバー向け。自分のPCでは .bat が200MBにする）、利用統計を送らない）
├── static/
│   └── html2canvas.min.js      # 画像保存の部品（1.4.1。enableStaticServing で /app/static/ から配る。読めなければ CDN から読む）
│
├── pages/                      # 画面遷移の中継用スクリプト群
│   ├── pages_coc.py            # クトゥルフ神話TRPG（通常版）を起動
│   ├── 🔒 pages_coc_shy.py       # クトゥルフ神話TRPG（自卓用の設定と起動）
│   └── pages_emo.py            # エモクロアTRPG（開発中の案内のみ）
│
├── core/                       # 🧠 全システム共通のデータ処理
│   ├── ccfolia_reader.py       # ココフォリアのログ（HTML 前の形式・2026年10月からの形式／テキスト／JSON／ZIP）を発言に分けて読む。
│   │                           # 1発言からロールの行を作る処理は各システム（例: systems/coc/core/parser_coc.py）から受け取る
│   ├── param_changes.py        # ステータスの増減（「[ A ] SAN : 50 → 44」）を読み、押し間違いの直しをまとめる（何を数えるかは各システムから受け取る）
│   └── logic_base.py           # ログの絞り込み、キャラ統合、「ファイル名<:::>名前」キー、ログの文字コードの読み方、「自分のPC」の目印
│
├── components/                 # 🎨 全システム共通のUI部品
│   ├── styles_base.py          # 全体共通のCSS
│   ├── common_ui.py            # 全選択/全解除ヘッダー、チェックボックス群、並び順の自動切替、エラー表示など
│   ├── sidebar_nav.py          # システムの一覧（ランチャーと共通）と、サイドバー下部の設定リセット・ページ選択・終了ボタン
│   ├── sidebar_files.py        # サイドバー：ファイル管理（アップロード・削除）
│   ├── sidebar_selector.py     # サイドバー：表示するファイル・タブ・キャラの選択と一括操作
│   └── sidebar_merge.py        # サイドバー：キャラクターの統合
│
├── systems/                    # 🎮 各TRPGシステム専用の実体
│   ├── coc/                    # 🐙 クトゥルフ神話TRPG（通常版。自卓用は下の coc_shy を差し込んで使う）
│   │   └── ...                 # 詳細は systems/coc/structure.md
│   └── 🔒 coc_shy/               # 自卓用の追加部品（外しても通常版は動く）
│       ├── addon_shy.py        # 自卓用の機能を、CoC の差し込み口（systems/coc/addon_coc.py）につなぐ。pages/pages_coc_shy.py が使う
│       ├── pl_list.py          # hist/ の pl_list.txt / system_list.txt / pl_mapping.json / char_aliases.json の読み書き（マッピングツールと共用）。
│       │                       # 設定ファイルの書式の確かめ（形の違う所は読み飛ばす）と、保存する前の写し（hist/.backup）もここ
│       ├── param_fixes.py      # マッピングツールで保存したパラメータ増減の直し（param_fixes.json）を当てる（差し込み口 fix_param_changes から使う）
│       ├── shy_ui.py           # よみがなで選べる選択欄、タブを移っても編集を残す表、表の高さ、PLモードの並び順（自卓用の画面とマッピングツールで共用）
│       ├── local_hist/         # 履歴フォルダの読み込み、PLモード・PL名での絞り込み、キャラ統合（表記ブレ）の反映（ui_hist / logic_hist）
│       └── pl_stats/           # 「👥 PL統計」タブ（ui_pls / logic_pls。集計はマッピングツールの PL統計 タブと共用。パラメータ増減は ui_pl_params / logic_pl_params）
│
├── 🔒 tools/                     # 🗂️ マッピングツール（自卓用。マッピングツール起動.bat から起動）
│   ├── mapping.py              # 本体と「📝 割り当て」タブ（ログのキャラ → 担当PL・ロール（GM / PL / other）・ロストの印を pl_mapping.json に、
│   │                           # ログのシステムを log_systems.json に、セッションのシナリオのエンドを session_ends.json に保存）
│   ├── mapping_aliases.py      # 「🔗 キャラ統合」タブ（探索者の表記ブレを正式名にまとめる・似ている名前のお知らせ。保存すると直しの名前も正式名に付け替える）
│   ├── mapping_stats.py        # 「📊 PL統計」タブ（割り当ての確認用。集計は systems/coc_shy/pl_stats と共用）
│   ├── mapping_lists.py        # 「📚 PL・システム一覧」タブ（pl_list.txt と system_list.txt を表で編集。CoC は固定の行）
│   ├── mapping_params.py       # 割り当てタブの下の「パラメータ増減の直し」（SAN の開始・終了の直しと、集計から外すパラメータを param_fixes.json に保存）
│   ├── mapping_inspect.py      # 「🩺 点検」タブ（読めない設定ファイル・フォルダに無いログの設定・使われていない直しなどの片付けと、ログの名前を変える手助け）
│   └── make_backup.py          # コードのバックアップの zip を作る（大きな変更の前に。.venv と hist は入れない）
│
├── 🔒 hist/                      # 📁 自卓のデータ置き場（年ごとのフォルダ）
│   ├── pl_list.txt             # PLの一覧（コード <:::> 表示名 <:::> 並び順 <:::> * <:::> よみがな…。手で書き換えてもよい）
│   ├── char_aliases.json       # キャラ名の表記ブレの統合（正式名 → 表記ブレ。マッピングツールの「キャラ統合」で編集）
│   ├── char_not_same.json      # 名前は似ているが別のキャラ（PLの表示名ごと。似ている名前のお知らせを出さない組。マッピングツールで追加）
│   ├── system_list.txt         # システムの一覧（名前 <:::> 並び順 <:::> あまり使わないなら * <:::> よみがな…。手で書き換えてもよい）
│   ├── .backup/<日付>/         # マッピングツールで設定ファイルを保存する前の中身の写し（その日の最初の1回だけ。10日分残す）
│   └── <年>/                   # ログ本体と .cache/
│       └── .cache/             # parsed_logs.pkl（解析キャッシュ）・parsed_logs_files.json（キャッシュを作ったときのログと読み込み方の版）・
│                               # pl_mapping.json（PL対応表・ロストの印）・log_systems.json（ログごとのシステム）・
│                               # param_fixes.json（パラメータ増減の直し）・param_checked.json（直しを確認し終えたログと、そのときの表の目印）・
│                               # session_ends.json（セッションごとのシナリオのエンド）。解析キャッシュ以外はマッピングツールで保存
│
├── 🔒 check/                     # 確認用のサンプルログ（7版・6版の部屋の、古い形式・新しい形式の HTML と JSON）
│
└── 🔒 tests/
    ├── regression.py           # 回帰チェック（修正前後で計算結果が変わっていないか）
    ├── baseline.pkl.gz         # 回帰チェックの基準データ
    ├── logic_check.py          # CoC（公開する部分）の計算・絞り込みが仕様どおりかの確認（画面を使わない部分）
    ├── ui_check.py             # CoC（公開する部分）の画面の操作の確認（ボタンや入力欄を実際に操作する）
    ├── mapping_check.py        # マッピングツールと自卓用（coc_shy・tools・自卓用ページ）の確認（計算と画面の両方）
    ├── public_check.py         # 公開前チェック（公開するファイルだけを写して、目印なしで全部の画面を動かす・置くファイルの点検）
    ├── _common.py              # 確認スクリプトの共通部分（結果の数え方、一時的な hist/、確認用のログなど）
    └── _ui_common.py           # 画面の操作の確認の共通部分（ui_check と mapping_check で使う）
