import streamlit as st

# ※ ページ一覧（左上のナビゲーション）の非表示と、ライトテーマへの固定は .streamlit/config.toml で設定している
# ※ data-testid などで Streamlit の内部の要素を指定しているので、Streamlit を更新すると効かなくなることがある

# 色（Streamlit の標準の色に合わせたもの。CoC の画面の色は systems/coc/components/styles_coc.py の Colors）
LINK_TEXT = "#888888"          # 全選択・全解除などのリンク風のボタンの文字
TOGGLE_BUTTON_BG = "#f0f2f6"   # サイドバーの開く・閉じるボタンの背景（Streamlit の薄いグレー）
ERROR_TEXT = "#ef4444"         # サイドバーの注意の文字（重なっている統合など）

BASE_CSS = f"""
<style>
/* =========================================
   1. メイン画面（画面A）のアップローダー
========================================= */
section[data-testid="stMain"] [data-testid="stFileUploader"] {{ padding-bottom: 15px; container-type: inline-size; }}

/* ドロップゾーン全体（中央揃えレイアウト） */
section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] {{
    min-height: 400px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 15px;
    box-sizing: border-box;
    position: relative; }}

/* 参照ボタン（左端に置く） */
section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] button {{
    position: absolute;
    left: 40px;
    top: 50%;
    transform: translateY(-50%);
    margin: 0;
    padding: 10px 24px; }}

/* アップロード欄が狭いとき（スマホ・サイドバーを開いた狭い画面など）は、ボタンを左端に固定せず説明の文字と縦に並べる
   （重ならないように）。画面全体ではなくアップロード欄の幅で見る（上の container-type）。ドロップゾーンの高さ（ドラッグしたときの枠）はそのまま */
@container (max-width: 760px) {{
    section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] button {{   /* 上の左固定と同じ強さの書き方にする */
        position: static;
        transform: none; }}
    /* 説明の欄が残りの高さを全部使うとボタンが上の端に寄るので、ボタンと説明をまとめて真ん中に置く */
    section[data-testid="stMain"] [data-testid="stFileUploaderDropzoneInstructions"] {{ flex-grow: 0; }}
}}

/* ドロップゾーン内のテキスト */
section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] span {{ font-size: 18px; }}

/* =========================================
   2. サイドバーのUI調整
========================================= */
/* 文字が途切れないように折り返しを許可 */
[data-testid="stSidebar"] [data-testid="stCheckbox"] label div,
[data-testid="stSidebar"] [data-testid="stRadio"] label div {{
    white-space: normal;
    word-break: break-word;
    overflow: visible; }}

/* ラジオボタンの隙間を広げて押しやすく */
[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] > label {{ margin-bottom: 0.5em; }}

/* 複数行になった時、チェックボックスの四角を上寄せに固定 */
[data-testid="stSidebar"] [data-testid="stCheckbox"] label {{ align-items: flex-start; }}

/* =========================================
   3. 全選択・全解除ボタン（Tertiary Button）
========================================= */
/* ボタンを包む親要素を右寄せにする */
div[data-testid="stButton"]:has(button[kind="tertiary"]) {{
    display: flex;
    justify-content: flex-end;
    margin-top: 4px;
    overflow: hidden; }}

/* ボタン本体をコンパクトに */
button[kind="tertiary"] {{
    padding: 0px;
    min-height: 20px;
    max-width: 100%; }}

/* ボタン内のテキスト（リンク風） */
button[kind="tertiary"] p {{
    font-size: 12px;
    text-decoration: underline;
    color: {LINK_TEXT};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
    display: block; }}

/* =========================================
   4. サイドバーのヘッダー（透明化・スクロール追従）
========================================= */
[data-testid="stSidebarHeader"] {{
    position: sticky;
    top: 0px;
    z-index: 99998;
    background-color: transparent;
    pointer-events: none; }}

/* =========================================
   5. サイドバーの開く・閉じるボタン（丸いボタンにして浮かせる）
========================================= */
button[data-testid="stBaseButton-headerNoPadding"] {{
    pointer-events: auto;
    background-color: {TOGGLE_BUTTON_BG};
    border-radius: 50%;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    width: 42px;
    height: 42px;
    margin-top: 12px;
    margin-left: 12px;
    transition: 0.2s;
    z-index: 99999; }}

button[data-testid="stBaseButton-headerNoPadding"]:hover {{ transform: scale(1.1); }}

/* =========================================
   6. 区切り線（Divider）の余白調整
========================================= */
[data-testid="stSidebar"] hr {{
    margin-top: 10px;
    margin-bottom: 15px; }}
</style>
"""

# ランチャー画面（app.py）専用：メイン画面のシステム選択ボタンを大きくし、ボタン名の改行を表示する
LAUNCHER_CSS = """
<style>
section[data-testid="stMain"] .stButton > button { height: 100px; font-size: 18px; }
section[data-testid="stMain"] .stButton > button p { white-space: pre-line; }
</style>
"""

def apply_custom_css(is_launcher=False):
    """サイドバーやウィジェットの共通デザイン（CSS）を適用する"""
    # <style> だけの st.html は画面に場所を取らない（st.markdown だと空の行ができる）
    st.html(BASE_CSS)
    if is_launcher:
        st.html(LAUNCHER_CSS)
