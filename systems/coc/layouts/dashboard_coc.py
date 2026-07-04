import streamlit as st
from ..features.summary         import ui_sum   as summary
from ..features.probability     import ui_prob  as probability
from ..features.growth          import ui_grow  as growth
from ..features.raw_log         import ui_log   as raw_log

def _render_status_caption(full_df, df_filtered, recalc_rule):
    status_texts = [
        f"📁読込済: {
            full_df['ファイル名'].nunique()}ファイル / {
                full_df['file_char'].nunique()}キャラ / {
                    len(full_df)}ロール",
        f"🔍表示中: {
            df_filtered['ファイル名'].nunique()}ファイル / {
                df_filtered['file_char'].nunique()}キャラ / {
                    len(df_filtered)}ロール",

        f"📜ルール: {recalc_rule}"
    ]
    st.caption(" ｜ ".join(status_texts))

def render_dashboard(full_df, df_filtered, recalc_rule):
    """【画面構築】ダッシュボード全体（4つのタブ）を描画する"""
    st.markdown("### 📊 解析ダッシュボード")
    _render_status_caption(full_df, df_filtered, recalc_rule)
    st.divider()

    tab_dash, tab_prob, tab_growth, tab_log = st.tabs([
        "📊 総合サマリー", 
        "🎲 条件別 確率集計", 
        "📈 成長チェック", 
        "📋 生ログ一覧"]
    )
        
    with tab_dash: 
        summary.render_summary(df_filtered, recalc_rule)
    with tab_prob: 
        probability.render_probability_analysis(df_filtered, recalc_rule)
    with tab_growth: 
        growth.render_growth_check(df_filtered, recalc_rule)
    with tab_log: 
        raw_log.render_raw_log(df_filtered, recalc_rule)