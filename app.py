import streamlit as st
from components import styles_base as styles

# ==========================================
# 1. ページ構成の設定
# ==========================================
st.set_page_config(
    page_title="TRPG Log Analyzer Selector", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. カスタムCSSの適用
# ==========================================
# ランチャー用のフラグを立てて共通CSSを呼び出す
styles.apply_custom_css(is_launcher=True)

# ==========================================
# 3. サイドバー・ナビゲーション（手動作成）
# ==========================================
st.sidebar.title("📖 ページ選択")
if st.sidebar.button("🏠 システム選択", use_container_width=True, type="primary"):
    st.switch_page("app.py") 

if st.sidebar.button("🎲 クトゥルフ神話TRPG", use_container_width=True):
    st.switch_page("pages/pages_coc.py")

# ==========================================
# 4. メイン画面のUI描画
# ==========================================
st.title("🎲 TRPGログ解析ツール")
st.subheader("使用するシステムを選択してください")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    if st.button("クトゥルフ神話TRPG\n(6版/7版)", key="main_coc_btn", use_container_width=True):
        st.session_state.system = "coc"
        st.switch_page("pages/pages_coc.py")

with col2:
    st.button("エモクロアTRPG\n(開発中)", key="main_emo_btn", use_container_width=True, disabled=True)

st.markdown("---")
st.info("※左上の「>」ボタンからサイドバーメニューを開けます。")