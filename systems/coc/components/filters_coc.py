import streamlit as st
from ..core import results_coc as results
from ..core import conditions_coc as conditions
from ..core import data_coc as data
from ..core import rules_coc as rules
from components import common_ui as common

# ==========================================
# 1-1. 条件設定UI：入力欄の初期値
# ==========================================
def _init_condition_state(prefix, sorted_all_res, default_succ_def):
    for r in sorted_all_res: 
        common.init_state(f"{prefix}_chk_{r}", (r in default_succ_def))
    common.init_state(f"{prefix}_l1", "AND")
    common.init_state(f"{prefix}_use_init", False)
    common.init_state(f"{prefix}_unk_behav", conditions.UNK_USE_TARGET)
    common.init_state(f"{prefix}_l2", "AND")
    common.init_state(f"{prefix}_use_ranges", False)
    common.init_state(f"{prefix}_l3", "AND")
    common.init_state(f"{prefix}_use_target", False)
    # 範囲の数（{prefix}_num_ranges）は、範囲の入力欄を出すときに render_range_inputs が初期値を入れる


# ==========================================
# 1-2. 条件設定UI：画面の描画（チェックボックス・範囲入力）
# ==========================================
DICE_LIMITS = (1, 100)   # 出目として入力できる値

def render_range_inputs(container, prefix, default_max, limits=DICE_LIMITS, default_min=1):
    """
    「○〜○」の範囲を複数指定する入力欄（＋追加／－減らすボタン付き）を描画し、範囲のリストを返す（出目・目標値で共通）。
    limits: 入力できる最小・最大（None なら決めない） / default_min・default_max: 新しく出す範囲の初期値。
    limits の最大が None（目標値）なら、最大の欄は空欄にでき、空欄＝上限なし。
    キー: {prefix}_num_ranges（範囲の数）, {prefix}_min_{i}, {prefix}_max_{i}
    """
    num_key = f"{prefix}_num_ranges"
    common.init_state(num_key, 1)
    lo, hi = limits
    ranges = []
    for i in range(st.session_state[num_key]):
        rc1, rc2 = container.columns(2)
        common.init_state(f"{prefix}_min_{i}", default_min)
        common.init_state(f"{prefix}_max_{i}", default_max)
        min_v = rc1.number_input(f"範囲{i+1} 最小", lo, hi, key=f"{prefix}_min_{i}")
        if hi is None:
            # value=None：一度数値を入れた後でも空欄に戻せる欄にする（指定しないと、空欄にしたとき最小値の 0 が入る）
            max_v = rc2.number_input(f"範囲{i+1} 最大", lo, hi, value=None, key=f"{prefix}_max_{i}", placeholder="上限なし")
        else:
            max_v = rc2.number_input(f"範囲{i+1} 最大", lo, hi, key=f"{prefix}_max_{i}")
        if min_v is None:
            min_v = lo   # 最小を空欄にしたときは、入力できる一番小さい値から
        if max_v is not None and min_v > max_v:
            container.caption(f"⚠️ 範囲{i+1}は最小が最大より大きいため、何も当てはまりません。")
        ranges.append((min_v, max_v))

    def add_r(): st.session_state[num_key] += 1
    def sub_r(): st.session_state[num_key] -= 1
    bc1, bc2 = container.columns(2)
    bc1.button("＋ 範囲を追加", key=f"btn_add_{prefix}_r", type="tertiary", on_click=add_r)
    if st.session_state[num_key] > 1:
        bc2.button("－ 減らす", key=f"btn_sub_{prefix}_r", type="tertiary", on_click=sub_r)
    return ranges

def _ranges_from_state(prefix, default_min, default_max):
    """render_range_inputs の入力欄の値（描画していない回でも、覚えている値から読む）"""
    return [(st.session_state.get(f"{prefix}_min_{i}", default_min), st.session_state.get(f"{prefix}_max_{i}", default_max))
            for i in range(st.session_state.get(f"{prefix}_num_ranges", 1))]

def render_target_inputs(container, prefix):
    """
    目標値の条件（種類と範囲）の入力欄（サイドバーと各画面の条件設定で共通）。戻り値: conditions_coc.TargetFilter。
    キー: {prefix}_mode と、範囲の入力欄（render_range_inputs）のキー
    """
    common.init_state(f"{prefix}_mode", conditions.TARGET_BASE)
    mode = container.radio("▼ 目標値の条件", conditions.TARGET_OPTIONS, key=f"{prefix}_mode")
    if mode == conditions.TARGET_OVER_INIT:
        container.caption("初期値が分からない技能（辞書にない技能・回避など）と、初期値0の項目（能力値・幸運・SANなど）は含めません。")
        return conditions.TargetFilter(mode=mode, ranges=[])
    lo, hi = conditions.TARGET_DEFAULT_RANGE
    ranges = render_range_inputs(container, prefix, default_max=hi, limits=conditions.TARGET_LIMITS, default_min=lo)
    return conditions.TargetFilter(mode=mode, ranges=ranges)

def _target_from_state(prefix):
    """render_target_inputs の入力欄の値から作る目標値の条件"""
    mode = st.session_state.get(f"{prefix}_mode", conditions.TARGET_BASE)
    if mode == conditions.TARGET_OVER_INIT:
        return conditions.TargetFilter(mode=mode, ranges=[])
    return conditions.TargetFilter(mode=mode, ranges=_ranges_from_state(prefix, *conditions.TARGET_DEFAULT_RANGE))


_COND_RANGE_DEFAULT_MAX = 5   # 条件設定の「出目の範囲」の最大の初期値

def _draw_condition_ui(prefix, header_title, sorted_all_res, default_succ_def):
    default_states = {r: (r in default_succ_def) for r in sorted_all_res}
    
    common.render_filter_header(
        title=header_title,
        prefix=f"{prefix}_chk",
        item_list=sorted_all_res,
        default_states=default_states,
        show_reset=True
    )
    
    common.render_chunked_checkboxes(item_keys=sorted_all_res, prefix=f"{prefix}_chk", num_columns=4)
    st.divider()
    c_l1, c_rest1, c_unk1 = st.columns([0.15, 0.4, 0.45])
    c_l1.radio("結合:", ["AND", "OR"], key=f"{prefix}_l1", label_visibility="collapsed")
    use_init_ui = c_rest1.checkbox("**初期値以下の出目を出した**", key=f"{prefix}_use_init")
    if use_init_ui:
        c_unk1.radio(
            "▼ 辞書にない技能の扱い", 
            conditions.UNKNOWN_INIT_OPTIONS,
            key=f"{prefix}_unk_behav"
        )

    st.divider()
    c_l2, c_rest2 = st.columns([0.15, 0.85])
    c_l2.radio("結合:", ["AND", "OR"], key=f"{prefix}_l2", label_visibility="collapsed")
    use_ranges_ui = c_rest2.checkbox("**指定した範囲の出目を出した**", key=f"{prefix}_use_ranges")

    if use_ranges_ui:
        render_range_inputs(c_rest2, prefix, default_max=_COND_RANGE_DEFAULT_MAX)

    st.divider()
    c_l3, c_rest3 = st.columns([0.15, 0.85])
    c_l3.radio("結合:", ["AND", "OR"], key=f"{prefix}_l3", label_visibility="collapsed")
    if c_rest3.checkbox("**目標値が指定した範囲に入っている**", key=f"{prefix}_use_target"):
        render_target_inputs(c_rest3, f"{prefix}_tgt")


# ==========================================
# 1-3. 条件設定UI：入力結果の回収と、条件の説明文の作成
# ==========================================
def _build_condition_config(prefix, sorted_all_res):
    sel_target_res = [r for r in sorted_all_res if st.session_state.get(f"{prefix}_chk_{r}", False)]
    logic1 = st.session_state.get(f"{prefix}_l1", "AND")
    use_init = st.session_state.get(f"{prefix}_use_init", False)
    unk_behav = st.session_state.get(f"{prefix}_unk_behav", conditions.UNK_USE_TARGET)
    logic2 = st.session_state.get(f"{prefix}_l2", "AND")
    use_ranges = st.session_state.get(f"{prefix}_use_ranges", False)
    active_ranges = _ranges_from_state(prefix, 1, _COND_RANGE_DEFAULT_MAX) if use_ranges else []
    logic3 = st.session_state.get(f"{prefix}_l3", "AND")
    target = _target_from_state(f"{prefix}_tgt") if st.session_state.get(f"{prefix}_use_target", False) else None

    # 条件の説明文。None は「全結果（条件なし）」を表す
    if not sel_target_res:
        cond_text = "【 該当する結果なし 】"
    elif len(sel_target_res) == len(sorted_all_res):
        cond_text = None
    else:
        cond_text = f"【 {', '.join(sel_target_res)} 】"

    def _combine(left, logic, right):
        # 「全結果 AND 〇〇」は〇〇だけ、「全結果 OR 〇〇」は全結果のまま
        if left is None:
            return right if logic == "AND" else None
        return f"{left} {logic} {right}"

    if use_init:
        cond_text = _combine(cond_text, logic1, "【 初期値以下 】")
    if use_ranges and active_ranges:
        range_strs = [conditions.describe_range(min_v, max_v) for min_v, max_v in active_ranges]
        cond_text = _combine(cond_text, logic2, f"【 出目({ ' OR '.join(range_strs) }) 】")
    if target is not None:
        cond_text = _combine(cond_text, logic3, f"【 {conditions.describe_target(target)} 】")
    final_cond_text = cond_text if cond_text is not None else "全結果対象"

    config = conditions.ConditionConfig(
        sel_target_res=sel_target_res, logic1=logic1, use_init=use_init, unk_behav=unk_behav,
        logic2=logic2, use_ranges=use_ranges, active_ranges=active_ranges,
        logic3=logic3, target=target,
    )
    return config, final_cond_text


# ==========================================
# 1. 🌟 条件設定UIの入口（成長チェック・確率集計・生ログで使用）
# ==========================================
def render_complex_condition_ui(
        prefix, 
        all_possible_res, 
        default_succ_def, 
        header_title="▼ 以下の結果を含める", 
        expander_title="", 
        recalc_rule=rules.DEFAULT_RULE.label):
    """戻り値: (conditions_coc.ConditionConfig, 条件の説明文)"""
    sorted_all_res = results.get_sorted_result(all_possible_res, recalc_rule, include_unfound_base=True)
    _init_condition_state(prefix, sorted_all_res, default_succ_def)

    with st.expander(expander_title, expanded=False):
        _draw_condition_ui(prefix, header_title, sorted_all_res, default_succ_def)

    return _build_condition_config(prefix, sorted_all_res)


# ==========================================
# 2-1. ダイスコマンドの絞り込み
# ==========================================
# コマンド → 並び順（COMMAND_SORT_ORDER に無いコマンドは後ろ）
_CMD_RANK = {c: i for i, c in enumerate(data.COMMAND_SORT_ORDER)}

# この2つは、項目が1つも無いときは None（＝絞り込まない）を返す
def _render_command_filter(full_df, prefix, num_cols):
    sel_cmds = None
    if 'コマンド' not in full_df.columns:
        return sel_cmds

    available_ids = sorted(
        full_df['コマンド'].dropna().unique().tolist(),
        key=lambda x: (_CMD_RANK.get(x, 999), x)
    )
    if not available_ids:
        return sel_cmds

    cmd_default_states = {cmd: cmd != 'CANCEL' for cmd in available_ids}
    cmd_labels = [data.CMD_NAME_MAP.get(cmd, cmd) for cmd in available_ids]

    common.render_filter_header(
        title="▼ ダイスコマンド",
        prefix=f"{prefix}_cmd",
        item_list=available_ids,
        default_states=cmd_default_states,
    )
    # 選択肢は読み込むログで変わる（外した項目は、選択肢から消えている間も外したまま残す）
    common.render_option_checkboxes(available_ids, prefix=f"{prefix}_cmd", defaults=cmd_default_states,
                                    item_labels=cmd_labels, num_columns=num_cols)

    return [cmd for cmd in available_ids if st.session_state.get(f"{prefix}_cmd_{cmd}")]

# ==========================================
# 2-2. 難易度の絞り込み
# ==========================================
def _render_diff_filter(full_df, prefix, num_cols):
    sel_diffs = None
    if '難易度' not in full_df.columns:
        return sel_diffs

    diff_keys = [d for d in data.DIFF_MAP if d in full_df['難易度'].values]
    if not diff_keys:
        return sel_diffs
    
    diff_labels = [data.DIFF_MAP.get(d, d) for d in diff_keys]
    common.render_filter_header(
        title="▼ 難易度指定ロール",
        prefix=f"{prefix}_diff",
        item_list=diff_keys,
    )
    common.render_option_checkboxes(diff_keys, prefix=f"{prefix}_diff", defaults=True,
                                    item_labels=diff_labels, num_columns=num_cols)

    return [d for d in diff_keys if st.session_state.get(f"{prefix}_diff_{d}")]

# ==========================================
# 2-3. B/Pダイス・複数ロールの除外
# ==========================================
def _render_bp_exclusion_ui(
        prefix,
        default_b=False, default_p=False,
        in_sidebar=False
    ):
    """B/Pダイス・複数ロールの除外トグル（3つ）を描画し、結果を返す共通UI"""
    st.markdown("**▼ B/Pダイス・複数ロールの除外**")
    if in_sidebar:
        c1, c2, c3 = st, st, st   # サイドバーは幅が狭いので縦に並べる
    else:
        c1, c2, c3 = st.columns(3)

    common.init_state(f"{prefix}_ex_b", default_b)
    common.init_state(f"{prefix}_ex_p", default_p)
    exclude_b = c1.toggle("ボーナスダイスを使用したロールを除外", key=f"{prefix}_ex_b")
    exclude_p = c2.toggle("ペナルティダイスを使用したロールを除外", key=f"{prefix}_ex_p")
    exclude_multi = c3.toggle("複数回ロール (x5など) を除外", key=f"{prefix}_ex_multi")
    return exclude_b, exclude_p, exclude_multi

# ==========================================
# 2. 🌟 コマンド・難易度・B/P除外UIの入口（サイドバー・生ログで使用）
# ==========================================
def render_adv_filters(
        full_df,
        prefix,
        default_b=False, default_p=False,
        expander_title="🎯 ダイスコマンド",
        in_sidebar=False
    ):
    """
    コマンド・難易度・BP除外の3つを束ねて描画する統括関数（in_sidebar=True ならサイドバーに縦1列で描画）。
    戻り値: conditions_coc.CommandFilter
    """
    num_cols = 1 if in_sidebar else 4
    container = st.sidebar if in_sidebar else st

    with container.expander(expander_title, expanded=False):
        sel_cmds = _render_command_filter(full_df, prefix, num_cols)
        st.divider()
        sel_diffs = _render_diff_filter(full_df, prefix, num_cols)
        st.divider()
        exclude_b, exclude_p, exclude_multi = \
            _render_bp_exclusion_ui(prefix, default_b=default_b, default_p=default_p, in_sidebar=in_sidebar)

    return conditions.CommandFilter(
        sel_cmds=sel_cmds, sel_diffs=sel_diffs,
        exclude_b=exclude_b, exclude_p=exclude_p, exclude_multi=exclude_multi,
    )


# ==========================================
# 3. 絞り込み条件の説明文（サイドバーの要約・確率集計の条件表示で使用）
# ==========================================
def short_list(items, limit=3):
    items = [str(i) for i in items]
    return "・".join(items) if len(items) <= limit else f"{'・'.join(items[:limit])} ほか{len(items) - limit}"

def only_or_except(label, all_items, selected, default_off=()):
    """全部選んでいれば None。少ない方を「○○のみ」「○○を除く」で表す（初期状態で外れている項目だけが外れていれば None）"""
    excluded = [i for i in all_items if i not in selected]
    if not excluded or set(excluded) == set(default_off):
        return None
    if not selected:
        return f"{label}：なし"
    if len(selected) <= len(excluded):
        return f"{label}：{short_list(selected)} のみ"
    return f"{label}：{short_list(excluded)} を除く"

def describe_command_filter(full_df, cmd):
    """ダイスコマンドの条件のうち、初期状態から変えているものを短い文のリストにする（cmd: conditions_coc.CommandFilter）"""
    if cmd is None:
        return []
    notes = []
    if cmd.sel_cmds is not None:
        all_cmds = full_df['コマンド'].dropna().unique().tolist()
        cancel = data.CMD_NAME_MAP.get('CANCEL', 'CANCEL')
        notes.append(only_or_except("コマンド", [data.CMD_NAME_MAP.get(c, c) for c in all_cmds],
                                    [data.CMD_NAME_MAP.get(c, c) for c in cmd.sel_cmds], default_off=(cancel,)))
        # 取り消し・編集済は初期状態では外れているので、含めたときはそれだけで説明を出す
        if 'CANCEL' in cmd.sel_cmds:
            notes.append(f"{cancel}も含める")
    if cmd.sel_diffs is not None:
        all_diffs = full_df['難易度'].dropna().unique().tolist()
        notes.append(only_or_except("難易度", [data.DIFF_MAP.get(d, d) for d in all_diffs],
                                    [data.DIFF_MAP.get(d, d) for d in cmd.sel_diffs]))
    # B/P・複数回ロールの除外は、初期状態（OFF）から変えて ON にしたものだけ
    toggles = ((cmd.exclude_b, "ボーナスダイス除外"),
               (cmd.exclude_p, "ペナルティダイス除外"),
               (cmd.exclude_multi, "複数回ロール除外"))
    notes += [text for value, text in toggles if value]
    return [n for n in notes if n]

