#import streamlit as st
#from . import texts_manual as texts
#@st.dialog("ℹ️ アプリの使い方と仕様", width="large")
#def show_manuala():
#    st.markdown("### 辞書にない技能の扱いについて")
#    st.write("当ツールは6版/7版の基本ルールブックに基づく技能の初期値辞書を内蔵しています。")
#    st.write("ただし、**ルールブックに記載のないオリジナル技能**や、**誤字（タイポ）のある技能**は「❓初期値不明」として扱われます。これらは各設定画面の「辞書にない技能の扱い」オプションから、目標値を初期値として代用したり、除外したりと柔軟に対応可能です。")
#    st.markdown("※「回避」「母国語」など、ステータスにより変動する技能は、システム上暫定的に初期値100（絶対に初期値以下にならない）として扱われます。")
#    
#    st.divider()
#   
#    st.markdown("### その他の仕様")
#    st.write("・**成功の判定基準:** 総合サマリーと成長チェックで、それぞれ個別に「成功」とみなす基準（クリティカルのみ、初期値以下を含める等）を設定できます。")
#    st.write("・**B/Pダイス:** 成長チェックでは、7版ルールの原則に従い、ボーナス・ペナルティダイスを使用したロールを成長対象から除外する設定が可能です。")

import streamlit as st
from . import texts_manual as texts

@st.dialog("📖 クトゥルフ神話TRPG 解析マニュアル", width="large")
def show_manual():
    
    # 🌟 タブを4つに整理
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
        
        with st.expander("**📄 ファイル・タブ・キャラの選択**", expanded=True):
            st.markdown(texts.SIDEBAR_FILE_CHAR)
            
        with st.expander("**🎲 成功度フィルター**", expanded=False):
            st.markdown(texts.SIDEBAR_SUCCESS)
            with st.expander("**各成功度の説明**",expanded=False):
                st.markdown(texts.SIDEBAR_SUCCESS_KINDS)

        with st.expander("**🔢 出目数値フィルター**", expanded=False):
            st.markdown(texts.SIDEBAR_ROLL_VAL)

        with st.expander("**🎯 技能フィルター**", expanded=False):
            st.markdown(texts.SIDEBAR_SKILL)

        with st.expander("**🎯 ダイスコマンドフィルター**", expanded=False):
            st.markdown(texts.SIDEBAR_CMD1)
            with st.expander("**対応するダイスコマンド**", expanded=False):
                st.markdown(texts.SIDEBAR_CMD_KIND1)

            st.markdown(texts.SIDEBAR_CMD2)
            with st.expander("**難易度指定ロールの種類**", expanded=False):
                st.markdown(texts.SIDEBAR_CMD_KIND2)

            st.markdown(texts.SIDEBAR_CMD3)

        with st.expander("**🎲 判定の再計算ルール**", expanded=False):
            st.markdown(texts.SIDEBAR_RECALC)
            with st.expander("**再計算ルールの種類**", expanded=False):
                st.markdown(texts.SIDEBAR_RECALC_KIND)

        with st.expander("**⚙️ 解析・抽出オプション**", expanded=False):
            st.markdown(texts.SIDEBAR_EXTRA)

        with st.expander("**👥 キャラクターの統合**", expanded=False):
            st.markdown(texts.SIDEBAR_MERGE)
            
    # ------------------------------------------------
    # 3. 各画面の見方
    # ------------------------------------------------
    with t_features:
        with st.expander("**📊 総合サマリー 画面**", expanded=True):
            st.markdown(texts.FEATURE_SUMMARY)
        with st.expander("**🎲 条件別 確率集計 画面**", expanded=False):
            st.markdown(texts.FEATURE_PROB)
        with st.expander("**📈 成長チェック 画面**", expanded=False):
            st.markdown(texts.FEATURE_GROW1)
            with st.expander("**成長しない項目**", expanded=False):
                st.markdown(texts.FEATURE_GROW_KIND)
            st.markdown(texts.FEATURE_GROW2)
        with st.expander("**📜 生ログ表示 画面**", expanded=False):
            st.markdown(texts.FEATURE_LOG)
            
    # ------------------------------------------------
    # 4. よくある質問 (FAQ)
    # ------------------------------------------------
    with t_faq:
        st.markdown(texts.FAQ)
        
    st.divider()
    cols = st.columns([0.8, 0.2])
    with cols[1]:
        if st.button("閉じる", use_container_width=True):
            st.rerun()