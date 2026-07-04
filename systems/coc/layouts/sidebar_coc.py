import streamlit as st
import pandas as pd
from ..core import utils_coc as utils
from components import common_ui as common
from ..components import filters_coc as filters_coc

# ==========================================
# 1. 成功度フィルター
# ==========================================
def _render_success_filter(full_df, recalc_rule):
    with st.sidebar.expander("🎲 成功度フィルター", expanded=True):
        all_res_options = utils.get_sorted_result(list(full_df['結果'].unique()), recalc_rule, True)
        for r in all_res_options:
            st.session_state.setdefault(f"res_{r}", True)
        common.render_filter_header("▼ 成功度", "res", all_res_options)
        common.render_chunked_checkboxes(all_res_options, prefix="res", num_columns=1)
        sel_success_levels = [r for r in all_res_options if st.session_state.get(f"res_{r}")]
    return sel_success_levels

# ==========================================
# 2. 出目数値フィルター
# ==========================================
def _render_roll_value_filter():
    with st.sidebar.expander("🔢 出目数値フィルター", expanded=True):
        # 1. 初期値判定 
        req_init_succ = st.checkbox("初期値以下の出目のみを含める", value=st.session_state.get("chk_req_init", False), key="chk_req_init")
        unk_behav_sb = "目標値を初期値として代用する"
        if req_init_succ:
            unk_behav_sb = st.radio(
                "▼ 辞書にない技能の扱い", 
                [
                    "目標値を初期値として代用する", 
                    "初期値を100として扱う (必ず含める)", 
                    "初期値を0として扱う (除外する)"
                ], 
                key="unk_behav_sb"
            )

        st.divider()

        # 2. 数値範囲指定 
        use_ranges = st.checkbox(
            "数値範囲で絞り込む", 
            value=st.session_state.get("chk_use_ranges", False), 
            key="chk_use_ranges"
        )
        active_ranges = []
        if use_ranges:
            if "num_ranges_filter" not in st.session_state: 
                st.session_state.num_ranges_filter = 1
            for i in range(st.session_state.num_ranges_filter):
                c1, c2 = st.columns(2)
                min_v = c1.number_input(
                    f"範囲{i+1} 最小", 1, 100, 
                    value=st.session_state.setdefault(f"min_f_{i}", 1), 
                    key=f"min_f_{i}"
                )
                max_v = c2.number_input(
                    f"範囲{i+1} 最大", 1, 100, 
                    value=st.session_state.setdefault(f"max_f_{i}", 100), 
                    key=f"max_f_{i}"
                )
                active_ranges.append((min_v, max_v))
                
            # ボタン群
            def add_range(): st.session_state.num_ranges_filter += 1
            def sub_range(): st.session_state.num_ranges_filter -= 1
        
            c1, c2 = st.columns(2)
            c1.button("＋ 範囲を追加", key="btn_add_f_range", type="tertiary", on_click=add_range)
            if st.session_state.num_ranges_filter > 1:
                c2.button("－ 減らす", key="btn_sub_f_range", type="tertiary", on_click=sub_range)
    return req_init_succ, unk_behav_sb, active_ranges

# ==========================================
# 3. 技能フィルター
# ==========================================
def _render_skill_filter(full_df, sel_chars, recalc_rule):
    with st.sidebar.expander("🎯 技能フィルター", expanded=False):
        char_filtered_df = full_df[full_df['file_char'].isin(sel_chars)] if sel_chars else pd.DataFrame(columns=full_df.columns)
        available_skills = char_filtered_df['ベース判定名'].unique().tolist() if not char_filtered_df.empty else []
        
        if not st.session_state.get('use_char_code_sort', False):
            available_skills = sorted(available_skills, key=lambda x: (utils.get_skill_sort_rank(x, recalc_rule), x))
        else:
            available_skills = sorted(available_skills)
        
        if "memory_sel_skills" not in st.session_state:
            st.session_state.memory_sel_skills = []

        use_skill_filter = st.checkbox("特定の技能のみに絞り込む", key="use_skill_filter")
        def format_skill_name(s):
            return "（技能名未入力）" if s == "---" else s
            
        if use_skill_filter:
            def _update_memory(avail_skills):
                current_sel = st.session_state.sel_skills_multi
                hidden_memory = [s for s in st.session_state.memory_sel_skills if s not in avail_skills]
                st.session_state.memory_sel_skills = current_sel + hidden_memory
            valid_defaults = [s for s in available_skills if s in st.session_state.memory_sel_skills]
            st.session_state["sel_skills_multi"] = valid_defaults

            sel_skills_ui = st.multiselect(
                "表示する技能を選択:", 
                available_skills, 
                format_func = format_skill_name, 
                placeholder = "技能を選んでください...", 
                key = "sel_skills_multi", 
                label_visibility = "collapsed",
                on_change = _update_memory, 
                args = (available_skills,)
            )
            sel_skills = sel_skills_ui if sel_skills_ui else available_skills
        else:
            sel_skills = available_skills
    return sel_skills


# ==========================================
# 4. 特殊ルールの除外オプション
# ==========================================
def _render_special_rules_filter(full_df): 
    adv_opts = filters_coc.render_adv_filters(
        full_df, 
        "sb",
        expander_title="🎯 ダイスコマンドフィルター"
    )    
    return {
        'exclude_b_global': adv_opts['exclude_b'], 
        'exclude_p_global': adv_opts['exclude_p'],
        'sel_cmds': adv_opts['sel_cmds'],
        'sel_diffs': adv_opts['sel_diffs'] 
    }

# ==========================================
# 4. 再計算ルール
# ==========================================
def _render_recalc_options(current_rule):
    with st.sidebar.expander("🎲 判定の再計算ルール", expanded=False):
        st.caption("ダイスログを各ルールに従い再計算します。")
        rules = [
            "7版ルールで再計算", 
            "クリファン5%（7版）で再計算", 
            "6版ルールで再計算", 
            "クリファン5%（6版）で再計算", 
            "再計算しない (ログの通り)"
        ]
        # 親から渡された current_rule を使って初期位置を決める
        idx = rules.index(current_rule) if current_rule in rules else 0
        
        st.radio(
            "recalc_rule_radio", 
            options=rules, 
            index=idx, 
            key="recalc_rule", 
            label_visibility="collapsed"
        )
    return st.session_state.get("recalc_rule", current_rule)

# ==========================================
# 5. 解析・抽出オプション
# ==========================================
def _render_extra_options():
    with st.sidebar.expander("⚙️ 解析・抽出オプション", expanded=False):
        st.toggle(
            "技能名を文字コード順で並べる", 
            value = st.session_state.get('use_char_code_sort', False), 
            key = "use_char_code_sort"
        )

        st.toggle(
            "B/Pダイスの内訳を抽出", 
            value = st.session_state.get("extract_bp", False), 
            key = "extract_bp"
        )
        if st.session_state.get("extract_bp", False):
            st.toggle(
                "B/Pダイスの内訳を通常結果に統合", 
                value = st.session_state.get("chk_int_bp", False), 
                key = "chk_int_bp"
            )
            
        st.toggle(
            "難易度指定ロールの失敗を救済", 
            value = st.session_state.get("rescue_diff", False), 
            key = "rescue_diff"
        )
        if st.session_state.get("rescue_diff", False):
            st.toggle(
                "救済結果を通常結果に統合", 
                value = st.session_state.get("chk_int_rescue", False), 
                key = "chk_int_rescue"
            )

    return {
        'chk_int_bp': st.session_state.get("chk_int_bp", False),
        'chk_int_rescue': st.session_state.get("chk_int_rescue", False)
    }

# ==========================================
# 🌟 メイン関数（司令塔）
# ==========================================
def render_coc_filters(full_df, sel_chars, recalc_rule):
    """【司令塔】CoC固有のフィルター設定UI全体を描画し、設定を返す"""
    # 1. 各パーツを描画し、結果を受け取る
    sel_success_levels = _render_success_filter(full_df, recalc_rule)
    req_init_succ, unk_behav_sb, active_ranges = _render_roll_value_filter()
    sel_skills = _render_skill_filter(full_df, sel_chars, recalc_rule)
    special_rules_opts = _render_special_rules_filter(full_df)
    st.sidebar.divider()
    current_recalc_rule = _render_recalc_options(recalc_rule) 
    extract_opts = _render_extra_options()
    
    # 2. 辞書にまとめて返す
    return {
        'recalc_rule': current_recalc_rule,
        'sel_skills': sel_skills,
        'sel_success_levels': sel_success_levels,
        'active_ranges': active_ranges,
        'req_init_succ': req_init_succ,
        'unk_behav_sb': unk_behav_sb,
        'exclude_b_global': special_rules_opts['exclude_b_global'],
        'exclude_p_global': special_rules_opts['exclude_p_global'],
        'sel_cmds': special_rules_opts.get('sel_cmds', []),
        'sel_diffs': special_rules_opts.get('sel_diffs', []),
        **extract_opts
    }