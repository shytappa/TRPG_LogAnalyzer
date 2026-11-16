import streamlit as st
from . import texts_manual as texts

@st.dialog("📖 クトゥルフ神話TRPG 解析マニュアル", width="large")
def show_manual():
    
    t_start, t_sidebar, t_features, t_faq = st.tabs([
        "🔰 はじめに", 
        "⚙️ サイドバーの設定", 
        "📊 各画面の見方", 
        "❓ Q&A"
    ])
    
    # ------------------------------------------------
    # 1. はじめに（アコーディオンなしでスッキリ表示）
    # ------------------------------------------------
    with t_start:
        st.markdown(texts.START_ABOUT)
        st.markdown(texts.START_WARNING)
        st.divider()
        st.markdown("### 🛠️ ツールの使い方")
        st.markdown(texts.START_STEPS)
            
    # ------------------------------------------------
    # 2. サイドバーの設定（実際のUIに合わせてアコーディオン化）
    # ------------------------------------------------
    with t_sidebar:
        st.write("画面左側の「サイドバー」で行える高度な設定について解説します。")
        
        with st.expander("**📄 表示ファイル・タブ・キャラ**", expanded=True):
            st.markdown(texts.SIDEBAR_FILE_CHAR)
            
        with st.expander("**🎲 成功度フィルター**"):
            st.markdown(texts.SIDEBAR_SUCCESS)
            with st.expander("**各成功度の説明**"):
                st.markdown(texts.SIDEBAR_SUCCESS_KINDS)

        with st.expander("**🔢 出目・目標値フィルター**"):
            st.markdown(texts.SIDEBAR_ROLL_VAL)

        with st.expander("**🎯 技能フィルター**"):
            st.markdown(texts.SIDEBAR_SKILL)

        with st.expander("**🎯 ダイスコマンドフィルター**"):
            st.markdown(texts.SIDEBAR_CMD1)
            with st.expander("**対応するダイスコマンド**"):
                st.markdown(texts.SIDEBAR_CMD_KIND1)

            st.markdown(texts.SIDEBAR_CMD2)
            with st.expander("**難易度指定ロールの種類**"):
                st.markdown(texts.SIDEBAR_CMD_KIND2)

            st.markdown(texts.SIDEBAR_CMD3)

        with st.expander("**🎲 判定の再計算ルール**"):
            st.markdown(texts.SIDEBAR_RECALC)
            with st.expander("**再計算ルールの種類**"):
                st.markdown(texts.SIDEBAR_RECALC_KIND)

        with st.expander("**⚙️ 解析・抽出オプション**"):
            st.markdown(texts.SIDEBAR_EXTRA)

        with st.expander("**👥 キャラクターの統合**"):
            st.markdown(texts.SIDEBAR_MERGE)

        with st.expander("**🔄 設定をリセット**"):
            st.markdown(texts.SIDEBAR_RESET)

    # ------------------------------------------------
    # 3. 各画面の見方
    # ------------------------------------------------
    with t_features:
        with st.expander("**📊 総合サマリー 画面**", expanded=True):
            st.markdown(texts.FEATURE_SUMMARY)
        with st.expander("**🎲 条件別 確率集計 画面**"):
            st.markdown(texts.FEATURE_PROB)
        with st.expander("**📈 成長チェック 画面**"):
            st.markdown(texts.FEATURE_GROW1)
            with st.expander("**成長しない項目**"):
                st.markdown(texts.FEATURE_GROW_KIND)
            st.markdown(texts.FEATURE_GROW2)
        with st.expander("**🎯 出目の分布 画面**"):
            st.markdown(texts.FEATURE_DICE)
        with st.expander("**📉 パラメータ増減 画面**"):
            st.markdown(texts.FEATURE_PARAMS)
        with st.expander("**📋 生ログ一覧 画面**"):
            st.markdown(texts.FEATURE_LOG)

    # ------------------------------------------------
    # 4. よくある質問 (FAQ)
    # ------------------------------------------------
    with t_faq:
        st.markdown(texts.FAQ)
        
    st.divider()
    cols = st.columns([0.8, 0.2])
    with cols[1]:
        if st.button("閉じる", width="stretch"):
            st.rerun()
