import streamlit as st
from components import styles_base as styles
from components import sidebar_nav

# ==========================================
# 1. ページ構成の設定
# ==========================================
st.set_page_config(
    page_title="TRPG Log Analyzer Selector",
    layout="centered",
    initial_sidebar_state="collapsed"
)
sidebar_nav.stop_if_shutdown()
# ランチャー用のフラグを立てて共通CSSを呼び出す
styles.apply_custom_css(is_launcher=True)

# ==========================================
# 2. メイン画面：システムの選択ボタン
# ==========================================
# システムが増えたら3つずつ段を増やす。自卓用ページは別の段に分け、無ければ段ごと出さない
NUM_COLUMNS = min(3, len(sidebar_nav.SYSTEMS))

def _render_button_rows(pages, key_prefix):
    for i in range(0, len(pages), NUM_COLUMNS):
        cols = st.columns(NUM_COLUMNS)
        for col, p in zip(cols, pages[i:i + NUM_COLUMNS]):
            with col:
                if st.button(f"{p['name']}\n({p['note']})", key=f"{key_prefix}_{p['id']}",
                             width="stretch", disabled=not p.get("enabled", True)):
                    st.switch_page(p["page"])

st.title("🎲 TRPGログ解析ツール")
st.subheader("使用するシステムを選択してください")
st.markdown("---")
_render_button_rows(sidebar_nav.SYSTEMS, "main")

private_pages = sidebar_nav.available_private_pages()
if private_pages:
    st.caption("🔒 自卓用")
    _render_button_rows(private_pages, "private")

st.markdown("---")
st.info("※左上の「>」ボタンからサイドバーメニューを開けます。")

# ==========================================
# 3. サイドバー（他のページと同じ、ページ選択と終了ボタン）
# ==========================================
sidebar_nav.render_sidebar_footer(current_system="launcher")
