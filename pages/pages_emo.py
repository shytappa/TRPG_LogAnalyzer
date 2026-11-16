import streamlit as st
from components import styles_base as styles
from components import sidebar_nav

# ==========================================
# エモクロアTRPG（開発中）
# ==========================================
# 解析処理は未実装。CoC版が固まったら systems/emo/ を作り、ここから起動する。
st.set_page_config(page_title="Emoklore Log Analyzer", layout="wide")
sidebar_nav.stop_if_shutdown()
styles.apply_custom_css()

st.title("🍃 エモクロアTRPG ログ解析")
st.info("エモクロアTRPG版は開発中です。左のサイドバーからシステムを選び直してください。")
sidebar_nav.render_sidebar_footer(current_system="emo")
