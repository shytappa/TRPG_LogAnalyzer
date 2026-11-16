import streamlit as st
import pandas as pd
import uuid
import copy
from core import logic_base
from components import common_ui as common
from ...core import results_coc as results
from ...core import conditions_coc as conditions
from ...core import rules_coc as rules
from ...components import filters_coc
from . import logic_log
from . import html_log

TARGET_GROUP = list(logic_log.SEARCH_TARGET_COLUMNS)   # 検索対象の選択肢
LOG_GROUP_OPTIONS = ["キャラクター名", "タブ", "結果", "技能", "統合前のキャラクター名", "ファイル名"]
LOG_PAGE_SIZE = 1000                       # 1ページの件数の初期値
LOG_PAGE_SIZE_OPTIONS = [100, 300, 500, 1000]
# ==========================================
# 1. キーワード検索機能
# ==========================================
def _new_search_term():
    return {"id": str(uuid.uuid4()), "word": "", "logic": "AND", "target": logic_log.SEARCH_ALL}

def _forget_inputs(prefixes, item_id):
    """消した条件の入力欄の値を session_state から消す（残しておくと、条件を足し引きするたびに増え続ける）"""
    for prefix in prefixes:
        st.session_state.pop(f"{prefix}{item_id}", None)

def _on_del_search(idx):
    _forget_inputs(("srch_logic_", "srch_tgt_", "srch_word_"), st.session_state.log_search_terms[idx]["id"])
    if len(st.session_state.log_search_terms) == 1:
        st.session_state.log_search_terms = [_new_search_term()]
    else:
        st.session_state.log_search_terms.pop(idx)

def _on_add_search():
    st.session_state.log_search_terms.append(_new_search_term())

def _render_search_ui():
    """検索条件の入力UIを描画する"""
    with st.expander("🔍 キーワード検索", expanded=False):
        if "log_search_terms" not in st.session_state:
            st.session_state.log_search_terms = [_new_search_term()]
        st.caption("入力した文字をそのまま含むロールを探します（大文字・小文字は区別しません）。NOT はその文字を含まないロールです。")

        for i, term in enumerate(st.session_state.log_search_terms):
            # 1つ目の条件は「含む」か「含まない（NOT）」だけ選べる
            logic_options = ["AND", "OR", logic_log.LOGIC_NOT] if i > 0 else ["AND", logic_log.LOGIC_NOT]
            logic_key = f"srch_logic_{term['id']}"
            if st.session_state.get(logic_key, term["logic"]) not in logic_options:   # 上の条件を消して1つ目になったとき
                st.session_state[logic_key] = term["logic"] = "AND"
            # 各入力欄の初期値は、検索条件リスト（log_search_terms）に保存されている値
            common.init_state(logic_key, term["logic"])
            common.init_state(f"srch_tgt_{term['id']}", term.get("target", logic_log.SEARCH_ALL))
            common.init_state(f"srch_word_{term['id']}", term["word"])
            c1, c2, c3, c4 = st.columns([0.12, 0.25, 0.53, 0.1])
            with c1:
                term["logic"] = st.selectbox(
                    "検索条件のつなぎ方",   # 見出しは隠す（画面の読み上げではこの名前が読まれる）
                    logic_options,
                    format_func=lambda x, first=(i == 0): "含む" if first and x == "AND" else x,
                    key=logic_key,
                    label_visibility="collapsed"
                )
            with c2:
                term["target"] = st.selectbox(
                    "検索する場所",
                    TARGET_GROUP,
                    key=f"srch_tgt_{term['id']}",
                    label_visibility="collapsed"
                )
            with c3:
                term["word"] = st.text_input(
                    "検索ワード",
                    placeholder="検索ワード...", 
                    key=f"srch_word_{term['id']}", 
                    label_visibility="collapsed"
                )
            with c4:
                st.button(
                    "✖", 
                    key=f"btn_srch_del_{term['id']}", 
                    on_click=_on_del_search, 
                    args=(i,)
                )
        st.button(
            "＋ 検索条件を追加",
            type="tertiary",
            key="btn_add_search_term",
            on_click=_on_add_search
        )

# ==========================================
# 2. 結果・出目フィルター機能
# ==========================================
def _render_filter(df, recalc_rule):
    """結果・出目とダイスコマンドの絞り込みUI。戻り値: conditions_coc.ConditionConfig"""
    all_res = results.result_options(df, recalc_rule)
    filter_config, _ = filters_coc.render_complex_condition_ui(
        "log_res",
        all_res,
        all_res,   # 初期状態では全結果を表示する
        expander_title="🎯 結果・出目で絞り込む",
        recalc_rule=recalc_rule
    )
    filter_config.command = filters_coc.render_adv_filters(
        df,
        "log_adv",
        expander_title="🎯 ダイスコマンドで絞り込む"
    )
    return filter_config


# ==========================================
# 3. 並べ替え・グループ化機能
# ==========================================
# 各階層の選択肢から、他の階層で使っている列は外しているので、同じ列が2回選ばれることはない
def _on_col_change(idx, wid_key):
    st.session_state.log_group_keys[idx]["col"] = st.session_state[wid_key]

def _on_del_group(idx):
    _forget_inputs(("sel_col_", "rad_asc_"), st.session_state.log_group_keys.pop(idx)["id"])

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
        st.markdown("**▼ グループ化（階層）**")
        if "log_group_keys" not in st.session_state: 
            st.session_state.log_group_keys = [{
                "id": str(uuid.uuid4()), 
                "col": "キャラクター名", 
                "asc": True
            }]
        
        used_cols = [k["col"] for k in st.session_state.log_group_keys]
        for i, gk in enumerate(st.session_state.log_group_keys):
            c1, c2, c3 = st.columns([0.5, 0.3, 0.2])
            available_opts = [opt for opt in LOG_GROUP_OPTIONS if opt not in used_cols or opt == gk["col"]]
            # 入力欄の初期値は、グループ階層リスト（log_group_keys）に保存されている値
            common.init_state(f"sel_col_{gk['id']}", gk["col"])
            common.init_state(f"rad_asc_{gk['id']}", "昇順" if gk["asc"] else "降順")
            with c1:
                st.selectbox(
                    "グループ化する列",   # 見出しは隠す（画面の読み上げではこの名前が読まれる）
                    available_opts,
                    key=f"sel_col_{gk['id']}",
                    label_visibility="collapsed",
                    on_change=_on_col_change,
                    args=(i, f"sel_col_{gk['id']}")
                )
            with c2:
                gk["asc"] = st.radio(
                    "グループの並び順",
                    ["昇順", "降順"], 
                    horizontal=True,
                    key=f"rad_asc_{gk['id']}",
                    label_visibility="collapsed"
                ) == "昇順"
            with c3:
                st.button(
                    "✖", 
                    key=f"btn_g_del_{gk['id']}", 
                    on_click=_on_del_group, 
                    args=(i,)
                )
                
        if len(st.session_state.log_group_keys) < len(LOG_GROUP_OPTIONS):
            st.button(
                "＋ グループ階層を追加", 
                type="tertiary", 
                key="btn_add_group_key", 
                on_click=_on_add_group
            )
        
        st.markdown("**▼ ログ本文の並び順**")
        c1, c2, c3 = st.columns([0.35, 0.35, 0.3])
        common.init_state("max_heading_depth_sel", 3)
        with c1:
            max_heading_depth = st.selectbox(
                "見出しの表示階層 (0で非表示):",
                options=[0, 1, 2, 3, 4, 5, 6],
                key="max_heading_depth_sel"
            )
        with c2:
            final_sort = st.selectbox(
                "一番下の並び順:", 
                logic_log.FINAL_SORT_OPTIONS,
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
@common.error_boundary("生ログ一覧の設定の表示中にエラーが発生しました")
def _render_settings_fragment(df, recalc_rule, base_hash_str):
    """ユーザー操作による再描画をこの中だけに封じ込め、アプリ全体を高速に保つ"""
    # この中だけを描き直す回は app_coc の書き戻しが動かないので、条件付きで出す欄（範囲の入力など）の値をここで書き戻す
    common.keep_widget_state(prefixes=_LOG_WIDGET_PREFIXES, keys=_LOG_WIDGET_KEYS)
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
        "search_terms": copy.deepcopy(st.session_state.get('log_search_terms', [])),
        "group_keys": copy.deepcopy(st.session_state.get('log_group_keys', [])),
        "filter_config": filter_config,
        "max_heading_depth": max_heading_depth,
        "final_sort": final_sort,
        "final_asc": final_asc,
        "current_state_str": current_state_str
    }

    c1, c2 = st.columns([0.75, 0.25])
    state_changed = st.session_state.get("raw_log_last_state") != current_state_str
    with c1:
        if state_changed and "raw_log_sorted" in st.session_state:
            st.warning("⚠️ 条件が変更されました。右の「適用して表示」を押して反映してください。")
        else:
            st.info("💡 ログの表示には時間がかかります。条件を設定してから右のボタンを押してください。")
    with c2:
        if st.button("🚀 適用して表示", type="primary", width="stretch"):
            st.session_state.log_force_render = True
            st.session_state.log_current_config = st.session_state._tmp_log_config
            st.session_state[_APPLIED_WIDGETS] = _log_widget_values()
            # 再実行のときにこの欄は並び替えより先に描画されるので、ここで「適用済み」にしておく（失敗したら render_raw_log で戻す）
            st.session_state.raw_log_last_state = current_state_str
            st.rerun()


# ==========================================
# 5. データ加工・HTML生成ロジック
# ==========================================
def _prepare_log(df, config, recalc_rule):
    """設定に基づいてデータを絞り込み・並び替える（「適用して表示」を押したときだけ実行）"""
    filter_config = config.get("filter_config") or conditions.ConditionConfig()
    search_terms = config.get("search_terms", [])
    group_keys = config.get("group_keys", [])
    use_char_code_sort = config.get("use_char_code_sort", False)

    # 元の表は書き換えない（列を足すだけなので、表全体は複製しない）。
    # ファイル名は、キャラ統合の前の元のファイル名にする（表示・検索・グループ化で、どのセッションのロールか分かるように）
    display_df = df.assign(No=range(len(df)), ファイル名=logic_base.file_names(df))

    # 1. 検索と絞り込み
    filtered_df = logic_log.apply_search_filters(display_df, search_terms)
    if not filtered_df.empty:
        complex_mask = conditions.get_ui_condition_mask(filtered_df, filter_config)
        filtered_df = filtered_df[complex_mask]

    if filtered_df.empty:
        return filtered_df

    # 2. 並び替え
    return logic_log.process_and_sort_log(
        filtered_df,
        group_keys,
        config.get("final_sort"),
        config.get("final_asc"),
        recalc_rule,
        use_char_code_sort
    )


@st.fragment
@common.error_boundary("生ログの表示中にエラーが発生しました")
def _render_log_page(sorted_df, config):
    """
    並び替え済みのログを1ページ分だけHTMLにして表示する。
    ページ送りでアプリ全体が再実行されないよう、この部分だけを独立して再描画する（fragment）
    """
    if sorted_df.empty:
        st.info("条件に一致するログが見つかりません。")
        return

    total_logs = len(sorted_df)
    state_str = config.get("current_state_str")
    common.init_state("log_page_size", LOG_PAGE_SIZE)
    page_size = st.session_state["log_page_size"]
    total_pages = (total_logs - 1) // page_size + 1

    # 条件を適用し直したら1ページ目に戻す
    if st.session_state.get("log_page_state") != state_str:
        st.session_state["log_page_state"] = state_str
        st.session_state["log_page"] = 1
    st.session_state["log_page"] = min(st.session_state.get("log_page", 1), total_pages)
    common.init_state("log_page", 1)

    def _move_page(step):
        st.session_state["log_page"] = min(max(st.session_state["log_page"] + step, 1), total_pages)

    c_count, c_prev, c_page, c_next, c_size = st.columns([0.34, 0.12, 0.2, 0.12, 0.22], vertical_alignment="bottom")
    pages_note = f"（{total_pages}ページ）" if total_pages > 1 else ""
    c_count.markdown(f"**全 {total_logs} 件**{pages_note}")
    if total_pages > 1:
        c_prev.button("◀ 前へ", key="btn_log_prev", width="stretch", on_click=_move_page, args=(-1,),
                      disabled=st.session_state["log_page"] <= 1)
        c_page.number_input("ページ番号:", min_value=1, max_value=total_pages, step=1, key="log_page")
        c_next.button("次へ ▶", key="btn_log_next", width="stretch", on_click=_move_page, args=(1,),
                      disabled=st.session_state["log_page"] >= total_pages)
    if total_logs > LOG_PAGE_SIZE_OPTIONS[0]:
        c_size.selectbox("1ページの件数:", LOG_PAGE_SIZE_OPTIONS, key="log_page_size")
    current_page = st.session_state["log_page"]

    # 同じ条件・同じページなら前回のHTMLを使い回す
    page_key = (state_str, current_page, page_size)
    cached = st.session_state.get("raw_log_page_cache")
    if not cached or cached[0] != page_key:
        start_idx = (current_page - 1) * page_size
        paged_df = sorted_df.iloc[start_idx:start_idx + page_size]
        html_str = html_log.build_log_html(paged_df, config.get("group_keys", []), config.get("max_heading_depth", 3))
        cached = (page_key, html_str)
        st.session_state.raw_log_page_cache = cached
    st.html(cached[1])   # 大きなHTMLはMarkdownとして解析させずにそのまま描画する（ブラウザ側の負荷軽減）


# ==========================================
# 6. 🌟 メイン関数
# ==========================================
# 生ログのタブの設定欄（検索・結果と出目・ダイスコマンド・並べ替え）の key
_LOG_WIDGET_PREFIXES = ("srch_", "sel_col_", "rad_asc_", "log_res", "log_adv")
_LOG_WIDGET_KEYS = ("log_search_terms", "log_group_keys", "max_heading_depth_sel", "final_sort_sel", "final_asc_rad")
# 最後に「適用して表示」したときの設定欄の値（「_」で始めないのは、「設定をリセット」で一緒に消すため）
_APPLIED_WIDGETS = "log_applied_widgets"

def _is_log_widget(k):
    return isinstance(k, str) and (k.startswith(_LOG_WIDGET_PREFIXES) or k in _LOG_WIDGET_KEYS)

def _log_widget_values():
    return {k: copy.deepcopy(v) for k, v in st.session_state.items() if _is_log_widget(k)}

def _restore_log_widgets(values):
    """設定欄を、最後に適用したときの値に戻す（適用していなかった変更は捨てる）"""
    for k in [k for k in st.session_state.keys() if _is_log_widget(k) and k not in values]:
        del st.session_state[k]
    for k, v in values.items():
        st.session_state[k] = copy.deepcopy(v)

def release_memory():
    """生ログのタブを開いていない間は、並び替え済みの表とページの表示を捨てる（戻ってきたら作り直す）"""
    for key in ("raw_log_sorted", "raw_log_page_cache"):
        st.session_state.pop(key, None)

def render_raw_log(df, recalc_rule=rules.DEFAULT_RULE.label):
    """生ログ画面全体の描画を統括する"""
    if df.empty:
        st.info("表示できるデータがありません。")
        return

    st.html(html_log.LOG_CSS)   # <style> だけの st.html は画面に場所を取らない
    # サイドバーの絞り込みなどで表示対象の行が変わったことを検知できるよう、中身からハッシュを作る
    # （行番号と短い列だけで十分区別できる。長い「生ログ」の本文まで計算すると遅いので含めない）
    hash_cols = [c for c in ['ファイル名', 'キャラクター名', '統合前のキャラクター名', 'タブ', '判定名', '結果', '出目', '初期値']
                 if c in df.columns]
    df_hash = int(pd.util.hash_pandas_object(df[hash_cols], index=True).sum())
    base_hash_str = f"{df_hash}_{recalc_rule}_{st.session_state.get('use_char_code_sort', False)}"

    # タブを移って戻ってきたとき（release_memory の後）は、適用していなかった条件の変更を捨てて、最後に適用した条件に戻す
    if "raw_log_sorted" not in st.session_state and _APPLIED_WIDGETS in st.session_state:
        _restore_log_widgets(st.session_state[_APPLIED_WIDGETS])

    # 1. UIの描画
    _render_settings_fragment(df, recalc_rule, base_hash_str)

    # 2. 実行フラグの判定
    force_render = st.session_state.pop("log_force_render", False)

    if "raw_log_sorted" not in st.session_state:
        # 初めて開いたときと、タブを移って戻ってきたときは、（上で戻した）今の設定で作り直す
        force_render = True
        st.session_state.log_current_config = st.session_state.get("_tmp_log_config", {})
        st.session_state[_APPLIED_WIDGETS] = _log_widget_values()

    # 3. 絞り込み・並び替え（ボタンを押したときだけ）
    if force_render:
        config = {**st.session_state.get("log_current_config", {}),
                  "use_char_code_sort": st.session_state.get('use_char_code_sort', False)}
        # 表を作り直したので、前の表から作ったページの表示は使わない（同じ条件で適用し直したときも）
        st.session_state.pop("raw_log_page_cache", None)
        try:
            st.session_state.raw_log_sorted = _prepare_log(df, config, recalc_rule)
            st.session_state.raw_log_last_state = config.get("current_state_str")
        except Exception as e:
            # 失敗したら前回の結果を出さず、「条件が変更されました」の表示に戻す
            st.session_state.pop("raw_log_sorted", None)
            st.session_state.raw_log_last_state = None
            # エラーの中身（ファイルの場所などを含むことがある）は、このPCから開いたときだけ出す
            common.show_error("ログの絞り込み・並び替えに失敗しました", e)
            return

    # 4. 表示中のページだけ描画
    if "raw_log_sorted" in st.session_state:
        _render_log_page(st.session_state.raw_log_sorted, st.session_state.get("log_current_config", {}))