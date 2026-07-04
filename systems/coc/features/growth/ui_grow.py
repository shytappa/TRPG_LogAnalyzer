import streamlit as st
import datetime
from ...core import utils_coc as utils
from ...components import export_coc as export
from ...components import filters_coc
from ...components.styles_coc import Templates
from . import logic_grow 
from . import copy_grow
from . import html_grow

# ==========================================
# 裏方1: 設定UIの描画部品
# ==========================================
def _render_settings_ui(df, tmp_rule, all_possible_res, default_succ_def):
    """設定用のアコーディオンパネルを描画し、ユーザーの入力値をすべて返す"""
    with st.expander("⚙️ 成長チェックの表示・絞り込み設定", expanded=False):
        c1, c2 = st.columns(2)
        hide_non_grow = c1.toggle(
            "成長しない項目（アイデア、幸運など）を除外", 
            value=st.session_state.get("gr_hide_non_grow", True),
            key="gr_hide_non_grow")
        hide_sanity = c1.toggle(
            "正気度ロールを除外", 
            value=st.session_state.get("gr_hide_sanity", True), 
            disabled=hide_non_grow, 
            key="gr_hide_sanity")
        ignore_target = c2.toggle(
            "目標値の違いを無視", 
            value=st.session_state.get("gr_ign_tgt", True), 
            key="gr_ign_tgt")
        only_growth = c2.toggle(
            "成長チェック(☑️)がついた技能のみ表示", 
            value=st.session_state.get("gr_only_gr", False), 
            key="gr_only_gr")
        
        st.divider()
        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>📋 詳細内訳の表示</div>", unsafe_allow_html=True)
        detail_mode = st.radio(
            "詳細内訳", 
            ["表示しない", "成功のみ表示", "すべて表示する"], 
            horizontal=True, 
            label_visibility="collapsed",
            key="gr_detail_mode")

        st.divider()
        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>🔄 行の並び替え</div>", unsafe_allow_html=True)
        c3, c4, c5 = st.columns(3)
        sort_check_top = c3.checkbox(
            "☑️ チェックがついた技能を優先", 
            value=st.session_state.get("gr_sort_check_top", True), 
            key="gr_sort_check_top")
            
        st.session_state.setdefault("gr_sort_order_rad", "昇順 (A→Z / 低い順)")
        
        def _update_grow_order():
            if "技能名順" in st.session_state.gr_sort_basis_sel:
                st.session_state.gr_sort_order_rad = "昇順 (A→Z / 低い順)"
            else:
                st.session_state.gr_sort_order_rad = "降順 (Z→A / 高い順)"

        sort_basis = c4.selectbox(
            "基準項目:", 
            ["技能名順", "総数順", "合計成功数順"],
            key="gr_sort_basis_sel",
            on_change=_update_grow_order
        )
        sort_order = c5.radio(
            "順序:", 
            ["昇順 (A→Z / 低い順)", "降順 (Z→A / 高い順)"], 
            key="gr_sort_order_rad"
        )
        sort_order = "降順" if "降順" in sort_order else "昇順"

    filter_config, _ = filters_coc.render_complex_condition_ui(
        "gr", all_possible_res, 
        default_succ_def, 
        header_title="▼ 成長対象とする結果", 
        expander_title="☑️ 成長マークの付与条件: ダイス結果", 
        recalc_rule=tmp_rule
    )
    adv_opts = filters_coc.render_adv_filters(
        df, "gr_adv", 
        default_b=True, default_p=False,
        expander_title="☑️ 成長マークの付与条件: ダイスコマンド"
    )
    filter_config.update(adv_opts)
    check_growth_mask = utils.get_ui_condition_mask(df, filter_config)

    config = {
        'hide_non_grow': hide_non_grow, 
        'hide_sanity': hide_sanity,
        'ignore_target': ignore_target, 
        'only_growth': only_growth,
        'sel_cmds': adv_opts['sel_cmds'],
        'sel_diffs': adv_opts['sel_diffs'], 
        'exclude_b': adv_opts['exclude_b'], 
        'exclude_p': adv_opts['exclude_p']
    }
    return config, detail_mode, sort_check_top, sort_basis, sort_order, check_growth_mask


# ==========================================
# メイン関数（司令塔）
# ==========================================
def render_growth_check(df, recalc_rule):
    if df.empty:
        st.info("集計対象のデータがありません。")
        return
    
    all_possible_res = utils.get_sorted_result(list(df['結果'].unique()), recalc_rule, True)
    default_succ_def = [r for r in all_possible_res if utils.is_actual_success(r)]
    
    # 1. UIから設定を受け取る
    config, detail_mode, sort_check_top, sort_basis, sort_order, check_growth_mask = \
        _render_settings_ui(df, recalc_rule, all_possible_res, default_succ_def)
    st.divider()

    # 2. ロジック関数でデータを処理・集計する
    df_growth = logic_grow.process_growth_data(df, recalc_rule, check_growth_mask, config)

    if not df_growth.empty:
        chars_present = list(df_growth['キャラクター名'].unique())

        c1, c2, c3 = st.columns([0.5, 0.25, 0.25], vertical_alignment="bottom")
        
        with c1:
            selected_char = st.selectbox("👤 キャラクターを選択:", chars_present, key="gr_char_select")
        
        # 3. 選択されたキャラクターで合算
        char_df = df_growth[df_growth['キャラクター名'] == selected_char].copy()

        # 4. ロジック関数で並び替え
        use_char_code = st.session_state.get('use_char_code_sort', False)
        char_df = logic_grow.sort_growth_data(char_df, sort_check_top, sort_basis, sort_order, recalc_rule, use_char_code)
        
        # 5. エクスポートボタン（コピー＆スクショ）の配置
        copy_text = logic_grow.generate_copy_text(char_df, selected_char)
        with c2: 
            copy_grow.render_copy_button(copy_text)
        with c3: 
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            export.render_screenshot_button("capture-growth", f"CoC_Growth_{now_str}")
        
        # 6. html_grow に委譲して HTMLを組み立てて表示
        html_str = html_grow.build_cards_html(char_df, selected_char, detail_mode)
        st.markdown(html_str, unsafe_allow_html=True)
    else:
        st.info("条件に一致するデータがありません。")