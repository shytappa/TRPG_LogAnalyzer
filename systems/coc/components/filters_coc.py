import streamlit as st
from ..core import utils_coc as utils
from ..core import data_coc as data
from components import common_ui as common
from .styles_coc import Templates

# ==========================================
# 裏方1: セッションステート（初期値）の準備
# ==========================================
def _init_condition_state(prefix, sorted_all_res, default_succ_def):
    for r in sorted_all_res: 
        st.session_state.setdefault(f"{prefix}_chk_{r}", (r in default_succ_def))
    st.session_state.setdefault(f"{prefix}_l1", "AND")
    st.session_state.setdefault(f"{prefix}_use_init", False)
    st.session_state.setdefault(f"{prefix}_unk_behav", "目標値を初期値として代用する")
    st.session_state.setdefault(f"{prefix}_l2", "AND")
    st.session_state.setdefault(f"{prefix}_use_ranges", False)
    st.session_state.setdefault(f"{prefix}_num_ranges", 1)


# ==========================================
# 裏方2: 画面の描画（ボタンやチェックボックス）
# ==========================================
def _draw_condition_ui(prefix, header_title, sorted_all_res, default_succ_def):
    default_states = {r: (r in default_succ_def) for r in sorted_all_res}
    
    common.render_filter_header(
        title=header_title,
        prefix=f"{prefix}_chk",
        item_list=sorted_all_res,
        default_states=default_states,
        show_reset=True,
        title_style=Templates.FILTER_HEADER
    )
    
    common.render_chunked_checkboxes(item_keys=sorted_all_res, prefix=f"{prefix}_chk", num_columns=4)
    st.divider()
    c_l1, c_rest1, c_unk1 = st.columns([0.15, 0.4, 0.45])
    c_l1.radio("結合:", ["AND", "OR"], key=f"{prefix}_l1", label_visibility="collapsed")
    use_init_ui = c_rest1.checkbox("**初期値以下の出目を出した**", key=f"{prefix}_use_init")
    if use_init_ui:
        c_unk1.radio(
            "▼ ルルブにない技能の扱い", 
            ["目標値を初期値として代用する", "初期値を100として扱う (必ず含める)", "初期値を0として扱う (除外する)"], 
            key=f"{prefix}_unk_behav"
        )
    
    st.divider()
    c_l2, c_rest2 = st.columns([0.15, 0.85])
    c_l2.radio("結合:", ["AND", "OR"], key=f"{prefix}_l2", label_visibility="collapsed")
    use_ranges_ui = c_rest2.checkbox("**指定した数値範囲の出目を出した**", key=f"{prefix}_use_ranges")
    
    if use_ranges_ui:
        for i in range(st.session_state[f"{prefix}_num_ranges"]):
            rc1, rc2 = c_rest2.columns(2)
            rc1.number_input(
                f"範囲{i+1} 最小", 1, 100, 
                value=st.session_state.setdefault(f"{prefix}_min_{i}", 1), 
                key=f"{prefix}_min_{i}"
            )
            rc2.number_input(
                f"範囲{i+1} 最大", 1, 100, 
                value=st.session_state.setdefault(f"{prefix}_max_{i}", 5), 
                key=f"{prefix}_max_{i}"
            )
        
        def add_r(): st.session_state[f"{prefix}_num_ranges"] += 1
        def sub_r(): st.session_state[f"{prefix}_num_ranges"] -= 1
        bc1, bc2 = c_rest2.columns(2)
        bc1.button("＋ 範囲を追加", key=f"btn_add_{prefix}_r", type="tertiary", on_click=add_r)
        if st.session_state[f"{prefix}_num_ranges"] > 1:
            bc2.button("－ 減らす", key=f"btn_sub_{prefix}_r", type="tertiary", on_click=sub_r)


# ==========================================
# 裏方3: 入力結果の回収と、テキストの生成
# ==========================================
def _build_condition_config(prefix, sorted_all_res):
    sel_target_res = [r for r in sorted_all_res if st.session_state.get(f"{prefix}_chk_{r}", False)]
    logic1 = st.session_state.get(f"{prefix}_l1", "AND")
    use_init = st.session_state.get(f"{prefix}_use_init", False)
    unk_behav = st.session_state.get(f"{prefix}_unk_behav", "")
    logic2 = st.session_state.get(f"{prefix}_l2", "AND")
    use_ranges = st.session_state.get(f"{prefix}_use_ranges", False)
    
    active_ranges = []
    if use_ranges:
        for i in range(st.session_state.get(f"{prefix}_num_ranges", 1)):
            active_ranges.append((
                st.session_state.get(f"{prefix}_min_{i}", 1), 
                st.session_state.get(f"{prefix}_max_{i}", 5)
            ))

    res_text = ""
    if len(sel_target_res) < len(sorted_all_res) and len(sel_target_res) > 0:
        res_text = f"【 {', '.join(sel_target_res)} 】"
        
    init_text = "【 初期値以下 】" if use_init else ""
    
    range_text = ""
    if use_ranges and active_ranges:
        range_strs = [f"{min_v}〜{max_v}" for min_v, max_v in active_ranges]
        range_text = f"【 出目({ ' OR '.join(range_strs) }) 】"

    part1_2 = ""
    if res_text and init_text:
        part1_2 = f"{res_text} {logic1} {init_text}"
    elif res_text:
        part1_2 = res_text
    elif init_text:
        part1_2 = init_text

    final_cond_text = ""
    if part1_2 and range_text:
        final_cond_text = f"{part1_2} {logic2} {range_text}"
    elif part1_2:
        final_cond_text = part1_2
    elif range_text:
        final_cond_text = range_text
    else:
        final_cond_text = "全結果対象"

    filter_config = {
        "sel_target_res": sel_target_res,
        "logic1": logic1,
        "use_init": use_init,
        "unk_behav": unk_behav,
        "logic2": logic2,
        "use_ranges": use_ranges,
        "active_ranges": active_ranges
    }
    return filter_config, final_cond_text


# ==========================================
# 🌟 メイン関数 (司令塔)
# ==========================================
def render_complex_condition_ui(
        prefix, 
        all_possible_res, 
        default_succ_def, 
        header_title="▼ 以下の結果を含める", 
        expander_title="", 
        recalc_rule="7版"):
    
    sorted_all_res = utils.get_sorted_result(all_possible_res, recalc_rule, include_unfound_base=True)
    _init_condition_state(prefix, sorted_all_res, default_succ_def)

    with st.expander(expander_title, expanded=False):
        _draw_condition_ui(prefix, header_title, sorted_all_res, default_succ_def)

    return _build_condition_config(prefix, sorted_all_res)


# ==========================================
# コマンドフィルター専用関数 
# ==========================================
def _render_command_filter(full_df, prefix, num_cols):
    sel_cmds = []
    if 'コマンド' not in full_df.columns:
        return sel_cmds
    
    def _get_cmd_rank(c):
        try: return data.COMMAND_SORT_ORDER.index(c)
        except ValueError: return 999
        
    available_ids = sorted(
        full_df['コマンド'].dropna().unique().tolist(), 
        key=lambda x: (_get_cmd_rank(x), x) 
    )
    if not available_ids:
        return sel_cmds

    cmd_default_states = {cmd: (False if cmd == 'CANCEL' else True) for cmd in available_ids}
    for cmd in available_ids:
        st.session_state.setdefault(f"{prefix}_cmd_{cmd}", cmd_default_states[cmd])
    
    cmd_labels = [data.CMD_NAME_MAP.get(cmd, cmd) for cmd in available_ids]

    common.render_filter_header(
        title="▼ ダイスコマンド", 
        prefix=f"{prefix}_cmd", 
        item_list=available_ids, 
        default_states=cmd_default_states,
    )
    common.render_chunked_checkboxes(
        item_keys=available_ids, 
        item_labels=cmd_labels,
        prefix=f"{prefix}_cmd", 
        num_columns=num_cols
    )
    
    return [cmd for cmd in available_ids if st.session_state.get(f"{prefix}_cmd_{cmd}")]

# ==========================================
# 難易度フィルター専用関数
# ==========================================
def _render_diff_filter(full_df, prefix, num_cols):
    sel_diffs = []
    if '難易度' not in full_df.columns:
        return sel_diffs

    diff_keys = [d for d in ['通常', 'r', 'h', 'e', 'c'] if d in full_df['難易度'].values]
    if not diff_keys:
        return sel_diffs
    
    diff_labels = [data.DIFF_MAP.get(d, d) for d in diff_keys]
    for d in diff_keys:
        st.session_state.setdefault(f"{prefix}_diff_{d}", True)

    common.render_filter_header(
        title="▼ 難易度指定ロール", 
        prefix=f"{prefix}_diff", 
        item_list=diff_keys, 
    )
    common.render_chunked_checkboxes(
        item_keys=diff_keys, 
        item_labels=diff_labels,
        prefix=f"{prefix}_diff", 
        num_columns=num_cols
    )
    
    return [d for d in diff_keys if st.session_state.get(f"{prefix}_diff_{d}")]

# ==========================================
# 特殊ルール（B/Pダイス）除外UI
# ==========================================
def _render_bp_exclusion_ui(
        prefix, 
        default_b=False, default_p=False, 
        label_b="ボーナスダイスを使用したロールを除外", 
        label_p="ペナルティダイスを使用したロールを除外"
    ):
    """B/Pダイスの除外設定トグルを2つ並べて描画し、結果を返す共通UI"""
    st.markdown(
        "<div style='font-weight:bold; margin-top:6px; color: #000000;'>▼ B/Pダイス・複数ロールの除外</div>", 
        unsafe_allow_html=True
    )
    if prefix=="sb":
        c1, c2, c3 = st, st, st
    else:
        c1, c2, c3 = st.columns(3)

    exclude_b = c1.toggle(
        label_b, 
        value=st.session_state.get(f"{prefix}_ex_b", default_b), 
        key=f"{prefix}_ex_b"
    )
    exclude_p = c2.toggle(
        label_p, 
        value=st.session_state.get(f"{prefix}_ex_p", default_p), 
        key=f"{prefix}_ex_p"
    )
    exclude_multi = c3.toggle(
        "複数回ロール (x5など) を除外", 
        value=st.session_state.get(f"{prefix}_ex_multi", False), 
        key=f"{prefix}_ex_multi"
    )
    return exclude_b, exclude_p, exclude_multi

# ==========================================
# 🌟 統括するアドバンスフィルター関数 メイン窓口
# ==========================================
def render_adv_filters(
        full_df, 
        prefix, 
        default_b=False, default_p=False,
        expander_title="🎯 ダイスコマンド" 
    ):
    """コマンド・難易度・BP除外の3つを束ねて描画する統括関数"""
    is_sidebar = True if prefix=="sb" else False
    num_cols = 1 if is_sidebar else 4

    # 下位の関数を順番に呼び出す
    container = st.sidebar if is_sidebar else st
    
    with container.expander(expander_title, expanded=False):
        sel_cmds = _render_command_filter(full_df, prefix, num_cols)
        st.divider()
        sel_diffs = _render_diff_filter(full_df, prefix, num_cols)
        st.divider()
        exclude_b, exclude_p, exclude_multi = \
            _render_bp_exclusion_ui(prefix, default_b=default_b, default_p=default_p)

    return {
        'sel_cmds': sel_cmds, 
        'sel_diffs': sel_diffs,
        'exclude_b': exclude_b,
        'exclude_p': exclude_p,
        'exclude_multi': exclude_multi
    }

