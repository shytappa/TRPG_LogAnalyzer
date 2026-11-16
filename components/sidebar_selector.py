import streamlit as st
import pandas as pd
from . import common_ui as common
from .sidebar_merge import char_key
from core import logic_base

# 閉じた欄・非表示の個別設定の中にあって描画しないことがあるので、毎回値を書き戻すチェックボックスのキーの先頭部分
# （一括操作の gtab_ / gchar_ / gmerge_、ファイルごとの tab_ / char_。書き戻しは各システムの司令塔でまとめて行う）
KEEP_PREFIXES = ("gtab_", "gchar_", "gmerge_", "tab_", "char_")

# ==========================================
# 1. 全ファイル共通の一括操作
# ==========================================
def _set_per_file_keys(prefix, item, is_active):
    """各ファイルの個別チェックボックス（{prefix}_{ファイル名}_{項目}）を一斉に切り替える。
    末尾一致で探すと「x_雑談」のような別の項目まで巻き込むため、ファイル名から正確なキーを組み立てる"""
    for fname in st.session_state.get("_sidebar_fnames", []):
        key = f"{prefix}_{fname}_{item}"
        if key in st.session_state: st.session_state[key] = is_active

def _per_file_sync(global_prefix, file_prefix):
    """一括操作のチェックボックス（{global_prefix}_{項目}）を、各ファイルの個別チェックボックスに反映するコールバックを作る"""
    def sync(item):
        _set_per_file_keys(file_prefix, str(item).strip(), st.session_state[common.checkbox_key(global_prefix, item)])
    return sync

def _all_sync(global_prefix, sync_single):
    """一括操作の「全選択・全解除」のコールバックを作る（各項目を ON/OFF してから sync_single で反映する）"""
    def sync_all(is_active, items):
        for item in items:
            st.session_state[common.checkbox_key(global_prefix, item)] = is_active
            sync_single(item)
    return sync_all

def _sync_single_merge(m_name):
    safe_m = str(m_name).strip()
    is_active = st.session_state[common.checkbox_key("gmerge", m_name)]
    targets = []
    for m in st.session_state.get('char_merges', []):
        if str(m['name']).strip() == safe_m:
            targets = m['targets']
            break
    # 統合に含まれる「そのファイルのそのキャラ」だけを切り替える
    # （全ファイル共通の gchar_ を変えると、統合していない別ファイルの同名キャラまで消えてしまうため）
    for tgt in targets:
        if logic_base.KEY_SEP in tgt:
            st.session_state[char_key(tgt)] = is_active

_sync_single_tab = _per_file_sync("gtab", "tab")
_sync_single_char = _per_file_sync("gchar", "char")
_sync_all_tabs = _all_sync("gtab", _sync_single_tab)
_sync_all_chars = _all_sync("gchar", _sync_single_char)
_sync_all_merges = _all_sync("gmerge", _sync_single_merge)

def _render_global_sync_ui(expander_title, header_title, item_list, prefix, sync_single_func, sync_all_func, default_func=None):
    if not item_list: return
    for item in item_list:
        def_val = default_func(item) if default_func else True
        common.init_state(common.checkbox_key(prefix, item), def_val)
    # 閉じている間はチェックボックスを描画しない（キャラは数百人になり重いため）。描画しない間も値は残す（KEEP_PREFIXES）
    # on_change="rerun": 開いたときに中身を描画し直す
    expander = st.expander(expander_title, expanded=False, key=f"nokeep_exp_{prefix}", on_change="rerun")
    if not expander.open:
        return
    with expander:
        st.caption("※ここを操作すると、下の対応する項目が一斉に変更されます。")

        cols = st.columns([0.7, 0.15, 0.15])
        cols[0].markdown(f"**▼ {header_title}**")
        cols[1].button("全選択", key=f"btn_all_{prefix}", type="tertiary", on_click=sync_all_func, args=(True, item_list))
        cols[2].button("全解除", key=f"btn_none_{prefix}", type="tertiary", on_click=sync_all_func, args=(False, item_list))

        common.render_chunked_checkboxes(
            item_list, prefix=prefix, num_columns=1,
            on_change=sync_single_func, args_func=lambda k: (k,)
        )

# ==========================================
# 2. ファイルごとのタブ・キャラ選択
# ==========================================
_DEFAULT_TABS = ("[メイン]", "[情報]", "[雑談]")   # ccfolia の既定のタブ（この順で先頭に並べる）
_TAB_PRIORITY = {t: i for i, t in enumerate(_DEFAULT_TABS, 1)}

def _get_sorted_tabs(tab_list, force_defaults=False):
    """タブ名（前後の空白を除く）を、既定のタブ → それ以外の名前順に並べる"""
    base_tabs = set(str(x).strip() for x in tab_list if pd.notna(x))
    if force_defaults: base_tabs.update(_DEFAULT_TABS)
    return sorted(base_tabs, key=lambda x: (_TAB_PRIORITY.get(x, len(_DEFAULT_TABS) + 1), x))

def _file_item_state(prefix, fname, item, global_prefix, default):
    """ファイルごとの個別設定があればそれを、無ければ全ファイル共通の一括設定を、それも無ければ既定値を返す"""
    key = f"{prefix}_{fname}_{item}"
    if key in st.session_state:
        return st.session_state[key]
    global_val = st.session_state.get(f"{global_prefix}_{item}")
    return global_val if global_val is not None else default

def _render_single_file_options(fname, tabs, chars, sel_file_tabs, sel_chars, default_tab_func=None, show_ui=True):
    """1ファイル分のタブ・キャラ選択。show_ui=False のときはチェックボックスを描画せず、選択状態だけを集める"""
    tab_default = lambda t: default_tab_func(t) if default_tab_func else True
    if show_ui:
        with st.expander("↳ 表示タブ", expanded=False):
            for t in tabs:
                common.init_state(f"tab_{fname}_{t}", _file_item_state("tab", fname, t, "gtab", tab_default(t)))
            common.render_filter_header("▼ 表示タブ", f"tab_{fname}", tabs)
            common.render_chunked_checkboxes(tabs, prefix=f"tab_{fname}", num_columns=1)
        with st.expander("↳ キャラクター", expanded=False):
            for c in chars:
                common.init_state(f"char_{fname}_{c}", _file_item_state("char", fname, c, "gchar", True))
            common.render_filter_header("▼ キャラクター", f"char_{fname}", chars)
            common.render_chunked_checkboxes(chars, prefix=f"char_{fname}", num_columns=1)

    sel_file_tabs.extend([logic_base.make_key(fname, t) for t in tabs if _file_item_state("tab", fname, t, "gtab", tab_default(t))])
    sel_chars.extend([logic_base.make_key(fname, c) for c in chars if _file_item_state("char", fname, c, "gchar", True)])


# ==========================================
# 3. 表示データの絞り込み（ファイル・タブ・キャラ）の入口
# ==========================================
def render_file_char_selector(full_df, default_tab_func=None, default_off_files=()):
    """
    サイドバーの「表示するファイル・タブ・キャラ」。戻り値: logic_base.SelectorParams。
    default_off_files: 最初はチェックを外しておくファイル（同じロールが別のファイルにも入っているものなど。付け直せば表示する）
    """
    common.apply_pending_widget_values()   # キャラ統合の変更などで頼まれた、チェックボックスの書き換え
    st.sidebar.markdown("### 🗂 表示データの絞り込み")
    sel_files, sel_file_tabs, sel_chars = [], [], []
    st.session_state["_sidebar_fnames"] = list(full_df['ファイル名'].unique())  # 一括操作のコールバック用

    with st.sidebar.expander("📄 表示ファイル・タブ・キャラ", expanded=True):
        # --- 1. 一括操作群 ---
        all_tabs = _get_sorted_tabs(full_df['タブ'].unique(), force_defaults=True)
        _render_global_sync_ui(
            "📑 全ファイル共通 タブ一括操作", "タブ一括操作", all_tabs, "gtab",
            _sync_single_tab, _sync_all_tabs, default_tab_func
        )
        all_chars = sorted(set(str(x).strip() for x in full_df['キャラクター名'].dropna().unique()))
        _render_global_sync_ui(
            "👥 全ファイル共通 キャラ一括操作", "キャラ一括操作", all_chars, "gchar",
            _sync_single_char, _sync_all_chars
        )
        current_merges = st.session_state.get("char_merges", [])
        if current_merges:
            all_merges_names = [m['name'] for m in current_merges]
            _render_global_sync_ui(
                "🔗 統合キャラクター 一括操作", "統合キャラ一括", all_merges_names, "gmerge",
                _sync_single_merge, _sync_all_merges
            )
        st.divider()

        # --- 2. 個別ファイル群 ---
        # ファイルごとのタブ・キャラのチェックボックスは数百〜千個以上になり重いため、既定では表示しない
        # （非表示中は上の一括操作の設定に従う。個別に変えた設定は表示を切り替えても残す）
        show_detail = st.toggle("ファイルごとにタブ・キャラを個別設定する", key="per_file_detail")
        # 非表示の間も個別設定が破棄されないよう、値を書き戻している（KEEP_PREFIXES）

        by_file = full_df.groupby('ファイル名', sort=False)   # グループ分けは1回だけ行い、2つの列で使い回す
        file_tabs = by_file['タブ'].unique()
        file_chars = by_file['キャラクター名'].unique()
        for fname in full_df['ファイル名'].unique():
            f_key = f"file_en_{fname}"

            common.init_state(f_key, fname not in default_off_files)
            if st.checkbox(f"📁 {common.escape_md_brackets(fname)}", key=f_key):
                sel_files.append(fname)
                tabs = _get_sorted_tabs(file_tabs[fname])
                chars = sorted(set(str(x).strip() for x in file_chars[fname] if pd.notna(x)))
                _render_single_file_options(fname, tabs, chars, sel_file_tabs, sel_chars, default_tab_func, show_ui=show_detail)

        st.divider()
        st.toggle("同名キャラをファイルごとに区別する", key="separate_char_by_file")

    return logic_base.SelectorParams(
        sel_files=sel_files, sel_file_tabs=sel_file_tabs, sel_chars=sel_chars,
        separate_char_by_file=st.session_state.get("separate_char_by_file", False),
    )
