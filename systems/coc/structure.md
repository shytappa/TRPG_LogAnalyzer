systems/coc/
│
├── app_coc.py                  # 👑 CoC解析の司令塔（ページのメイン処理）
├── profile_coc.py              # ⚙️ プロファイル（初期値・後から足す機能）の型と通常版の設定。自卓用の設定は pages/pages_coc_shy.py 側に置く
├── addon_coc.py                # 🔌 後から機能を足す差し込み口（何もしない既定の形）。通常版の処理は、足す機能の中身を知らない
│
├── layouts/                    # 🖼️ 画面の大枠・骨組み（レイアウト）
│   ├── dashboard_coc.py        # メイン画面（6つのタブ）の枠組み
│   └── sidebar_coc.py          # CoC専用フィルターを並べるサイドバーの枠組み
│
├── components/                 # 🧩 CoC専用の細かいUI部品
│   ├── badges_coc.py           # キャラクター名のバッジ生成
│   ├── filters_coc.py          # CoC独自の絞り込みUI（B/Pダイス除外など）
│   ├── highlight_coc.py        # マスの強調表示（ハイライト）の設定欄（総合サマリー・パラメータ増減・出目の分布で共通）
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
│   ├── params/                 # パラメータ増減（SAN・HP・MP・幸運の増減。ログからの読み取りは core/param_changes.py）
│   │   ├── ui_params.py
│   │   ├── logic_params.py
│   │   └── html_params.py
│   │
│   ├── dice/                   # 出目の分布（キャラごとに、出目が 1〜10・11〜20…のどこに何回入ったか。10ずつ・5ずつ）
│   │   ├── ui_dice.py
│   │   ├── logic_dice.py
│   │   └── html_dice.py
│   │
│   └── manual/                 # 使い方・マニュアル表示
│       ├── manual_coc.py
│       └── texts_manual.py     # マニュアルの本文
│
│   ※ 自卓用の機能（履歴・PLモード・PL統計・マッピングツールで保存した直しを当てる部分）は systems/coc_shy/ にある
│     （ルートの structure.md を参照）。通常版の処理からは読み込まないので、フォルダごと外しても動く。
│     自卓用からしか使わない部品は、公開版の側に置かず systems/coc_shy/ に置く
│
└── core/                       # 🧠 純粋なデータ処理（※UIは一切含めない）
    ├── rules_coc.py            # 再計算ルール（7版/6版/クリファン5%/再計算しない）の定義
    ├── logic_coc.py            # クトゥルフ独自の成功度判定・集計ロジック
    ├── results_coc.py          # 判定結果の分類（成功・クリ・ファン）と並び順
    ├── skills_coc.py           # 技能名の整形、初期値・技能の並び順の照会
    ├── conditions_coc.py       # 絞り込み条件（初期値以下、B/P除外、各画面の条件設定）のマスク
    ├── parser_coc.py           # 1発言から CoC のロールの行を作る処理（ファイルの読み取りは core/ccfolia_reader.py）
    └── data_coc.py             # 技能の一覧（版ごとに 正式名・初期値・並び順・別名・成長するか を1行で）と、成功度の並び順など


## 書き方の決まり

- **データの列名**：ログから読み取った値や、画面に出す集計結果の列は日本語（例: `キャラクター名`, `出目`, `結果`, `初期値`）。
  処理の途中で使うだけの作業列は `_` で始まる英語（例: `_file_char`, `_clean_skill_name`, `_init_unknown`, `_is_success`）。
- **入力欄の初期値**：`common.init_state(キー, 初期値)` で入れ、ウィジェットには `key=` だけを渡す（`value=` / `index=` は使わない）。
  初期値を2か所で決めると、Streamlit が警告を出したり、どちらの値が効くか分かりにくくなるため。
  例外は、キャラ統合の編集欄のように保存済みのデータをそのまま編集する欄と、空欄に戻せる数字の欄にするための `value=None`
  （目標値の範囲の「最大」（filters_coc.render_range_inputs）、パラメータ増減の「SAN の開始・終了を直す」欄。
  指定しないと、一度数字を入れた後に消すと最小値の 0 が入ってしまう。初期値を入れる指定ではないので、警告は出ない）。
- **選択肢が変わるチェックボックス**（成功度・ダイスコマンド・難易度など、ルールや読み込むログで項目が変わるもの）は
  `common.render_option_checkboxes` で作る。一時的に選択肢から消えた項目の値も、自動で書き戻しの対象になる。
- **値を書き戻さない部品の key**：ボタンは `btn_`、表の行選択・タブ・開閉を見る欄は `nokeep_` で始める。
  開いていないタブの設定を残す処理（`common.keep_widget_state`）が、これらを書き戻さないように飛ばすため。


