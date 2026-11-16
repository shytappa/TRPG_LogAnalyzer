"""
CoC Log Analyzer - Main Application (司令塔)
"""

# ==========================================
# 1. ライブラリ・モジュールのインポート
# ==========================================
import streamlit as st
import pandas as pd

from core import logic_base, ccfolia_reader
from components import common_ui as common, sidebar_nav, sidebar_files, sidebar_selector, sidebar_merge

from . import profile_coc as profiles
from .core import parser_coc as parser
from .core import logic_coc
from .core.logic_coc import CocFilterParams
from .layouts import sidebar_coc
from .layouts import dashboard_coc
from .features.manual import manual_coc as manual
from .features.params import ui_params as param_ui
from .components import styles_coc as styles

# ==========================================
# 2. 共通UIパーツ
# ==========================================
def _render_header():
    """【共通UI】タイトル描画"""
    c1, c2 = st.columns([0.85, 0.15])
    c1.title("🛠️ クトゥルフ神話TRPG ログ解析")
    # 狭い画面でも折り返さず、入りきらない分は「…」にする（styles_coc の .manual-button）
    with c2.container(key="manual_button"):
        if st.button("ℹ️ 使い方", width="stretch", help="使い方・仕様"):
            manual.show_manual()


# ==========================================
# 3. データの読み込み（結果はセッションの中で使い回す）
# ==========================================
def _session_cached(store_name, key, compute, max_entries):
    """
    計算結果をこのセッションの中で覚えておく（同じ key なら計算し直さない。覚えておくのは直近 max_entries 件）。
    st.cache_data は呼ぶたびにログ本文や表の中身を全部ハッシュ計算するので、
    ファイル名や設定だけで判断できるものはこちらを使う。
    """
    store = st.session_state.setdefault(store_name, {})
    if key not in store:
        if len(store) >= max_entries:
            store.pop(next(iter(store)))   # 一番古いものを捨てる
        store[key] = compute()
    return store[key]

def _load_key(profile):
    """
    読み込むログの組み合わせを表すキー。ファイルの追加・削除や履歴フォルダの読み込みのたびに増える番号で判断する
    （ファイルの中身は見ないので軽い）。後から足す機能が見るもの（自卓用ならPL対応表などの更新）も足す
    """
    return (tuple(st.session_state.file_dict), sidebar_files.sources_revision(), profile.addon.load_key())

LOG_NAME_COL = '_log_name'

def _read_all_logs(profile):
    """
    読み込み済みのログ（アップロード分＋後から足す機能が読み込むログ）を1つの表にまとめる。
    戻り値: (表, 読み込みに関する注意のリスト, 読み込み元 → その中のログのファイル名)
    """
    dfs, messages = [], []
    source_files = {}   # 読み込み元（アップロードしたファイル・ZIP・履歴フォルダ）→ その中のログのファイル名
    uploaded = st.session_state.file_dict
    names = []
    if uploaded:
        up_df, parse_messages = parser.parse_files(uploaded)
        dfs.append(up_df)
        messages.extend(parse_messages)
        names = up_df['ファイル名'].unique().tolist() if not up_df.empty else []
        # ZIP の中のログは、表示名ではなく、読み込んだ ZIP の名前の列で見分ける（名前に「 内の 」が入っていても間違えないように）
        by_zip = {}
        for name, zip_name in ccfolia_reader.zip_members(up_df):
            by_zip.setdefault(zip_name, set()).add(name)
        for key in uploaded:
            source_files[key] = by_zip.get(key) or {key}
    extra_dfs, extra_messages, extra_files = profile.addon.read_logs(names)
    dfs.extend(extra_dfs)
    messages.extend(extra_messages)
    source_files.update(extra_files)

    dfs = [d for d in dfs if not d.empty]
    if not dfs:
        return pd.DataFrame(), messages, source_files
    df = pd.concat(dfs, ignore_index=True)
    # ログに書かれたままの名前（パラメータ増減のタブで、ステータスの変化の記録の名前を、画面での名前に揃えるのに使う）
    df[LOG_NAME_COL] = df['キャラクター名']
    # 後から足す機能のログに「統合前のキャラクター名」（元のキャラ名）があれば、アップロードしたログの分を埋めておく
    if '統合前のキャラクター名' in df.columns:
        df['統合前のキャラクター名'] = df['統合前のキャラクター名'].fillna(df['キャラクター名'])
    df = profile.addon.after_read(df)
    # 名前が空欄の駒（GMのダイス用など）は、画面で見えるように仮の名前で表示する
    # （後から足す機能の照合（自卓用のPL対応表など）は元の空欄名で済ませてあるので、ここで置き換えても影響しない）
    for col in ('キャラクター名', '統合前のキャラクター名'):
        if col in df.columns:
            is_blank = df[col].isna() | (df[col].astype(str).str.strip() == "")
            df.loc[is_blank, col] = logic_base.BLANK_CHAR_NAME
    return df, messages, source_files


# ==========================================
# 4. 画面の描画処理（View）
# ==========================================
def _render_upload_screen():
    """【画面A】アップロード画面（取り込み処理はサイドバーのアップローダーと共通）"""
    uploaded_files = st.file_uploader(
        "ログファイル（.html / .json / .txt / .zip など）をドロップ",
        type=sidebar_files.UPLOAD_TYPES,
        accept_multiple_files=True,
        key=f"nokeep_main_uploader_{st.session_state.uploader_key}",   # uploader_key はサイドバーのファイル管理が用意している
    )
    # 同じファイルを何度も取り込まないよう、取り込んだファイル（file_id）を覚えておき、新しく入れたものだけを取り込む
    done = st.session_state.setdefault("_main_uploaded_ids", set())
    new_files = [f for f in uploaded_files or [] if f.file_id not in done]
    if new_files:
        before = len(st.session_state.file_dict)
        sidebar_files.store_uploaded_files(new_files)
        done.update(f.file_id for f in new_files)
        # 読み込めたファイルが増えたときだけ、欄を空にしてやり直す（ダッシュボードに切り替わる）。
        # 1つも増えなかったとき（大きすぎるなど）は、欄をそのままにして、やり直しを繰り返さない（次に入れたファイルはそのまま取り込める）
        if len(st.session_state.file_dict) > before:
            st.session_state.uploader_key += 1
            st.rerun()

def _keep_hidden_settings(addon):
    """
    閉じたタブ・閉じた欄・条件付きで出す欄の設定は、描画しない回に Streamlit が捨ててしまうので、毎回値を書き戻す。
    どの設定を書き戻すかは、その欄を作っているモジュールの KEEP_PREFIXES / KEEP_KEYS（後から足す機能は keep_prefixes）に書く
    （ここで1回にまとめて行う）。入力欄を作る前に呼ぶ（作った後の欄の値は書き換えられない）
    """
    common.keep_widget_state(
        prefixes=sidebar_selector.KEEP_PREFIXES + sidebar_coc.KEEP_PREFIXES + dashboard_coc.KEEP_PREFIXES
                 + tuple(addon.keep_prefixes)
                 + common.option_checkbox_prefixes(),   # 選択肢が変わるチェックボックス（成功度・コマンドなど）は自動で載る
        keys=sidebar_coc.KEEP_KEYS)

def _render_dashboard_screen(profile):
    """【画面B】ダッシュボードメイン画面"""
    addon = profile.addon
    _keep_hidden_settings(addon)
    recalc_rule = st.session_state['recalc_rule']   # 初期値は profiles.activate で入れている
    extract_bp  = st.session_state.get('extract_bp', False)
    rescue_diff = st.session_state.get('rescue_diff', False)
    split_combined = st.session_state.get(sidebar_coc.SPLIT_COMBINED_KEY, True)

    # 1. データの読み込み（ファイルの組み合わせが変わったときだけ解析し直す）
    load_key = _load_key(profile)
    with st.spinner("ログを解析中..."):
        # 読み込むログが変わったら前の解析結果は使わないので、1つだけ覚えておく
        raw_df, messages, source_files = _session_cached("_loaded_logs", load_key, lambda: _read_all_logs(profile), max_entries=1)
    st.session_state["_source_files"] = source_files   # ファイルを ✖ で消すときに、関連する設定も消すため
    for message in messages:
        st.warning(f"⚠️ {message}")
    if raw_df.empty:
        st.warning("ダイスロールが見つかりませんでした。")
        common.keep_all_widget_state()   # サイドバーの絞り込みを描画しないので、その設定が消えないように残す
        return

    # 2. データの加工
    # 再計算はPLの絞り込みより先に行う（絞り込みを変えるたびに再計算し直さないように）
    # 設定を行き来したとき用に、直近2つの設定の結果を覚えておく
    full_df = _session_cached(
        "_preprocessed_logs", (load_key, extract_bp, rescue_diff, recalc_rule, split_combined),
        lambda: logic_coc.preprocess_raw_data(raw_df, extract_bp, rescue_diff, recalc_rule, split_combined),
        max_entries=2,
    ).copy(deep=False)   # 覚えておいた表を、この後の処理で書き換えないように（pandas 3 では、書き換えた列だけが複製される）
    # 「通常結果に統合」は成功度フィルターより前に行い、フィルターの選択肢も統合後の表記にする
    full_df = logic_coc.integrate_results(
        full_df,
        extract_bp and st.session_state.get('chk_int_bp', False),
        rescue_diff and st.session_state.get('chk_int_rescue', False),
    )
    # 後から足す機能の表示の切り替え（自卓用なら PCモード／PLモードとPL名での絞り込み）
    full_df, view = addon.select_rows(full_df)
    if full_df.empty:
        st.warning("表示対象のダイスロールが見つかりませんでした。条件を変更してください。")
        common.keep_all_widget_state()   # PL名を全解除したときなどに、サイドバーの絞り込みの設定が消えないように残す
        return
    full_df = logic_base.add_search_keys(full_df)

    # 3. サイドバーの絞り込み設定
    # ココフォリアの ZIP の「部屋名[すべて]」は、同じ ZIP のタブごとのファイルと同じロールが入っているので、最初は表示しない
    overlapping = ccfolia_reader.overlapping_all_tab_files(ccfolia_reader.zip_members(full_df))
    selector = sidebar_selector.render_file_char_selector(full_df, default_tab_func=profile.default_tab_func,
                                                          default_off_files=overlapping)
    hidden_overlaps = [f for f in overlapping if f not in selector.sel_files]
    if hidden_overlaps:
        st.info("ℹ️ " + "、".join(f"「{common.escape_markdown(f)}」" for f in hidden_overlaps)
                + " は、同じ ZIP の中のタブごとのファイルと同じロールが入っているため、最初は表示していません"
                  "（サイドバーの「📄 表示ファイル・タブ・キャラ」でチェックを付けると表示します。両方表示すると同じロールを2回数えます）。")
    coc_filters = sidebar_coc.render_coc_filters(full_df, selector.sel_chars, recalc_rule)
    merges = sidebar_merge.render_character_merge_ui(full_df)
    params = CocFilterParams(selector=selector, merges=merges, **coc_filters)

    # 4. 絞り込みとダッシュボード描画
    df_filtered = logic_base.universal_filters(full_df, params)
    df_filtered = logic_coc.apply_coc_specific_filters(df_filtered, params)
    df_filtered = addon.after_filters(df_filtered, view)   # 後から足す機能の、表示のための印（自卓用ならロストの 💀）
    def param_inputs():
        """パラメータ増減のタブで使うもの（そのタブを開いたときだけ呼ぶ。後から足す機能のログを読み直すため）"""
        return param_ui.ParamInputs(
            files={**st.session_state.file_dict, **addon.param_log_files()},
            fix_changes=addon.fix_param_changes,
            decorate=lambda d: addon.after_filters(d, view),   # ほかのタブと同じ表示の印（自卓用ならロストの 💀）
            name_rows=addon.param_rows(full_df, view)[['ファイル名', LOG_NAME_COL, 'キャラクター名']],
            show_start_end=addon.param_show_start_end(view),
        )
    # 「🎛️絞り込み」の要約は、最初から外している ZIP の「すべて」のファイルを除いて数える（最初の状態では何も出ないように）
    notes_df = full_df[~full_df['ファイル名'].isin(hidden_overlaps)] if hidden_overlaps else full_df
    dashboard_coc.render_dashboard(full_df, df_filtered, recalc_rule, params, param_inputs,
                                   filter_notes=sidebar_coc.describe_filters(notes_df, params),
                                   summary_sort=addon.summary_default_sort(view),
                                   extra_tabs=addon.extra_tabs(df_filtered, recalc_rule, view))


# ==========================================
# 5. メインアプリケーション（Controller）
# ==========================================
# 設定リセットで残すもの（読み込んだログ・キャラ統合とその「1キャラを複数の統合に含める」・開いているタブ）。
# 後から足す機能の分は addon.reset_keep_keys
RESET_KEEP_KEYS = ("file_dict", "char_merges", "chk_allow_overlap", "dashboard_tab")

def main(profile=profiles.STANDARD):
    """profile: 通常版は STANDARD（既定）。自卓用はページ側（pages/pages_coc_shy.py）で作ったプロファイルを渡す。違いは profile_coc.py を参照"""
    st.set_page_config(page_title="CoC Log Analyzer", layout="wide")
    sidebar_nav.stop_if_shutdown()

    # セッションステートの初期化
    profiles.activate(profile)
    if "file_dict" not in st.session_state:
        st.session_state.file_dict = {}

    try:
        # ヘッダーとサイドバー
        st.html(styles.COC_GLOBAL_CSS)
        addon = profile.addon
        extra_sources = addon.file_sources()
        sidebar_files.render_file_manager(extra_sources, addon.per_log_prefixes)
        addon.render_sidebar()
        _render_header()

        # 画面の分岐
        if st.session_state.file_dict or extra_sources:
            _render_dashboard_screen(profile)
        else:
            _render_upload_screen()
    finally:
        # 途中でエラーが起きても「設定をリセット」で元に戻せるよう、必ず出す。
        sidebar_nav.render_sidebar_footer(current_system=profile.name,
                                          keep_on_reset=RESET_KEEP_KEYS + tuple(profile.addon.reset_keep_keys),
                                          data_keys=("file_dict",) + tuple(profile.addon.data_keys))
