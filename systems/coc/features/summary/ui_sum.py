import streamlit as st
import datetime
from components import common_ui as common
from ...components import export_coc as export
from ...core import utils_coc as utils
from ...components import filters_coc as filters_coc
from ...components.styles_coc import Templates
from . import logic_sum 
from . import html_sum 


# ==========================================
# 1. 補助UIの描画部品群
# ==========================================
def _render_grouped_checkboxes(disp_keys, disp_labels, prefix, recalc_rule):
    """サマリーの列項目を意味の塊で改行して表示する"""
    final_groups, other_keys, key_to_label = logic_sum.get_checkbox_groups(disp_keys, disp_labels, recalc_rule)
    
    for group_keys in final_groups:
        group_labels = [key_to_label[k].replace('(', '（').replace(')', '）') for k in group_keys]
        common.render_chunked_checkboxes(group_keys, group_labels, prefix=prefix, num_columns=4)

    if other_keys:
        st.markdown("<div style='margin-top: 0px; margin-bottom: 0px; border-top: 1px dashed #cbd5e1; padding-top: 6px;'></div>", unsafe_allow_html=True)
        other_labels = [key_to_label[k].replace('(', '（').replace(')', '）') for k in other_keys]
        common.render_chunked_checkboxes(other_keys, other_labels, prefix=prefix, num_columns=4)


def _render_table_settings(disp_keys, disp_labels, recalc_rule, default_active_keys):
    """表の表示列・並び替え設定のUIを描画し、設定値を返す"""
    with st.expander("🔽 表の表示・並び替え設定", expanded=False):
        
        def_states = {k: (k in default_active_keys) for k in disp_keys}
        for k in disp_keys: st.session_state.setdefault(f"col_chk_{k}", def_states[k])

        common.render_filter_header(
            title="▼ 表示する列の選択", 
            prefix="col_chk", 
            item_list=disp_keys, 
            default_states=def_states, 
            show_reset=True,
            title_style=Templates.FILTER_HEADER
        )
        _render_grouped_checkboxes(disp_keys, disp_labels, prefix="col_chk", recalc_rule=recalc_rule)
        
        selected_columns_keys = [k for k in disp_keys if st.session_state.get(f"col_chk_{k}")]

        st.divider()
        
        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>🔄 行の並び替え</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        sort_options_labels = ["キャラクター名"] + disp_labels
        sort_options_keys = ["char_name"] + disp_keys
        st.session_state.setdefault("sum_sort_order", "昇順 (A→Z / 低い順)")

        def _update_sum_order():
            if st.session_state.sum_sort_key == "キャラクター名":
                st.session_state.sum_sort_order = "昇順 (A→Z / 低い順)"
            else:
                st.session_state.sum_sort_order = "降順 (Z→A / 高い順)"
        with c1:
            sort_key_label = st.selectbox(
                "基準項目:", 
                sort_options_labels, 
                key="sum_sort_key", 
                on_change=_update_sum_order
            )
        with c2:
            sort_basis = c2.radio(
                "判定数値:", 
                ["確率（％）", "回数"], 
                horizontal=True, 
                key="sum_sort_basis"
            )
        with c3:
            sort_order_label = c3.radio(
                "順序:", 
                ["昇順 (A→Z / 低い順)", "降順 (Z→A / 高い順)"], 
                horizontal=True, 
                key="sum_sort_order"
            )
        
        sort_key = sort_options_keys[sort_options_labels.index(sort_key_label)]
        sort_order = "降順" if "降順" in sort_order_label else "昇順"

    return selected_columns_keys, sort_key, sort_basis, sort_order


def _render_highlight_settings(disp_keys, disp_labels, recalc_rule, char_count):
    """マスの強調表示(ハイライト)設定のUIを描画し、設定値を返す"""
    with st.expander("✨ マスの強調表示 (ハイライト設定)", expanded=False):
        default_hl_keys = ["succ_col", "cf_col", "クリティカル", "ファンブル", "1_crit", "100_fumb"]
        for k in disp_keys: st.session_state.setdefault(f"hl_chk_{k}", k in default_hl_keys)

        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>▼ 強調表示の有効化</div>", unsafe_allow_html=True)
        use_highlight = st.toggle(
            "ハイライト機能を有効にする", 
            value=st.session_state.setdefault("sum_hl_toggle", True), 
            key="sum_hl_toggle"
        )
        
        st.divider()
        
        default_states = {k: (k in default_hl_keys) for k in disp_keys}
        common.render_filter_header(
            title="▼ 強調する結果の選択", 
            prefix="hl_chk", 
            item_list=disp_keys, 
            default_states=default_states, 
            show_reset=True,
            title_style=Templates.FILTER_HEADER
        )
        _render_grouped_checkboxes(disp_keys, disp_labels, prefix="hl_chk", recalc_rule=recalc_rule)
        
        sel_highlights = [k for k in disp_keys if st.session_state.get(f"hl_chk_{k}")]

        st.divider()
        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>▼ ハイライトの判定基準</div>", unsafe_allow_html=True)
        c1, c2 = st.columns([0.25, 0.75])
        with c1:
            hl_basis = st.radio(
                "判定数値:", 
                ["確率（％）", "回数"], 
                horizontal=True, 
                key="hl_basis"
            )
        with c2:
            hl_type = st.radio(
                "強調する対象:", 
                ["最大と最小の両方", "最大/最高値", "最小/最低値"], 
                horizontal=True, 
                key="hl_type"
            )
        
        c1, c2 = st.columns([0.25, 0.75])
        with c1:
            include_zero = st.toggle(
                "最小値に 0 (0%) を含める", 
                value=st.session_state.setdefault("hl_include_zero", False), 
                key="hl_include_zero"
            )
        with c2:
            use_tie_disable = st.toggle(
                "同率（同じ値）がN人以上いる場合はハイライトを無効化する", 
                value=st.session_state.setdefault("hl_use_tie", False), 
                key="hl_use_tie"
            )
        
        disable_tie_count = None
        if use_tie_disable:
            if not char_count < 2:
                _, c2 = st.columns([0.25, 0.75]) 
                with c2:
                    disable_tie_count = st.selectbox(
                        "N = :", 
                        options=list(range(2, char_count + 1)),
                        index=0,  
                        key="hl_tie_count"
                    )
        
    return use_highlight, sel_highlights, hl_basis, hl_type, include_zero, disable_tie_count


# ==========================================
# 2. メイン関数（司令塔）
# ==========================================
def render_summary(df, recalc_rule):
    """サマリー画面全体の描画を統括するメイン関数"""
    if df.empty:
        st.info("表示できるデータがありません。")
        return
    st.markdown(html_sum.SUMMARY_CSS, unsafe_allow_html=True)

    # 1. 表示項目とUI設定の取得
    metrics_container = st.empty()
    st.divider()
    
    display_mode = st.radio(
        "表示形式:", 
        ["パーセント ＋ (回数)", "パーセント（％）のみ", "回数のみ"], 
        horizontal=True, 
        key="sum_disp_mode"
    )
    final_columns, disp_keys, disp_labels, default_keys = \
        logic_sum.get_column_definitions(list(df['結果'].unique()), recalc_rule, display_mode)
    
    selected_columns_keys, sort_key, sort_basis, sort_order = \
        _render_table_settings(disp_keys, disp_labels, recalc_rule, default_keys)
    
    # 2. 「成功」フラグの計算
    filter_all_res = utils.get_sorted_result(final_columns, recalc_rule, True)
    default_succ = [r for r in filter_all_res if utils.is_actual_success(r)]
    filter_config, _ = filters_coc.render_complex_condition_ui(
        "sum", 
        final_columns, 
        default_succ, 
        expander_title="🎯 「成功」としてカウントする基準", 
        recalc_rule=recalc_rule
    )

    df_calc = df.copy().reset_index(drop=True)
    df_calc['成功フラグ'] = utils.get_ui_condition_mask(df_calc, filter_config)
    selected_successes = filter_config["sel_target_res"]
    df_calc['_is_crit'] = df_calc['結果'].str.contains('クリティカル|決定的', na=False, regex=True)
    df_calc['_is_fumb'] = df_calc['結果'].str.contains('ファンブル|致命的', na=False, regex=True)


    # 3. ハイライトと集計ロジックの実行
    char_count = df_calc['キャラクター名'].nunique()
    use_highlight, sel_highlights, hl_basis, hl_type, include_zero, disable_tie_count = \
        _render_highlight_settings(disp_keys, disp_labels, recalc_rule, char_count)

    df_chars = logic_sum.calc_char_stats(df_calc, final_columns, sort_key, sort_basis, sort_order)
    overall_data = logic_sum.calc_overall_stats(df_calc, final_columns)
    max_dict, min_dict = logic_sum.get_min_max(df_chars, disp_keys, include_zero, disable_tie_count)
    
    check_max = "最大" in hl_type or "両方" in hl_type
    check_min = "最小" in hl_type or "両方" in hl_type

    # 4. HTML描画
    st.divider()
    c1, c2 = st.columns([0.75, 0.25], vertical_alignment="bottom")
    with c1: 
        st.markdown("**▼ キャラクター別 サマリー内訳**")
    with c2: 
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        export.render_screenshot_button("capture-summary", f"CoC_Summary_{now_str}")

    metrics_html = html_sum.build_metrics_html(overall_data, display_mode, disp_labels[1], disp_labels[2])
    metrics_container.markdown(metrics_html, unsafe_allow_html=True)
    
    table_html = html_sum.build_table_html(
        overall_data, df_chars, disp_keys, disp_labels, 
        selected_columns_keys, selected_successes, display_mode, 
        check_max, check_min, sel_highlights, max_dict, min_dict, use_highlight, hl_basis
    )
    st.markdown(
        f'<div id="capture-summary" style="background: white; padding: 0; border-radius: 8px;">{table_html}</div>', 
        unsafe_allow_html=True
    )