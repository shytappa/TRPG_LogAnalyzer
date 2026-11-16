"""「📉 パラメータ増減」タブの画面（SAN の減った・回復した量、HP・MP・幸運の減った量をキャラごとに出す）"""
import os
from dataclasses import dataclass
from typing import Callable
import pandas as pd
import streamlit as st
from core import ccfolia_reader
from components import common_ui as common, sidebar_files
from ...components import export_coc as export
from ...components import highlight_coc
from ..summary import html_sum
from . import logic_params, html_params

# このタブの入力欄の key はすべて「prm_」で始める（dashboard_coc.KEEP_PREFIXES で、タブを移っても残す）
KEY_PREFIX = "prm"          # 表示する列（prm_col）・並び替え（prm_sort_）・強調（prm_hl）
FIX_PREFIX = "prm_fix_"     # SAN の開始・終了を直す欄


@dataclass
class ParamInputs:
    """
    files: 読むログ（ファイル名 → 中身。ZIP も可）
    fix_changes: 読んだ変化に、後から足す機能の側で保存してある直しを当てる関数（addon_coc.fix_param_changes。通常版は何もしない）
    name_rows: 数えるキャラと画面での名前を決めるロールの表（logic_params.select_characters の name_rows）
    show_start_end: SAN の開始・終了の列（と、それを直す欄）を出すか
    """
    files: dict
    fix_changes: Callable[[pd.DataFrame], pd.DataFrame] | None = None
    # 絞り込み・キャラクターの統合の後の表に、表示のための手を加える関数（addon_coc.after_filters。自卓用ならロストの 💀）
    decorate: Callable[[pd.DataFrame], pd.DataFrame] | None = None
    name_rows: pd.DataFrame | None = None
    show_start_end: bool = True


# 同じログなら読み直さない。全員で共有されるので、ロールの読み込み（parser_coc）と同じく件数と期間に上限を付ける
# （自分のPC：6時間、公開サーバー：1時間。マニュアルの「最長1時間で消えます」）
@st.cache_data(show_spinner=False, max_entries=8, ttl="6h" if ccfolia_reader.IS_LOCAL else "1h")
def _extract(file_items):
    """ログ（(ファイル名, 中身) のタプル）からパラメータの変化を読む。同じログなら読み直さない"""
    return logic_params.extract(dict(file_items))

def extract_changes(files):
    """ログ（ファイル名 → 中身）のパラメータの変化（logic_params.extract）。同じログなら読み直さない"""
    return _extract(tuple(files.items()))


# ==========================================
# 1. 設定の欄
# ==========================================
def _render_column_checkboxes(columns, prefix):
    """列のチェックボックスを、SAN（開始・減った・回復・終了）の行と、ほかのパラメータ（減った量）の行に分けて並べる"""
    groups = {}
    for col in columns:
        param = col.split(" ")[0]
        groups.setdefault(param if param in logic_params.data.PARAM_WITH_RECOVERY else "", []).append(col)
    for cols in groups.values():
        common.render_chunked_checkboxes(cols, prefix=prefix, num_columns=4)

def render_table_settings(columns, show_start_end, empty_cols, prefix=KEY_PREFIX, name_label=logic_params.SORT_BY_NAME):
    """
    表示する列と並び順。戻り値: (出す列, 並び替えの基準, 昇順か)。並び替えの基準が name_label なら名前順。
    最初は、全員が 0 の列（empty_cols）と、show_start_end でなければ SAN の開始・終了を出さない。
    prefix: 入力欄の key の頭（ほかの画面で同じ設定欄を使うときは変える）
    """
    col_prefix, sort_key_name, order_key = f"{prefix}_col", f"{prefix}_sort_key", f"{prefix}_sort_order"
    with st.expander("🔽 表の表示・並び替え設定", expanded=False):
        defaults = {c: c not in empty_cols and (show_start_end or c not in logic_params.START_END_COLUMNS) for c in columns}
        # 全員 0 かどうかが変わった列（読み込むログ・表示モードを変えたなど）は、チェックをそれに合わせる（変わらない列は、選んだまま）
        prev_empty = st.session_state.get(f"_{prefix}_empty_cols")
        if prev_empty is not None:
            for c in set(prev_empty) ^ set(empty_cols):
                if c in columns:
                    st.session_state[common.checkbox_key(col_prefix, c)] = defaults[c]
        st.session_state[f"_{prefix}_empty_cols"] = list(empty_cols)
        # 開始・終了を出すかが変わったら（自卓用の PCモード⇔PLモード）、その2列のチェックも合わせる
        if st.session_state.get(f"_{prefix}_start_end_default") != show_start_end:
            st.session_state[f"_{prefix}_start_end_default"] = show_start_end
            for c in logic_params.START_END_COLUMNS:
                if c in columns:
                    st.session_state[common.checkbox_key(col_prefix, c)] = defaults[c]
        for c in columns:
            common.init_state(common.checkbox_key(col_prefix, c), defaults[c])
        common.render_filter_header(title="▼ 表示する列の選択", prefix=col_prefix, item_list=columns,
                                    default_states=defaults, show_reset=True)
        _render_column_checkboxes(columns, col_prefix)
        shown = [c for c in columns if st.session_state.get(common.checkbox_key(col_prefix, c))]

        st.divider()
        st.markdown("**🔄 行の並び替え**")
        options = [name_label] + columns
        if st.session_state.get(sort_key_name) not in options:   # 列が無くなったら（PLモードに切り替えたなど）、名前順に戻す
            st.session_state[sort_key_name], st.session_state[order_key] = name_label, common.SORT_ASC
        common.init_state(sort_key_name, name_label)
        common.init_state(order_key, common.SORT_ASC)
        c1, c2 = st.columns(2)
        sort_key = c1.selectbox("基準項目:", options, key=sort_key_name,
                                on_change=common.sort_order_updater(sort_key_name, order_key,
                                                                    lambda basis: basis == name_label))
        order = c2.radio("順序:", common.SORT_ORDER_OPTIONS, horizontal=True, key=order_key)
    return shown, sort_key, "降順" not in order

def render_highlight_settings(columns, row_count, prefix=KEY_PREFIX, default=lambda c: c.endswith(logic_params.LOSS)):
    """
    マスの強調表示（欄は総合サマリーと共通の highlight_coc）。戻り値: logic_params.HighlightConfig。
    row_count: 比べる行の数 / default: 最初に強調する列か（最初は「減少」の列）
    """
    return highlight_coc.render_column_highlight_settings(
        columns, row_count, prefix, [c for c in columns if default(c)], _render_column_checkboxes)

def _fix_key(kind, char):
    return f"{FIX_PREFIX}{kind}_{char}"

def _clear_fix_inputs_if_logs_changed():
    """
    読み込むログが変わったら（追加・✖ で削除・履歴フォルダの読み込み）、SAN の開始・終了を直す欄を空に戻す
    （入力欄はキャラ名で区別しているので、入れ替えた別のログの同じ名前のキャラに、前の値が付いてしまうため）
    """
    revision = sidebar_files.sources_revision()
    previous = st.session_state.get("_prm_fix_sources_rev")
    if previous is not None and previous != revision:
        for key in [k for k in st.session_state.keys() if isinstance(k, str) and k.startswith(FIX_PREFIX)]:
            del st.session_state[key]
    st.session_state["_prm_fix_sources_rev"] = revision

def _render_fix_inputs(table):
    """SAN の開始・終了を直す欄。戻り値: {キャラクター名: (開始 または None, 終了 または None)}（直したキャラだけ）"""
    start_col, end_col = logic_params.START_END_COLUMNS
    if start_col not in table.columns:
        return {}
    chars = [c for c in table.index if not table.loc[c, [start_col, end_col]].isna().all()]
    with st.expander("✏️ SAN の開始・終了を直す（ログの値と実際が違うとき）"):
        st.caption("空欄ならログの値を使います。直すと、直した分の差を「減少」（多く減っていたとき）か「回復」（少なく減っていたとき）に足します。"
                   "ページを開き直したときと、読み込むログを変えたときに元に戻ります。")
        h1, h2, h3 = st.columns([0.4, 0.3, 0.3])
        h1.caption("キャラクター名")
        h2.caption(start_col)
        h3.caption(end_col)
        for char in chars:
            c1, c2, c3 = st.columns([0.4, 0.3, 0.3], vertical_alignment="center")
            c1.markdown(common.escape_markdown(char))   # 書式として読まない（「# KP」が見出し、「*ミア*」が斜体にならないように）
            for col, kind, label in ((c2, "start", start_col), (c3, "end", end_col)):
                # value=None：数値を入れた後でも空欄（ログの値を使う）に戻せる欄にする
                # 見出しは隠すが、画面の読み上げでどのキャラの欄か分かるようにキャラ名を入れる
                col.number_input(f"{common.escape_markdown(char)} の {label}", value=None, step=1, key=_fix_key(kind, char),
                                 placeholder=f"ログの値: {table.loc[char, label]}", label_visibility="collapsed")
    fixes = {}
    for char in chars:
        start, end = st.session_state.get(_fix_key("start", char)), st.session_state.get(_fix_key("end", char))
        if start is not None or end is not None:
            fixes[char] = (start, end)
    return fixes


# ==========================================
# 2. 🌟 メイン関数
# ==========================================
def render_param_changes(inputs, params):
    """
    inputs: ParamInputs（読むログ・保存してある直し・数えるキャラ）。params: サイドバーの絞り込み（表示するファイル・キャラ、キャラクターの統合）
    """
    st.html(html_sum.SUMMARY_CSS)   # 表の見た目は総合サマリーと同じ
    _clear_fix_inputs_if_logs_changed()
    changes = extract_changes(inputs.files)
    # 後から足す機能の直しは、記録が無いかを見る前に当てる（記録の無い探索者の直しだけがあるときも数えるため）
    if inputs.fix_changes is not None:
        changes = inputs.fix_changes(changes)
    if changes.empty:
        st.info("ログにステータスの変化の記録（「SAN : 50 → 44」など）が見つかりませんでした。")
        return
    selected = logic_params.select_characters(changes, params, inputs.name_rows)
    if inputs.decorate is not None and not selected.empty:
        selected = inputs.decorate(selected)
    if selected.empty:
        st.info("表示中のキャラには、ステータスの変化の記録がありません。")
        return

    base = logic_params.summarize(selected)
    columns = list(base.columns)
    shown, sort_key, ascending = render_table_settings(columns, inputs.show_start_end, logic_params.empty_columns(base))
    hl = render_highlight_settings(columns, len(base))
    fixes = _render_fix_inputs(base) if inputs.show_start_end else {}
    table = logic_params.sort_table(logic_params.summarize(selected, fixes)[columns], sort_key, ascending)

    st.divider()
    c1, c2 = st.columns([0.75, 0.25], vertical_alignment="bottom")
    c1.markdown("**▼ キャラクター別 パラメータ増減**")
    with c2:
        export.render_screenshot_button("capture-params", "CoC_Params")
    if not shown:
        st.info("表示する列が選ばれていません。「🔽 表の表示・並び替え設定」で選んでください。")
    else:
        name_files = selected.groupby("キャラクター名")["ファイル名"].first().to_dict()
        table_html = html_params.build_table_html(table, shown, logic_params.highlight_marks(table, hl), logic_params.totals(table),
                                                  name_files=name_files)
        st.html(f'<div id="capture-params">{table_html}</div>')

    dropped = logic_params.outliers(selected)
    if not dropped.empty:
        # キャラ名・ファイル名は書式として読まない（「*ミア*」が斜体にならないように）
        lines = [f"{common.escape_markdown(r.キャラクター名)} の {r.パラメータ}：{r.前} → {r.後}"
                 f"（{common.escape_markdown(os.path.basename(str(r.ファイル名)))}）"
                 for r in dropped.itertuples()]
        st.caption(f"⚠️ 1回で {logic_params.RULES.outlier} 以上動いた変化は、集計から外しました（ふざけた値への切り替えなど）: " + "、".join(lines))
    st.caption("ココフォリアの駒のステータスを変えたときに残る「SAN : 50 → 44」などの記録から数えています。"
               "サイドバーのうち、表示するファイル・キャラとキャラクターの統合だけが効きます（成功度・技能などの絞り込みは効きません）。"
               "押し間違いなどの直し（すぐ逆向きに動かしたもの）は、前の変化と差し引いて1回にしています"
               f"（間に回復・ダメージのロールかそのキャラ自身のロールがあるときや、{logic_params.RULES.threshold} 発言より後のときは、本当の変化として数えます）。"
               "詳しくは「ℹ️ 使い方」の「📉 パラメータ増減 画面」を見てください。")
