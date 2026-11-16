import streamlit as st
from components import common_ui as common
from ...components import export_coc as export
from ...core import results_coc as results
from ...core import conditions_coc as conditions
from ...core import logic_coc
from ...components import filters_coc as filters_coc
from ...components import highlight_coc
from ... import profile_coc as profiles
from . import logic_sum
from . import html_sum


# ==========================================
# 1. 補助UIの描画部品群
# ==========================================
def _render_grouped_checkboxes(disp_keys, disp_labels, prefix, recalc_rule):
    """サマリーの列項目を意味の塊で改行して表示する"""
    final_groups, other_keys, key_to_label = logic_sum.get_checkbox_groups(disp_keys, disp_labels, recalc_rule)

    def render(keys):
        labels = [key_to_label[k].replace('(', '（').replace(')', '）') for k in keys]   # 括弧は全角で表示する
        common.render_chunked_checkboxes(keys, labels, prefix=prefix, num_columns=4)

    for group_keys in final_groups:
        render(group_keys)

    if other_keys:
        st.caption("その他")
        render(other_keys)


# 並び順の初期値（列のキー, 順序）。普通にログを入れた場合は名前順（後から足す機能は、ほかの初期値を渡せる）
DEFAULT_SORT = ("char_name", common.SORT_ASC)

def _render_table_settings(disp_keys, disp_labels, recalc_rule, default_active_keys, default_sort):
    """表の表示列・並び替え設定のUIを描画し、設定値を返す"""
    with st.expander("🔽 表の表示・並び替え設定", expanded=False):

        def_states = {k: (k in default_active_keys) for k in disp_keys}
        for k in disp_keys: common.init_state(f"col_chk_{k}", def_states[k])

        common.render_filter_header(
            title="▼ 表示する列の選択",
            prefix="col_chk",
            item_list=disp_keys,
            default_states=def_states,
            show_reset=True
        )
        _render_grouped_checkboxes(disp_keys, disp_labels, prefix="col_chk", recalc_rule=recalc_rule)

        selected_columns_keys = [k for k in disp_keys if st.session_state.get(f"col_chk_{k}")]

        st.divider()

        st.markdown("**🔄 行の並び替え**")
        c1, c2, c3 = st.columns(3)
        # 選択肢は列のキーで持つ（表示形式で「成功率」⇔「成功数」と名前が変わっても選択が外れないように）
        sort_options_keys = ["char_name"] + disp_keys
        key_to_label = dict(zip(sort_options_keys, ["キャラクター名"] + disp_labels))
        # 並び順の初期値（default_sort）が変わったら（自卓用の PLモード⇔PCモードの切り替えなど）、その初期値に戻す。
        # 「_」で始まる _sum_sort_default は「設定をリセット」でも消えないので、並び替えの設定が消えていたら（リセット後など）初期値を入れ直す
        if (st.session_state.get("_sum_sort_default") != default_sort
                or "sum_sort_key" not in st.session_state or "sum_sort_order" not in st.session_state):
            st.session_state["_sum_sort_default"] = default_sort
            st.session_state["sum_sort_key"], st.session_state["sum_sort_order"] = default_sort
        # 基準の列が選択肢から消えたら（版を切り替えた時など）、順序も一緒に初期値に戻す（名前が降順のまま残らないように）
        if st.session_state.get("sum_sort_key") not in sort_options_keys:
            if default_sort[0] in sort_options_keys:
                st.session_state["sum_sort_key"], st.session_state["sum_sort_order"] = default_sort
            else:
                st.session_state["sum_sort_key"], st.session_state["sum_sort_order"] = DEFAULT_SORT
        # 値は上で必ず入っている。書き直してブラウザに確実に伝える（common.init_state の説明を参照）
        common.init_state("sum_sort_key", default_sort[0])
        common.init_state("sum_sort_order", default_sort[1])
        with c1:
            sort_key = st.selectbox(
                "基準項目:",
                sort_options_keys,
                format_func=key_to_label.get,
                key="sum_sort_key",
                on_change=common.sort_order_updater("sum_sort_key", "sum_sort_order", lambda basis: basis == "char_name")
            )
        with c2:
            sort_basis = st.radio(
                "判定数値:",
                logic_sum.BASIS_OPTIONS,
                horizontal=True,
                key="sum_sort_basis"
            )
        with c3:
            sort_order_label = st.radio(
                "順序:",
                common.SORT_ORDER_OPTIONS,
                horizontal=True,
                key="sum_sort_order"
            )

    ascending = "降順" not in sort_order_label
    return selected_columns_keys, sort_key, sort_basis, ascending


def _render_highlight_settings(disp_keys, disp_labels, recalc_rule, char_count):
    """
    マスの強調表示(ハイライト)設定のUIを描画し、設定値（logic_sum.HighlightConfig）を返す（欄は highlight_coc で共通）。
    char_count: 比べる行の数（表のキャラの数）
    """
    # 6版の「決定的成功」「致命的失敗」も、7版の「クリティカル」「ファンブル」と同じく最初から強調する
    default_hl_keys = ["succ_col", "cf_col", "クリティカル", "ファンブル", "決定的成功", "致命的失敗", "1_crit", "100_fumb"]
    if profiles.current().summary_highlight_expected:
        default_hl_keys.append(logic_sum.EXPECTED_KEY)
    return highlight_coc.render_highlight_settings(
        highlight_coc.SUMMARY_KEYS, disp_keys, char_count, default_hl_keys,
        lambda _keys, prefix: _render_grouped_checkboxes(disp_keys, disp_labels, prefix=prefix, recalc_rule=recalc_rule),
        columns_title="▼ 強調する結果の選択")


# ==========================================
# 2. 🌟 メイン関数（司令塔）
# ==========================================
def render_summary(df, recalc_rule, default_sort=DEFAULT_SORT):
    """
    サマリー画面全体の描画を統括するメイン関数。
    default_sort: 行の並び順の初期値（列のキー, 順序）。普通は名前順
    """
    if df.empty:
        st.info("表示できるデータがありません。")
        return
    st.html(html_sum.SUMMARY_CSS)   # <style> だけの st.html は画面に場所を取らない

    # 1. 表示項目とUI設定の取得
    metrics_container = st.empty()
    st.divider()

    display_mode = st.radio(
        "表示形式:",
        logic_sum.DISPLAY_OPTIONS,
        horizontal=True,
        key="sum_disp_mode"
    )
    # 表示形式を切り替えたら、並び替えとハイライトの判定数値も表示に合わせる（出目の分布と同じく、
    # 「回数のみ」なら回数、「パーセント」を含む形式なら割合で比べる。判定数値は、その後に手で変えてもよい）
    if st.session_state.get("_sum_prev_disp_mode") != display_mode:
        st.session_state["_sum_prev_disp_mode"] = display_mode
        basis = logic_sum.BASIS_COUNT if display_mode == logic_sum.DISPLAY_COUNT else logic_sum.BASIS_PCT
        st.session_state["sum_sort_basis"] = basis
        st.session_state["hl_basis"] = basis
    final_columns, disp_keys, disp_labels, default_keys = \
        logic_sum.get_column_definitions(list(df['結果'].unique()), recalc_rule, display_mode,
                                         hide_detail_columns=profiles.current().summary_hide_detail_columns,
                                         show_expected=profiles.current().summary_show_expected)

    selected_columns_keys, sort_key, sort_basis, ascending = \
        _render_table_settings(disp_keys, disp_labels, recalc_rule, default_keys, default_sort or DEFAULT_SORT)

    # 2. 「成功」フラグの計算（final_columns は get_column_definitions で成功度の順に並べてある）
    filter_config, _ = filters_coc.render_complex_condition_ui(
        "sum",
        final_columns,
        results.success_results(final_columns),
        expander_title="🎯 「成功」としてカウントする基準",
        recalc_rule=recalc_rule
    )

    df_calc = df.reset_index(drop=True)   # 新しい表になるので、複製は要らない
    df_calc['_is_success'] = conditions.get_ui_condition_mask(df_calc, filter_config)
    selected_successes = filter_config.sel_target_res
    df_calc['_is_crit'] = results.map_results(df_calc['結果'], results.is_crit)
    df_calc['_is_fumb'] = results.map_results(df_calc['結果'], results.is_fumble)
    # 「期待成功率」「期待との差」の列用（救済を成功に数えるかは、成功率と同じくサイドバーの救済の設定に合わせる）
    df_calc['_exp_p'], df_calc['_exp_hit'] = logic_coc.expected_success(
        df_calc, recalc_rule, rescue=st.session_state.get('rescue_diff', False))

    # 3. ハイライトと集計ロジックの実行
    char_count = df_calc['キャラクター名'].nunique()
    hl = _render_highlight_settings(disp_keys, disp_labels, recalc_rule, char_count)

    df_chars = logic_sum.calc_char_stats(df_calc, final_columns, sort_key, sort_basis, ascending)
    overall_data = logic_sum.calc_overall_stats(df_calc, final_columns)
    max_dict, min_dict = logic_sum.get_min_max(df_chars, disp_keys, hl.include_zero, hl.tie_count, hl.min_rolls)

    # 4. HTML描画
    st.divider()
    c1, c2 = st.columns([0.75, 0.25], vertical_alignment="bottom")
    with c1:
        st.markdown("**▼ キャラクター別 サマリー内訳**")
    with c2:
        export.render_screenshot_button("capture-summary", "CoC_Summary")

    key_to_label = dict(zip(disp_keys, disp_labels))   # 列の並びは変わることがあるので、見出しはキーで引く
    metrics_html = html_sum.build_metrics_html(overall_data, display_mode, key_to_label["succ_col"], key_to_label["cf_col"])
    metrics_container.html(metrics_html)

    if not selected_columns_keys:   # パラメータ増減・出目の分布と同じ案内（名前の列だけの表は出さない）
        st.info("表示する列が選ばれていません。「🔽 表の表示・並び替え設定」で選んでください。")
        return
    table_html = html_sum.build_table_html(
        overall_data, df_chars, disp_keys, disp_labels,
        selected_columns_keys, selected_successes, display_mode,
        hl, max_dict, min_dict
    )
    # 大きなHTMLはMarkdownとして解析させずにそのまま描画する（ブラウザ側の負荷軽減）
    st.html(f'<div id="capture-summary">{table_html}</div>')
