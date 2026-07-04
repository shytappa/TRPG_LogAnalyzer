import streamlit as st
import datetime
from ...core import utils_coc as utils
from ...components import export_coc as export
from ...components import filters_coc
from . import logic_prob
from . import html_prob

def _render_sort_options():
    """表示・並び替え設定のUIを描画し、選択された基準と順序を返す"""
    with st.expander("🔄 行の並び替え", expanded=False):
        c1, c2 = st.columns(2)
        st.session_state.setdefault("prob_sort_order", "降順 (Z→A / 高い順)")
        def _update_prob_order():
            if st.session_state.prob_sort_basis == "名前":
                st.session_state.prob_sort_order = "昇順 (A→Z / 低い順)"
            else:
                st.session_state.prob_sort_order = "降順 (Z→A / 高い順)"
        sort_basis = c1.selectbox(
            "基準項目:", 
            logic_prob.SORT_BASIS_OPTIONS, 
            key="prob_sort_basis", 
            on_change=_update_prob_order
        )
        sort_order_label = c2.radio(
            "順序:", 
            ["昇順 (A→Z / 低い順)", "降順 (Z→A / 高い順)"],
            key="prob_sort_order"
        )
        sort_order = "降順" if "降順" in sort_order_label else "昇順"
    return sort_basis, sort_order


# ==========================================
# 🌟 メイン関数（司令塔）
# ==========================================
def render_probability_analysis(df, recalc_rule):
    total_rolls = len(df)
    if total_rolls == 0: 
        st.info("集計対象のデータがありません。")
        return
        
    # 1. フィルターUIの描画と設定の取得
    res_types_actual = utils.get_sorted_result(list(df['結果'].unique()), recalc_rule, True)
    default_succ_def = [r for r in res_types_actual if utils.is_actual_success(r)]
    
    filter_config, cond_text = filters_coc.render_complex_condition_ui(
        "prob", 
        res_types_actual, 
        default_succ_def, 
        expander_title="🎯 確率集計用フィルター", 
    )
    adv_opts = filters_coc.render_adv_filters(
        df, 
        "prov_adv", 
        expander_title="🎯 ダイスコマンドフィルター"
    )
    filter_config.update(adv_opts)
    
    sort_basis, sort_order = _render_sort_options()
    st.divider()

    # 2. データの絞り込み
    check_cond_mask = utils.get_ui_condition_mask(df, filter_config)
    target_df = df[check_cond_mask]

    # 3. UI: 並び替えオプションの配置
    c1, _, c2 = st.columns([0.6, 0.15, 0.25], vertical_alignment="bottom")
    
    with c1:
        st.markdown("**▼ 抽出結果 ＆ キャラクター内訳**")
    with c2: 
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        export.render_screenshot_button("capture-prob", f"CoC_Probability_{now_str}")

    # 4. ロジック関数を呼び出して、計算・ソート済みのデータを受け取る
    char_stats = logic_prob.calc_char_stats(df, target_df, sort_basis, sort_order)
    
    if char_stats.empty:
        st.info("条件に一致するデータがありません。")
        return

    # 5. 全体確率の計算とHTMLの生成・描画
    matched = len(target_df)
    pct = (matched / total_rolls * 100) if total_rolls else 0
    
    html_str = html_prob.build_probability_html(cond_text, pct, matched, total_rolls, char_stats)
    st.markdown(html_str, unsafe_allow_html=True)