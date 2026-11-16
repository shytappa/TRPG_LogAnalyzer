"""
マスの強調表示（ハイライト）の設定欄。総合サマリー・パラメータ増減・出目の分布（と自卓用の同じ形の表）で共通。
言葉・並び・初期値はここでだけ決める（前は画面ごとに書いてあり、直すたびに2か所を揃える必要があった）。
強調するマスの計算も共通（features/summary/logic_sum の highlight_extremes・highlight_kind）
"""
from dataclasses import dataclass
import streamlit as st
from components import common_ui as common
from .. import profile_coc as profiles
from ..features.summary import logic_sum

TYPE_BOTH, TYPE_MAX, TYPE_MIN = "最大と最小の両方", "最大/最高値", "最小/最低値"
TYPE_OPTIONS = [TYPE_BOTH, TYPE_MAX, TYPE_MIN]


@dataclass(frozen=True)
class HighlightKeys:
    """設定欄の入力欄の key（画面ごとに違う。basis・min_rolls は総合サマリーだけ）"""
    on: str           # ハイライト機能を有効にする
    columns: str      # 強調する列のチェックボックスの頭（common.checkbox_key）
    type: str         # 強調する対象（最大・最小）
    zero: str         # 最小値に 0 を含める
    use_tie: str      # 同率で無効化
    tie: str          # 同率の人数 N
    basis: str | None = None           # 判定数値（割合か回数か）
    use_min_rolls: str | None = None   # 総数が少ないキャラはハイライトしない
    min_rolls: str | None = None       # その回数


def prefixed_keys(prefix):
    """パラメータ増減・出目の分布などの key（「頭_on」「頭_type」…。列のチェックボックスは「頭_列名」）"""
    return HighlightKeys(on=f"{prefix}_on", columns=prefix, type=f"{prefix}_type", zero=f"{prefix}_zero",
                         use_tie=f"{prefix}_use_tie", tie=f"{prefix}_tie")


# 総合サマリーの key（自卓用プロファイルの widget_defaults が hl_include_zero・hl_use_tie を使っている）
SUMMARY_KEYS = HighlightKeys(on="sum_hl_toggle", columns="hl_chk", type="hl_type", zero="hl_include_zero",
                             use_tie="hl_use_tie", tie="hl_tie_count", basis="hl_basis",
                             use_min_rolls="hl_use_min_rolls", min_rolls="hl_min_rolls")


def _render_chunked_checkboxes(columns, prefix):
    common.render_chunked_checkboxes(columns, prefix=prefix, num_columns=4)

def render_column_highlight_settings(columns, row_count, prefix, default_columns, render_columns=_render_chunked_checkboxes):
    """
    列ごとの表（パラメータ増減・出目の分布など）の設定欄。key は「{prefix}_hl_…」。
    render_columns を渡さなければ、列のチェックボックスを4列で並べる
    """
    return render_highlight_settings(prefixed_keys(f"{prefix}_hl"), columns, row_count, default_columns, render_columns)


def render_highlight_settings(keys, columns, row_count, default_columns, render_columns,
                              expander_title="✨ マスの強調表示 (ハイライト設定)", columns_title="▼ 強調する列の選択"):
    """
    ハイライトの設定欄を描画して、logic_sum.HighlightConfig を返す。
    columns: 強調できる列 / row_count: 比べる行の数（「同率N人」の N の上限。その表でハイライトの比べ合いに入る行の数）
    default_columns: 最初に強調する列 / render_columns(列のリスト, チェックボックスの頭): 列のチェックボックスを並べる関数
    """
    profile = profiles.current()
    with st.expander(expander_title, expanded=False):
        st.markdown("**▼ 強調表示の有効化**")
        common.init_state(keys.on, True)
        use_highlight = st.toggle("ハイライト機能を有効にする", key=keys.on)
        st.divider()

        defaults = {c: c in default_columns for c in columns}
        for c in columns:
            common.init_state(common.checkbox_key(keys.columns, c), defaults[c])
        common.render_filter_header(title=columns_title, prefix=keys.columns, item_list=columns,
                                    default_states=defaults, show_reset=True)
        render_columns(columns, keys.columns)
        selected = tuple(c for c in columns if st.session_state.get(common.checkbox_key(keys.columns, c)))
        st.divider()

        st.markdown("**▼ ハイライトの判定基準**")
        basis = logic_sum.BASIS_PCT
        if keys.basis:
            c1, c2 = st.columns([0.3, 0.7])
            basis = c1.radio("判定数値:", logic_sum.BASIS_OPTIONS, horizontal=True, key=keys.basis)
            hl_type = c2.radio("強調する対象:", TYPE_OPTIONS, horizontal=True, key=keys.type)
        else:
            hl_type = st.radio("強調する対象:", TYPE_OPTIONS, horizontal=True, key=keys.type)

        # 初期値は自卓用プロファイルで ON にしている（profile_coc の widget_defaults。総合サマリーと同じ値を使う）
        c1, c2 = st.columns([0.3, 0.7])
        common.init_state(keys.zero, profile.widget_defaults.get("hl_include_zero", False))
        common.init_state(keys.use_tie, profile.widget_defaults.get("hl_use_tie", False))
        include_zero = c1.toggle("最小値に 0 (0%) を含める", key=keys.zero)
        tie_count = None
        if c2.toggle("同率（同じ値）がN人以上いる場合はハイライトを無効化する", key=keys.use_tie) and row_count >= 2:
            options = list(range(2, row_count + 1))
            # 比べる行の数が減って選択肢から外れたときも、初期値に戻す
            if st.session_state.get(keys.tie) not in options:
                st.session_state[keys.tie] = options[min(profile.hl_tie_count_index(row_count), len(options) - 1)]
            common.init_state(keys.tie, options[0])
            tie_count = c2.selectbox("N = :", options, key=keys.tie)

        min_rolls = 0
        if keys.use_min_rolls:
            # 1回振って1回クリティカルの人が「100%」で目立たないように
            _, c2 = st.columns([0.3, 0.7])
            common.init_state(keys.use_min_rolls, False)
            if c2.toggle("総数がN回未満のキャラはハイライトしない", key=keys.use_min_rolls):
                common.init_state(keys.min_rolls, 10)
                min_rolls = c2.number_input("N = ", min_value=1, max_value=9999, key=keys.min_rolls)

    return logic_sum.HighlightConfig(
        use_highlight=use_highlight, keys=selected, basis=basis,
        check_max=hl_type in (TYPE_BOTH, TYPE_MAX), check_min=hl_type in (TYPE_BOTH, TYPE_MIN),
        include_zero=include_zero, tie_count=tie_count, min_rolls=min_rolls,
    )
