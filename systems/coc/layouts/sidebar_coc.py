import streamlit as st
from ..core import skills_coc as skills
from ..core import results_coc as results
from ..core import conditions_coc as conditions
from ..core import rules_coc as rules
from components import common_ui as common
from ..components import filters_coc as filters_coc

# ==========================================
# 1. 成功度フィルター
# ==========================================
def _render_success_filter(full_df, recalc_rule):
    with st.sidebar.expander("🎲 成功度フィルター", expanded=True):
        all_res_options = results.result_options(full_df, recalc_rule)
        common.render_filter_header("▼ 成功度", "res", all_res_options)
        # 選択肢はルールで変わる（外した項目は、ルールを行き来しても外したまま残す）
        common.render_option_checkboxes(all_res_options, prefix="res", defaults=True, num_columns=1)
        sel_success_levels = [r for r in all_res_options if st.session_state.get(common.checkbox_key("res", r))]
    return sel_success_levels

# ==========================================
# 2. 出目数値フィルター
# ==========================================
def _render_roll_value_filter():
    with st.sidebar.expander("🔢 出目・目標値フィルター", expanded=True):
        # 1. 初期値判定 
        req_init_succ = st.checkbox("初期値以下の出目のみを含める", key="chk_req_init")
        unk_behav_sb = conditions.UNK_USE_TARGET
        if req_init_succ:
            common.init_state("unk_behav_sb", conditions.UNK_USE_TARGET)
            unk_behav_sb = st.radio(
                "▼ 辞書にない技能の扱い",
                conditions.UNKNOWN_INIT_OPTIONS,
                key="unk_behav_sb"
            )

        st.divider()

        # 2. 出目の範囲
        use_ranges = st.checkbox("出目で絞り込む", key="chk_use_ranges")
        active_ranges = []
        if use_ranges:
            active_ranges = filters_coc.render_range_inputs(st, "sb_range", default_max=100)

        st.divider()

        # 3. 目標値の範囲（出目と同じく、最小・最大を複数指定できる）
        target = None
        if st.checkbox("目標値で絞り込む", key="chk_use_target"):
            target = filters_coc.render_target_inputs(st, "sb_target")
    return req_init_succ, unk_behav_sb, active_ranges, target

# ==========================================
# 3. 技能フィルター
# ==========================================
SKILL_ONLY    = "選んだ技能のみ"
SKILL_EXCLUDE = "選んだ技能を除く"

def _render_skill_filter(full_df, sel_chars, recalc_rule):
    with st.sidebar.expander("🎯 技能フィルター", expanded=False):
        available_skills = full_df.loc[full_df['_file_char'].isin(sel_chars), '_base_skill_name'].unique().tolist()
        
        if not st.session_state.get('use_char_code_sort', False):
            available_skills = sorted(available_skills, key=lambda x: (skills.get_skill_sort_rank(x, recalc_rule), x))
        else:
            available_skills = sorted(available_skills)
        
        if "memory_sel_skills" not in st.session_state:
            st.session_state.memory_sel_skills = []

        use_skill_filter = st.checkbox("技能で絞り込む", key="use_skill_filter")
        def format_skill_name(s):
            return "（技能名未入力）" if s == "---" else s
            
        if use_skill_filter:
            common.init_state("skill_filter_mode", SKILL_ONLY)
            mode = st.radio("技能の絞り込み方", [SKILL_ONLY, SKILL_EXCLUDE], key="skill_filter_mode",
                            horizontal=True, label_visibility="collapsed")
            def _update_memory(avail_skills):
                current_sel = st.session_state.sel_skills_multi
                hidden_memory = [s for s in st.session_state.memory_sel_skills if s not in avail_skills]
                st.session_state.memory_sel_skills = current_sel + hidden_memory
            valid_defaults = [s for s in available_skills if s in st.session_state.memory_sel_skills]
            st.session_state["sel_skills_multi"] = valid_defaults

            sel_skills_ui = st.multiselect(
                "技能を選択:",
                available_skills,
                format_func = format_skill_name,
                placeholder = "技能を選んでください...",
                key = "sel_skills_multi",
                label_visibility = "collapsed",
                on_change = _update_memory,
                args = (available_skills,)
            )
            if mode == SKILL_EXCLUDE:
                sel_skills = [s for s in available_skills if s not in sel_skills_ui]
            else:
                sel_skills = sel_skills_ui if sel_skills_ui else available_skills
        else:
            sel_skills = available_skills
    return sel_skills


# ==========================================
# 4. ダイスコマンドフィルター（コマンド・難易度・B/P除外）
# ==========================================
def _render_special_rules_filter(full_df):
    """戻り値: conditions_coc.CommandFilter"""
    return filters_coc.render_adv_filters(
        full_df,
        "sb",
        expander_title="🎯 ダイスコマンドフィルター",
        in_sidebar=True
    )

# ==========================================
# 5. 再計算ルール
# ==========================================
def _render_recalc_options(current_rule):
    with st.sidebar.expander("🎲 判定の再計算ルール", expanded=False):
        st.caption("ダイスログを各ルールに従い再計算します。")
        labels = rules.RULE_LABELS
        # 初期値はプロファイル（profile_coc.activate）が入れている。知らないルール名なら親から渡されたものに戻す
        if st.session_state.get("recalc_rule") not in labels:
            st.session_state["recalc_rule"] = current_rule if current_rule in labels else labels[0]
        common.init_state("recalc_rule", current_rule)   # ブラウザに値を確実に伝える（common.init_state の説明を参照）

        st.radio(
            "再計算ルール",   # 見出しは隠す（画面の読み上げではこの名前が読まれる）
            options=labels,
            key="recalc_rule",
            label_visibility="collapsed"
        )

# ==========================================
# 6. 解析・抽出オプション
# ==========================================
SPLIT_COMBINED_KEY = "split_combined"   # 組み合わせロールの結果を分割（app_coc が前処理に渡す）

def _render_extra_options():
    with st.sidebar.expander("⚙️ 解析・抽出オプション", expanded=False):
        # 統合の2つは自卓用プロファイルで初期値ONにしている（profile_coc.activate）
        st.toggle("技能名を文字コード順で並べる", key="use_char_code_sort")

        common.init_state(SPLIT_COMBINED_KEY, True)
        st.toggle("組み合わせロールの結果を分割", key=SPLIT_COMBINED_KEY,
                  help="ON：組み合わせロール（CBR）を目標値ごとに1回ずつ数えます（結果はそれぞれの目標値に対する結果）。"
                       "OFF：1回のロールとして数え、結果はログに出た全体の結果（成功・部分的成功・失敗）にします。"
                       "「部分的成功」は成功に数えます。出目の分布は、どちらでも1回として数えます。")

        st.toggle("B/Pダイスの内訳を抽出", key="extract_bp")
        if st.session_state.get("extract_bp", False):
            common.init_state("chk_int_bp", False)
            st.toggle("B/Pダイスの内訳を通常結果に統合", key="chk_int_bp")

        st.toggle("難易度指定ロールの失敗を救済", key="rescue_diff")
        if st.session_state.get("rescue_diff", False):
            common.init_state("chk_int_rescue", False)
            st.toggle("救済結果を通常結果に統合", key="chk_int_rescue")
    # 統合の2つは app_coc で、成功度フィルターより前に反映している（logic_coc.integrate_results）

# ==========================================
# 7. 🌟 メイン関数（司令塔）
# ==========================================
# 条件付きで出す欄（範囲の値、辞書にない技能の扱い、統合の2つ、目標値、技能の絞り込み方）は、隠している間も値を残す
# （書き戻しは app_coc._keep_hidden_settings でまとめて行う）
KEEP_PREFIXES = ("sb_range_", "sb_target_")
KEEP_KEYS = ("unk_behav_sb", "chk_int_bp", "chk_int_rescue", "skill_filter_mode")

def render_coc_filters(full_df, sel_chars, recalc_rule):
    """
    【司令塔】CoC固有のフィルター設定UI全体を描画し、設定を返す。
    戻り値は logic_coc.CocFilterParams の引数（selector と merges 以外）の辞書
    """
    # 1. 各パーツを描画し、結果を受け取る
    sel_success_levels = _render_success_filter(full_df, recalc_rule)
    req_init_succ, unk_behav, active_ranges, target = _render_roll_value_filter()
    sel_skills = _render_skill_filter(full_df, sel_chars, recalc_rule)
    command = _render_special_rules_filter(full_df)
    st.sidebar.divider()
    _render_recalc_options(recalc_rule)
    _render_extra_options()

    return dict(
        sel_skills=sel_skills,
        sel_success_levels=sel_success_levels,
        active_ranges=active_ranges,
        req_init_succ=req_init_succ,
        unk_behav=unk_behav,
        command=command,
        target=target,
    )


# ==========================================
# 8. 適用中の絞り込み条件の要約（ダッシュボードの上に表示）
# ==========================================
def describe_filters(full_df, params):
    """初期状態から変えている絞り込み条件を、短い文のリストにする（params: logic_coc.CocFilterParams）"""
    notes = []
    sel = params.selector
    n_files, n_chars = full_df['ファイル名'].nunique(), full_df['_file_char'].nunique()
    if len(sel.sel_files) < n_files or len(sel.sel_chars) < n_chars:
        notes.append(f"ファイル {len(sel.sel_files)}/{n_files}・キャラ {len(sel.sel_chars)}/{n_chars}")
    if len(sel.sel_file_tabs) < full_df['_file_tab'].nunique():
        notes.append("一部のタブのみ")

    all_res = results.result_options(full_df, st.session_state.get("recalc_rule"))
    notes.append(filters_coc.only_or_except("成功度", all_res, params.sel_success_levels))

    if st.session_state.get("use_skill_filter"):
        chosen = st.session_state.get("sel_skills_multi", [])
        if chosen:
            mode_text = "を除く" if st.session_state.get("skill_filter_mode") == SKILL_EXCLUDE else "のみ"
            notes.append(f"技能：{filters_coc.short_list(chosen)} {mode_text}")

    if params.req_init_succ:
        notes.append("初期値以下の出目のみ")
    if params.active_ranges:
        notes.append("出目 " + "・".join(f"{a}〜{b}" for a, b in params.active_ranges))
    if params.target is not None:
        notes.append(conditions.describe_target(params.target))

    notes += filters_coc.describe_command_filter(full_df, params.command)

    if params.merges.char_merges:
        notes.append(f"キャラ統合 {len(params.merges.char_merges)}件")
    return [n for n in notes if n]