"""
CoC Log Analyzer - Main Application (司令塔)
"""

# ==========================================
# 1. ライブラリ・モジュールのインポート
# ==========================================
import streamlit as st
import os
import time
import threading
import signal

from core import logic_base as logic_base
from components import sidebar_base as sidebar_base

from .core import parser_coc as parser
from .core import logic_coc as logic_coc
from .layouts import sidebar_coc as sidebar_coc
from .layouts import dashboard_coc as dashboard_coc
from .features.manual import manual_coc as manual
from .components import styles_coc as styles

# ==========================================
# 2. システム管理・共通UIパーツ
# ==========================================
def _render_shutdown_confirm():
    """【画面C】終了確認画面"""
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.warning("### ⚠️ 本当にシステムを終了しますか？")
    st.write("保存されていない設定は失われます。")
    
    c1, c2, _ = st.columns([0.2, 0.2, 0.6])
    with c1:
        if st.button("はい、終了します", type="primary", use_container_width=True):
            st.session_state.shutdown_triggered = True
            st.session_state.show_shutdown_confirm = False
            st.rerun()
    with c2:
        if st.button("いいえ、戻ります", use_container_width=True):
            st.session_state.show_shutdown_confirm = False
            st.rerun()

def _execute_shutdown():
    """【裏方処理】安全なシステム終了"""
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.error("### 🛑 システムを終了しました")
    st.info("ご利用ありがとうございました。このタブやウィンドウは閉じて構いません。")
    st.components.v1.html("<script>window.close();</script>", height=0)

    def delayed_kill():
        time.sleep(2)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=delayed_kill).start()
    st.stop()

def _render_header():
    """【共通UI】タイトル描画"""
    c1, c2 = st.columns([0.85, 0.15])
    c1.title("🛠️ クトゥルフ神話TRPG ログ解析")
    if c2.button("ℹ️ 使い方・仕様", use_container_width=True):
        manual.show_manual()


# ==========================================
# 3. 画面の描画処理（View）
# ==========================================
def _render_upload_screen():
    """【画面A】アップロード画面"""
    uploaded_files = st.file_uploader(
        "ログファイル（.html / .txt）をドロップ", 
        type=["html", "txt"], 
        accept_multiple_files=True
    )
    if uploaded_files:
        for f in uploaded_files: 
            if f.name not in st.session_state.file_dict:
                raw_bytes = f.getvalue()
                try:
                    decoded_text = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    decoded_text = raw_bytes.decode('cp932', errors='replace')
                
                st.session_state.file_dict[f.name] = decoded_text
        st.rerun()

def _render_dashboard_screen():
    """【画面B】ダッシュボードメイン画面"""
    # 0. 注文の事前受け取り（スッキリ化）
    recalc_rule = st.session_state.get('recalc_rule', '7版ダイスで再計算')
    extract_bp  = st.session_state.get('extract_bp', False)
    rescue_diff = st.session_state.get('rescue_diff', False)

    # 1. データの仕入れ
    with st.spinner("ログを解析中..."):
        full_df = parser.get_all_parsed_data(st.session_state.file_dict)

    if full_df.empty:
        st.warning("ダイスロールが見つかりませんでした。")
    else:
        # 2. データの加工
        full_df = logic_coc.preprocess_raw_data(full_df, extract_bp, rescue_diff, recalc_rule)
        full_df = logic_base.add_search_keys(full_df)
        
        selector_params = sidebar_base.render_file_char_selector(full_df)
        coc_params = sidebar_coc.render_coc_filters(full_df, selector_params['sel_chars'], recalc_rule)
        merge_params = sidebar_base.render_character_merge_ui(full_df)

        filter_params = {**selector_params, **coc_params, **merge_params}

        df_filtered = logic_base.universal_filters(full_df, filter_params)
        df_filtered = logic_coc.apply_coc_specific_filters(df_filtered, filter_params)

        dashboard_coc.render_dashboard(full_df, df_filtered, recalc_rule)


# ==========================================
# 4. メインアプリケーション（Controller）
# ==========================================
def main():
    st.set_page_config(page_title="CoC Log Analyzer", layout="wide")

    # セッションステートの初期化
    if "file_dict" not in st.session_state: 
        st.session_state.file_dict = {}
    if "show_shutdown_confirm" not in st.session_state: 
        st.session_state.show_shutdown_confirm = False
    if "shutdown_triggered" not in st.session_state: 
        st.session_state.shutdown_triggered = False

    # ヘッダーとサイドバー
    st.markdown(styles.COC_GLOBAL_CSS, unsafe_allow_html=True)
    sidebar_base.render_file_manager()
    _render_header()

    # 画面の分岐
    if st.session_state.shutdown_triggered:
        _execute_shutdown()
    elif st.session_state.show_shutdown_confirm:
        _render_shutdown_confirm()
    elif not st.session_state.file_dict:
        _render_upload_screen()
    else:
        _render_dashboard_screen()

    sidebar_base.render_sidebar_footer(current_system="coc")

if __name__ == "__main__":
    main()