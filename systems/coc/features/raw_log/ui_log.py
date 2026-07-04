import streamlit as st
import uuid
from ...core import utils_coc as utils
from ...components import filters_coc
from ...components.styles_coc import Templates
from . import logic_log
from . import html_log

TARGET_GROUP = ["全体から", "チャット本文のみ", "キャラクター名のみ", "タブのみ", "結果のみ", "ファイル名のみ"]
LOG_GROUP_OPTIONS = ["キャラクター名", "タブ", "結果", "技能", "統合前のキャラクター名", "ファイル名"]
LOG_PAGE_SIZE = 1000
# ==========================================
# 1. キーワード検索機能
# ==========================================
def _on_del_search(idx):
    if len(st.session_state.log_search_terms) == 1:
        st.session_state.log_search_terms = [{
            "id": str(uuid.uuid4()), 
            "word": "", 
            "logic": "AND", 
            "target": "全体から"
        }]
    else:
        st.session_state.log_search_terms.pop(idx)

def _on_add_search():
    st.session_state.log_search_terms.append({
        "id": str(uuid.uuid4()), 
        "word": "", 
        "logic": "AND", 
        "target": "全体から"
    })

def _render_search_ui():
    """検索条件の入力UIを描画する"""
    with st.expander("🔍 キーワード検索", expanded=False):
        if "log_search_terms" not in st.session_state: 
            st.session_state.log_search_terms = [{
                "id": str(uuid.uuid4()), 
                "word": "", 
                "logic": "AND", 
                "target": "全体から"
            }]
        
        search_targets = TARGET_GROUP
        for i, term in enumerate(st.session_state.log_search_terms):
            c1, c2, c3, c4 = st.columns([0.1, 0.25, 0.55, 0.1])
            with c1:
                if i > 0: 
                    term["logic"] = st.selectbox(
                        f"logic_{term['id']}", 
                        ["AND", "OR"], 
                        index=["AND", "OR"].index(term["logic"]), 
                        key=f"srch_logic_{term['id']}", 
                        label_visibility="collapsed"
                    )
                else: 
                    st.markdown(
                        "<div style='text-align: center; color: #94a3b8; margin-top: 8px;'>AND / OR</div>",
                        unsafe_allow_html=True
                    )
            with c2:
                term["target"] = st.selectbox(
                    f"tgt_{term['id']}", 
                    search_targets, 
                    index=search_targets.index(term.get("target", "全体から")), 
                    key=f"srch_tgt_{term['id']}", 
                    label_visibility="collapsed"
                )
            with c3:
                term["word"] = st.text_input(
                    f"word_{term['id']}", 
                    value=term["word"], 
                    placeholder="検索ワード...", 
                    key=f"srch_word_{term['id']}", 
                    label_visibility="collapsed"
                )
            with c4:
                st.button(
                    "✖", 
                    key=f"srch_del_{term['id']}", 
                    on_click=_on_del_search, 
                    args=(i,)
                )
        st.button(
            "＋ 検索条件を追加", 
            type="tertiary", 
            key="add_search_term", 
            on_click=_on_add_search
        )

# ==========================================
# 2. 結果・出目フィルター機能
# ==========================================
def _render_filter(df, recalc_rule):
    filter_config = {}
    
    unique_res_tuple = tuple(df['結果'].unique())
    all_possible_res = utils.get_sorted_result(list(unique_res_tuple), recalc_rule, True)
    default_succ_def = [r for r in all_possible_res] 

    res_cfg, _ = filters_coc.render_complex_condition_ui(
        "log_res", 
        all_possible_res, 
        default_succ_def, 
        expander_title="🎯 結果・出目で絞り込む", 
        recalc_rule=recalc_rule
    )
    filter_config.update(res_cfg)

    adv_cfg = filters_coc.render_adv_filters(
        df, 
        "log_adv",
        expander_title="🎯 ダイスコマンドで絞り込む"
    )
    filter_config.update(adv_cfg)
    return filter_config


# ==========================================
# 3. 並べ替え・グループ化機能
# ==========================================
def _update_group_keys():
    """重複を排除してグループ階層リストを整える"""
    new_keys, seen_cols = [], set()
    for gk in st.session_state.log_group_keys:
        if gk["col"] not in seen_cols: 
            new_keys.append(gk)
            seen_cols.add(gk["col"])
    st.session_state.log_group_keys = new_keys

def _on_col_change(idx, wid_key):
    st.session_state.log_group_keys[idx]["col"] = st.session_state[wid_key]
    _update_group_keys()

def _on_del_group(idx):
    st.session_state.log_group_keys.pop(idx)
    _update_group_keys()

def _on_add_group():
    used = [k["col"] for k in st.session_state.log_group_keys]
    st.session_state.log_group_keys.append({
        "id": str(uuid.uuid4()), 
        "col": next(opt for opt in LOG_GROUP_OPTIONS if opt not in used),
        "asc": True
    })

def _render_grouping_ui():
    """グループ化の階層と最終的な並び順の設定UIを描画する"""
    with st.expander("🔄 並べ替えとグループ化", expanded=False):
        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>▼ グループ化（階層）</div>", unsafe_allow_html=True)
        if "log_group_keys" not in st.session_state: 
            st.session_state.log_group_keys = [{
                "id": str(uuid.uuid4()), 
                "col": "キャラクター名", 
                "asc": True
            }]
        
        for i, gk in enumerate(st.session_state.log_group_keys):
            if "id" not in gk: gk["id"] = str(uuid.uuid4())
            c1, c2, c3 = st.columns([0.5, 0.3, 0.2])
            available_opts = [
                opt for opt in LOG_GROUP_OPTIONS if opt not in [
                    k["col"] for k in st.session_state.log_group_keys] or opt == gk["col"]
            ]
            with c1:
                st.selectbox(
                    f"g_col_{gk['id']}", 
                    available_opts, 
                    index=available_opts.index(gk["col"]) if gk["col"] in available_opts else 0, 
                    key=f"sel_col_{gk['id']}", 
                    label_visibility="collapsed",
                    on_change=_on_col_change,
                    args=(i, f"sel_col_{gk['id']}")
                )
            with c2:
                gk["asc"] = st.radio(
                    f"g_asc_{gk['id']}", 
                    ["昇順", "降順"], 
                    horizontal=True, index=0 if gk["asc"] else 1, 
                    key=f"rad_asc_{gk['id']}", 
                    label_visibility="collapsed"
                ) == "昇順"
            with c3:
                st.button(
                    "✖", 
                    key=f"g_del_{gk['id']}", 
                    on_click=_on_del_group, 
                    args=(i,)
                )
                
        if len(st.session_state.log_group_keys) < len(LOG_GROUP_OPTIONS):
            st.button(
                "＋ グループ階層を追加", 
                type="tertiary", 
                key="add_group_key", 
                on_click=_on_add_group
            )
        
        st.markdown(f"<div style='{Templates.FILTER_HEADER}'>▼ ログ本文の並び順</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([0.35, 0.35, 0.3])
        with c1:
            max_heading_depth = st.selectbox(
                "見出しの表示階層 (0で非表示):", 
                options=[0, 1, 2, 3, 4, 5, 6], 
                index=3, 
                key="max_heading_depth_sel"
            )
        with c2:
            final_sort = st.selectbox(
                "一番下の並び順:", 
                ["時系列 (ログの通り)", "出目順"], 
                key="final_sort_sel"
            )
        with c3:
            final_asc = st.radio(
                "順序:", 
                ["昇順", "降順"], 
                horizontal=True, 
                key="final_asc_rad"
            ) == "昇順"
        
    return max_heading_depth, final_sort, final_asc


# ==========================================
# 4. 独立UI空間（フラグメント）
# ==========================================
@st.fragment
def _render_settings_fragment(df, recalc_rule, base_hash_str):
    """ユーザー操作による再描画をこの中だけに封じ込め、アプリ全体を高速に保つ"""
    _render_search_ui()
    filter_config = _render_filter(df, recalc_rule)
    max_heading_depth, final_sort, final_asc = _render_grouping_ui()
    
    current_state_str = (
        f"{base_hash_str}_"
        f"{st.session_state.get('log_search_terms', [])}_"
        f"{st.session_state.get('log_group_keys', [])}_"
        f"{max_heading_depth}_"
        f"{final_sort}_"
        f"{final_asc}_"
        f"{str(filter_config)}"
    )
    st.divider()
    
    st.session_state._tmp_log_config = {
        "filter_config": filter_config,
        "max_heading_depth": max_heading_depth,
        "final_sort": final_sort,
        "final_asc": final_asc,
        "current_state_str": current_state_str
    }

    c1, c2 = st.columns([0.75, 0.25])
    state_changed = st.session_state.get("raw_log_last_state") != current_state_str
    with c1:
        if state_changed and "raw_log_html_cache" in st.session_state:
            st.warning("⚠️ 条件が変更されました。右の「適用して表示」を押して反映してください。")
        else:
            st.info("💡 ログの表示には時間がかかります。条件を設定してから右のボタンを押してください。")
    with c2:
        if c2.button("🚀 適用して表示", type="primary", use_container_width=True):
            st.session_state.log_force_render = True
            st.session_state.log_current_config = st.session_state._tmp_log_config
            st.session_state.raw_log_last_state = st.session_state._tmp_log_config["current_state_str"]
            st.rerun()


# ==========================================
# 5. データ加工・HTML生成ロジック
# ==========================================
def _build_and_paginate_log(df, config, recalc_rule):
    """設定に基づいてデータを絞り込み、並び替え、分割し、HTMLを生成する"""
    filter_config = config.get("filter_config", {})
    search_terms = st.session_state.get("log_search_terms", [])
    group_keys = st.session_state.get("log_group_keys", [])
    use_char_code_sort = st.session_state.get('use_char_code_sort', False)
    
    display_df = df.copy()
    display_df['No'] = range(len(display_df))

    if 'clean_skill_name' in display_df.columns:
        display_df['_技能'] = display_df['clean_skill_name']
    else:
        display_df['_技能'] = display_df['判定名'].apply(utils.clean_skill_name)

    # 1. 検索と絞り込み
    filtered_df = logic_log.apply_search_filters(display_df, search_terms)
    if not filtered_df.empty:
        complex_mask = utils.get_ui_condition_mask(filtered_df, filter_config)
        filtered_df = filtered_df[complex_mask]

    if filtered_df.empty:
        return "<div class='chat-container'><div style='padding:20px; color:#64748b;'>条件に一致するログが見つかりません。</div></div>"

    # 2. 並び替え
    sorted_df = logic_log.process_and_sort_log(
        filtered_df, 
        group_keys, 
        config.get("final_sort"), 
        config.get("final_asc"), 
        recalc_rule, 
        use_char_code_sort
    )

    # 3. ページネーション（分割）
    total_logs = len(sorted_df)
    total_pages = (total_logs - 1) // LOG_PAGE_SIZE + 1
    
    if total_pages > 1:
        st.markdown(f"**全 {total_logs} 件**（{total_pages}ページに分割して表示しています）")
        current_page = st.number_input(
            "ページ番号:", 
            min_value=1, 
            max_value=total_pages, 
            value=1, 
            step=1, 
            key=f"log_page_{config.get('current_state_str')}"
        )
        start_idx = (current_page - 1) * LOG_PAGE_SIZE
        end_idx = start_idx + LOG_PAGE_SIZE
        paged_df = sorted_df.iloc[start_idx:end_idx]
    else:
        st.markdown(f"**全 {total_logs} 件**")
        paged_df = sorted_df

    # 4. HTMLの構築
    return html_log.build_log_html(paged_df, group_keys, config.get("max_heading_depth", 3))


# ==========================================
# 6. 🌟 メイン関数
# ==========================================
def render_raw_log(df, recalc_rule="7版"):
    """生ログ画面全体の描画を統括する"""
    if df.empty:
        st.info("表示できるデータがありません。")
        return

    st.markdown(html_log.LOG_CSS, unsafe_allow_html=True)
    unique_res_tuple = tuple(df['結果'].unique())
    file_names = tuple(df['ファイル名'].unique()) if 'ファイル名' in df.columns else ()
    df_hash = hash((file_names, unique_res_tuple))
    base_hash_str = f"{df_hash}_{recalc_rule}"
    
    # 1. UIの描画
    _render_settings_fragment(df, recalc_rule, base_hash_str)

    # 2. 実行フラグの判定
    force_render = st.session_state.pop("log_force_render", False)
    
    if "raw_log_html_cache" not in st.session_state:
        force_render = True
        st.session_state.log_current_config = st.session_state.get("_tmp_log_config", {})

    # 3. ロジックの実行とHTML生成
    if force_render:
        config = st.session_state.get("log_current_config", {})
        html_content = _build_and_paginate_log(df, config, recalc_rule)
        st.session_state.raw_log_html_cache = html_content
        st.session_state.raw_log_last_state = config.get("current_state_str")

    # 4. 描画
    if "raw_log_html_cache" in st.session_state:
        st.markdown(st.session_state.raw_log_html_cache, unsafe_allow_html=True)