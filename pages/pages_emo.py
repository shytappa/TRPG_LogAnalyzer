import streamlit as st
import os
import sys
from components import styles_base as styles

# ==========================================
# 1. ユーザーへの即時フィードバック
# ==========================================
placeholder = st.empty()
placeholder.info("⏳ システムを読み込んでいます...")
styles.apply_custom_css()

# ==========================================
# 2. 実行環境のパス調整
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
coc_dir = os.path.abspath(os.path.join(current_dir, "..", "systems", "coc"))

if coc_dir not in sys.path:
    sys.path.append(coc_dir)

# ==========================================
# 3. メインアプリケーションの起動
# ==========================================
try:
    import systems.coc.app_coc
    placeholder.empty()
    systems.coc.app_coc.main()

except Exception as e:
    placeholder.empty() 
    st.error("⚠️ アプリケーションの起動中にエラーが発生しました。")
    st.exception(e)