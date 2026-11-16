import streamlit as st
from components import common_ui as common
from ...core import results_coc as results
from ...core import conditions_coc as conditions
from ...components import export_coc as export
from ...components import filters_coc
from . import logic_prob
from . import html_prob

# ==========================================
# 1. 並び替え設定UI
# ==========================================
def _render_sort_options():
    """表示・並び替え設定のUIを描画し、(並び替えの基準, 昇順か, 信頼区間を出すか, 最小ロール数) を返す"""
    with st.expander("🔄 表示・並び替え設定", expanded=False):
        c1, c2 = st.columns(2)
        common.init_state("prob_sort_order", common.SORT_DESC)
        sort_basis = c1.selectbox(
            "基準項目:",
            logic_prob.SORT_BASIS_OPTIONS,
            key="prob_sort_basis",
            on_change=common.sort_order_updater("prob_sort_basis", "prob_sort_order", lambda basis: basis == logic_prob.SORT_BY_NAME)
        )
        sort_order_label = c2.radio(
            "順序:",
            common.SORT_ORDER_OPTIONS,
            horizontal=True,
            key="prob_sort_order"
        )
        ascending = "降順" not in sort_order_label

        st.divider()
        c1, c2 = st.columns(2)
        show_ci = c1.toggle("95%信頼区間を表示する", key="prob_show_ci",
                            help="回数が少ないと、たまたまの偏りで確率が大きくぶれます。本当の確率がだいたいこの範囲に入る、という幅を表示します。")
        common.init_state("prob_min_rolls", 1)
        min_rolls = c2.number_input("総ロール数がこの回数未満のキャラを隠す", min_value=1, max_value=9999, key="prob_min_rolls")
    return sort_basis, ascending, show_ci, min_rolls


# ==========================================
# 2. 🌟 メイン関数（司令塔）
# ==========================================
def render_probability_analysis(df, recalc_rule):
    if df.empty:
        st.info("集計対象のデータがありません。")
        return

    # 1. フィルターUIの描画と設定の取得
    res_types_actual = results.result_options(df, recalc_rule)

    filter_config, cond_text = filters_coc.render_complex_condition_ui(
        "prob",
        res_types_actual,
        results.success_results(res_types_actual),
        expander_title="🎯 確率集計用フィルター",
        recalc_rule=recalc_rule
    )
    adv_opts = filters_coc.render_adv_filters(
        df, 
        "prob_adv", 
        expander_title="🎯 ダイスコマンドフィルター"
    )
    sort_basis, ascending, show_ci, min_rolls = _render_sort_options()
    st.divider()

    # 2. データの絞り込み
    # ダイスコマンドの条件は「どのロールを数えるか」なので、分母（総ロール数）も絞り込む
    cmd_notes = filters_coc.describe_command_filter(df, adv_opts)   # ダイスコマンドの条件も、条件の下に添える
    df = df[conditions.command_mask(df, adv_opts)]
    total_rolls = len(df)
    target_df = df[conditions.get_ui_condition_mask(df, filter_config)]

    # 3. UI: 並び替えオプションの配置
    c1, _, c2 = st.columns([0.6, 0.15, 0.25], vertical_alignment="bottom")
    
    with c1:
        st.markdown("**▼ 抽出結果 ＆ キャラクター内訳**")
    with c2: 
        export.render_screenshot_button("capture-prob", "CoC_Probability")

    # 4. ロジック関数を呼び出して、計算・ソート済みのデータを受け取る
    char_stats = logic_prob.calc_char_stats(df, target_df, sort_basis, ascending)

    if char_stats.empty:
        st.info("条件に一致するデータがありません。")
        return
    hidden = char_stats["総ロール数"] < min_rolls
    if hidden.any():
        st.caption(f"総ロール数が{min_rolls}回未満の {int(hidden.sum())}人 を隠しています（全体の確率には含めています）。")
    char_stats = char_stats[~hidden]

    # 5. 全体確率の計算とHTMLの生成・描画
    matched = len(target_df)
    pct = (matched / total_rolls * 100) if total_rolls else 0
    ci = logic_prob.wilson_interval(matched, total_rolls) if show_ci else None

    html_str = html_prob.build_probability_html(cond_text, pct, matched, total_rolls, char_stats, ci, show_ci, cmd_notes)
    st.html(html_str)