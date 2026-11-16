"""「🎯 出目の分布」タブの画面（キャラごとに、出目が 1〜10、11〜20、… のどこに何回入ったか）"""
import altair as alt
import pandas as pd
import streamlit as st
from components import common_ui as common
from ...components import export_coc as export, highlight_coc
from ..summary import html_sum, logic_sum
from . import logic_dice, html_dice

# このタブの入力欄の key はすべて「dice_」で始める（dashboard_coc.KEEP_PREFIXES で、タブを移っても残す）
KEY_PREFIX = "dice"
DEFAULT_SORT = (logic_dice.SORT_BY_NAME, common.SORT_ASC)   # 並び順の初期値（名前順）
MIN_ROWS_DEFAULT = 30   # 色付け・強調の対象にする最低のロール数（少ないと、たまたまの偏りが大きく見えるため）
CHART_HEIGHT = 360


def _render_settings(prefix, name_header, default_sort):
    """
    区切りの幅・表示・色・列・並び順の設定。default_sort: 並び順の初期値（列, 順序）。
    戻り値: (幅, 単位, 色を付けるか, 出す列, 並び替えの基準, 昇順か, 色付け・強調の対象にする最低のロール数)
    """
    k = lambda name: f"{prefix}_{name}"
    c1, c2, c3 = st.columns([0.22, 0.53, 0.25], vertical_alignment="bottom")
    common.init_state(k("width"), logic_dice.WIDTHS[0])
    width = c1.radio("区切りの幅:", logic_dice.WIDTHS, key=k("width"), horizontal=True, format_func=lambda w: f"{w} ずつ")
    if st.session_state.get(k("unit")) not in logic_dice.UNITS:   # 前の版の選択肢の名前が残っていたら、初期値に戻す
        st.session_state.pop(k("unit"), None)
    common.init_state(k("unit"), logic_dice.UNITS[0])
    unit = c2.radio("表示形式:", logic_dice.UNITS, key=k("unit"), horizontal=True)
    common.init_state(k("heat_on"), True)
    heat_on = c3.toggle("多い・少ないで色分け", key=k("heat_on"),
                        help="偏りが無いときの割合より多いマスはオレンジ、少ないマスは青（離れているほど濃い）")

    with st.expander("🔽 表の表示・並び替え設定", expanded=False):
        common.init_state(k("show_total"), True)
        common.init_state(k("show_mean"), True)
        c1, c2 = st.columns(2)
        show_total = c1.checkbox(logic_dice.TOTAL, key=k("show_total"))
        show_mean = c2.checkbox(logic_dice.MEAN, key=k("show_mean"), help=f"1〜100 が同じ確率で出るなら {logic_dice.MEAN_EXPECTED}")
        shown = ([logic_dice.TOTAL] if show_total else []) + ([logic_dice.MEAN] if show_mean else []) + logic_dice.bin_labels(width)

        st.divider()
        st.markdown("**🔄 行の並び替え**")
        options = [logic_dice.SORT_BY_NAME, logic_dice.TOTAL, logic_dice.MEAN] + logic_dice.bin_labels(width)
        # 並び順の初期値が変わったら（自卓用の PCモード⇔PLモードなど）その初期値に戻す。総合サマリーと同じ考え方
        # （「_」で始まるキーは「設定をリセット」でも消えないので、並び替えの設定が消えていたら初期値を入れ直す）
        if (st.session_state.get(f"_{prefix}_sort_default") != default_sort
                or k("sort_key") not in st.session_state or k("sort_order") not in st.session_state):
            st.session_state[f"_{prefix}_sort_default"] = default_sort
            st.session_state[k("sort_key")], st.session_state[k("sort_order")] = default_sort
        if st.session_state.get(k("sort_key")) not in options:   # 区切りの幅を変えて、選んでいた列が無くなったら名前順に戻す
            st.session_state[k("sort_key")], st.session_state[k("sort_order")] = DEFAULT_SORT
        common.init_state(k("sort_key"), default_sort[0])
        common.init_state(k("sort_order"), default_sort[1])
        c1, c2 = st.columns(2)
        sort_key = c1.selectbox("基準項目:", options, key=k("sort_key"),
                                format_func=lambda o: name_header if o == logic_dice.SORT_BY_NAME else o,
                                on_change=common.sort_order_updater(k("sort_key"), k("sort_order"),
                                                                    lambda basis: basis == logic_dice.SORT_BY_NAME))
        order = c2.radio("順序:", common.SORT_ORDER_OPTIONS, horizontal=True, key=k("sort_order"))

        st.divider()
        common.init_state(k("heat_min"), MIN_ROWS_DEFAULT)
        min_rows = st.number_input("色分け・強調をするのは、総数がこの回数以上の行だけ", min_value=0, step=10, key=k("heat_min"),
                                   help="ロールが少ないと、たまたまの偏りが大きく見えるため")
    return width, unit, heat_on, shown, sort_key, "降順" not in order, min_rows

def _highlight_values(table):
    """強調で比べる値の表（区切りの列は割合。総数が違う人どうしを回数で比べても意味が無いため）"""
    return logic_dice.percentages(table).astype(float)

def _render_chart(table, total_row, width, prefix):
    """選んだ行の割合を棒グラフで並べる（点線が、偏りが無いときの割合）"""
    k = f"{prefix}_chart_rows"
    options = list(total_row.index) + list(table.index)
    common.init_state(k, options[:1] + list(table[logic_dice.TOTAL].sort_values(ascending=False).index[:2]))
    st.session_state[k] = [o for o in st.session_state[k] if o in options]
    chosen = st.multiselect("グラフに出す行:", options, key=k)
    if not chosen:
        return
    pcts = logic_dice.percentages(pd.concat([total_row, table]))
    labels = logic_dice.bin_labels(width)
    data = pcts.loc[chosen, labels].reset_index(names="名前").melt(id_vars="名前", var_name="出目", value_name="割合")
    bars = alt.Chart(data).mark_bar().encode(
        x=alt.X("出目:N", sort=labels, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("名前:N", sort=chosen),
        y=alt.Y("割合:Q", title="割合（％）"),
        color=alt.Color("名前:N", sort=chosen, legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["名前", "出目", alt.Tooltip("割合:Q", format=".1f")],
    )
    expected = alt.Chart(pd.DataFrame({"y": [logic_dice.expected_pct(width)]})).mark_rule(strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart(bars + expected, height=CHART_HEIGHT, width="stretch")


# ==========================================
# 🌟 メイン関数
# ==========================================
def render_dice_distribution(df, prefix=KEY_PREFIX, by="キャラクター名", name_header="キャラクター名", row_label="キャラクター",
                             capture_id="capture-dice", default_sort=None):
    """
    df: ロールの表（サイドバーの絞り込み後）。by: 行にする列。name_header・row_label: 名前の列の見出しと、表の題の「○○別」。
    prefix・capture_id: 入力欄の key の頭と、画像保存で写す部分の id（ほかの画面でも使うときに変える）。
    default_sort: 並び順の初期値（列, 順序）。None なら名前順（自卓用の PLモードでは総合サマリーと同じく総数の多い順を渡す）
    """
    if df.empty:
        st.info("表示できるデータがありません。")
        return
    st.html(html_sum.SUMMARY_CSS)   # 表の見た目は総合サマリーと同じ
    width, unit, heat_on, shown, sort_key, ascending, min_rows = _render_settings(prefix, name_header, default_sort or DEFAULT_SORT)
    table = logic_dice.distribution(df, width, by)
    total_row = logic_dice.overall(df, width)
    if table.empty:
        st.info("1〜100 の出目のロールがありません。")
        return
    all_columns = [logic_dice.TOTAL, logic_dice.MEAN] + logic_dice.bin_labels(width)
    eligible = table[table[logic_dice.TOTAL] >= min_rows]
    hl = highlight_coc.render_column_highlight_settings(all_columns, len(eligible), prefix, [logic_dice.MEAN])
    marks = logic_sum.table_highlight_marks(_highlight_values(eligible), hl)

    sort_basis = table if unit == logic_dice.UNIT_COUNT else logic_dice.percentages(table)
    table = table.loc[logic_dice.sort_table(sort_basis, sort_key, ascending).index]

    st.divider()
    c1, c2 = st.columns([0.75, 0.25], vertical_alignment="bottom")
    c1.markdown(f"**▼ {row_label}別 出目の分布**")
    with c2:
        export.render_screenshot_button(capture_id, "CoC_Dice")
    view = html_dice.TableView(unit=unit, width=width, heat_on=heat_on, heat_min=min_rows)
    name_files = df.groupby(by)["ファイル名"].first().to_dict() if "ファイル名" in df.columns else None
    table_html = html_dice.build_table_html(table, total_row, shown, view, marks, name_header=name_header, name_files=name_files)
    st.html(f'<div id="{capture_id}">{table_html}</div>')
    notes = [f"偏りが無ければ、どの区切りも {logic_dice.expected_pct(width):.0f}% くらいになります（平均出目は {logic_dice.MEAN_EXPECTED}）。"]
    if heat_on:
        notes.append("それより多いマスはオレンジ、少ないマスは青で、離れているほど濃くしています。")
    notes.append(f"総数が {min_rows} 回未満の行は、たまたまの偏りが大きいので、色分け・強調をしません。"
                 "強調では、区切りの列は割合で比べます。"
                 "ボーナス・ペナルティダイスは、サイドバーの「B/Pダイスの内訳を抽出」が ON なら振った出目を全部、OFF なら採用された出目だけを数えます"
                 "（採用された出目は、ボーナスなら小さく、ペナルティなら大きく偏ります）。"
                 "詳しくは「ℹ️ 使い方」の「🎯 出目の分布 画面」を見てください。")
    st.caption("".join(notes))

    st.markdown("**▼ グラフ**")
    _render_chart(table, total_row, width, prefix)
