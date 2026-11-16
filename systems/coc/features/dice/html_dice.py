"""「🎯 出目の分布」タブの表のHTML（見た目は総合サマリーの表と同じ。CSS は html_sum.SUMMARY_CSS を使う）"""
import zlib
from dataclasses import dataclass, replace
from html import escape
import pandas as pd
from ...components.styles_coc import Colors
from ..summary import html_sum
from ..params import html_params
from . import logic_dice

COL_WIDTH = 64       # 区切りの列の最小幅(px)
COL_WIDTH_BOTH = 76  # 割合＋回数のときの最小幅(px)
HEAT_LEVELS = 5      # 色の濃さの段階
PLAIN_THEME = Colors.THEME_SKY   # 色分けを OFF にしたときの区切りの列の色（見出し, マス, 文字）
HEAT_STEP = 0.1      # 期待からこれだけ離れるごとに1段濃くする（0.1 = 期待の1割）
MORE_RGB, LESS_RGB = Colors.AMBER_500, Colors.SKY_700   # 期待より多い／少ない


def _rgb(hex_color):
    return ", ".join(str(int(hex_color[i:i + 2], 16)) for i in (1, 3, 5))

def heat_level(dev):
    """期待からのずれ（logic_dice.deviation）→ 色の段階（多ければ +1〜+5、少なければ −1〜−5、ほぼ期待どおりなら 0）"""
    if pd.isna(dev):
        return 0
    level = min(HEAT_LEVELS, int(abs(dev) / HEAT_STEP + 1e-9))   # 1e-9: 0.2 / 0.1 が 1.999… になって1段下がらないように
    return level if dev > 0 else -level

def _heat_css(scope):
    rules = []
    for level in range(1, HEAT_LEVELS + 1):
        alpha = 0.1 + 0.1 * level
        rules.append(f".{scope} td.heat-p{level} {{ background: rgba({_rgb(MORE_RGB)}, {alpha:.2f}); }}")
        rules.append(f".{scope} td.heat-n{level} {{ background: rgba({_rgb(LESS_RGB)}, {alpha:.2f}); }}")
    return "".join(rules)

def _plain_css(scope):
    """色分けを OFF にしたときの、区切りの列の薄い色（白黒だけにならないように）"""
    head, cell, text = PLAIN_THEME
    return (f".{scope} th.col-bin {{ background: {head}; color: {text}; }}"
            f".{scope} td.col-bin {{ background: {cell}; color: {text}; }}")

def _value(value, kind):
    if pd.isna(value):
        return ""
    if kind == "pct":
        return f'{value:.1f}<span class="unit">%</span>'
    if kind == "mean":
        return f"{value:.1f}"
    return f"{int(value)}"

def _bin_value(pct, count, unit):
    """区切りのマスの中身（割合・回数・割合＋回数）"""
    if unit == logic_dice.UNIT_COUNT:
        return _value(count, "count")
    if unit == logic_dice.UNIT_BOTH and not pd.isna(pct):
        return f"{_value(pct, 'pct')}<br><span class='count-sub'>( {int(count)} 回 )</span>"
    return _value(pct, "pct")

def _classes(*names):
    names = [n for n in names if n]
    return f' class="{" ".join(names)}"' if names else ""

def _row(name, counts, pcts, columns, view, marks, row_class="", name_td=None):
    """1行分。name_td: 名前のマス（無ければ名前をそのまま出す。全体の行）"""
    if name_td is None:
        name_td = f'<td class="char-name">{escape(str(name))}</td>'
    cells = [f'<tr class="{row_class}">{name_td}']
    colored = view.heat_on and counts[logic_dice.TOTAL] >= view.heat_min
    for col in columns:
        mark = marks.get((name, col))
        hl = (f"cell-strong cell-{mark}", f"<div class='hl-box hl-{mark}'></div>") if mark else ("", "")
        sep = "col-sep" if col == view.last_stat else ""
        if col == logic_dice.TOTAL:
            cells.append(f'<td{_classes("col-total", "col-stat", sep, hl[0])}>{hl[1]}{_value(counts[col], "count")}</td>')
        elif col == logic_dice.MEAN:
            cells.append(f'<td{_classes("col-stat", sep, hl[0])}>{hl[1]}{_value(counts[col], "mean")}</td>')
        else:
            level = heat_level(logic_dice.deviation(pcts[col], view.width)) if colored else 0
            heat = "" if level == 0 else f'heat-{"p" if level > 0 else "n"}{abs(level)}'
            cells.append(f"<td{_classes('col-bin', heat, hl[0])}>{hl[1]}{_bin_value(pcts[col], counts[col], view.unit)}</td>")
    cells.append("</tr>")
    return "".join(cells)


@dataclass
class TableView:
    """表の見せ方。unit: 区切りの列を割合・回数・割合＋回数のどれで出すか / heat_on: 多い・少ないで色を付けるか /
    heat_min: 総数がこの回数以上の行だけ色を付ける / last_stat: 区切りの列の手前に線を引く列（総数・平均出目の最後）"""
    unit: str
    width: int
    heat_on: bool = True
    heat_min: int = 0
    last_stat: str | None = None

def build_table_html(table, total_row, columns, view, marks=None, name_header="キャラクター名", name_files=None):
    """
    table: 行ごとの回数の表（logic_dice.distribution の形、並べたい順） / total_row: 全体の1行の表（logic_dice.overall）
    columns: 出す列 / view: TableView / marks: 強調するマス {(行の名前, 列): "max" または "min"}
    name_files: 名前の見せ方に使う、名前 → ファイル名（総合サマリーと同じく、括弧の中身・ファイル名を2段目に出す）
    区切りのマスは、偏りが無いときの割合（区切りの幅 ％）より多いとオレンジ、少ないと青で、離れているほど濃くする
    """
    marks = marks or {}
    stats = [c for c in columns if c in (logic_dice.TOTAL, logic_dice.MEAN)]
    view = replace(view, last_stat=stats[-1] if stats and len(stats) < len(columns) else None)
    pcts, total_pcts = logic_dice.percentages(table), logic_dice.percentages(total_row)
    scope = f"d{zlib.crc32(','.join(columns).encode()):08x}"
    headers = [f'<th class="char-name">{escape(name_header)}</th>']
    for col in columns:
        label = "平均<br>出目" if col == logic_dice.MEAN else escape(col)   # 「平均出」「目」と折れないように
        stat = col in (logic_dice.TOTAL, logic_dice.MEAN)
        headers.append(f'<th{_classes("col-total" if col == logic_dice.TOTAL else "", "col-stat" if stat else "col-bin", "col-sep" if col == view.last_stat else "")}>{label}</th>')
    rows = [_row(total_row.index[0], total_row.iloc[0], total_pcts.iloc[0], columns, view, {}, "overall-row")]
    rows += [_row(name, table.loc[name], pcts.loc[name], columns, view, marks, name_td=html_params.name_cell(name, name_files))
             for name in table.index]
    css = (f".{scope} th {{ background: {Colors.SLATE_100}; color: {Colors.SLATE_700}; }}"
           f".{scope} td.col-stat {{ background: {Colors.SLATE_50}; }}"
           f".{scope} .col-sep {{ border-right: 3px solid {Colors.SLATE_300}; }}"
           + (_heat_css(scope) if view.heat_on else _plain_css(scope))
           + html_sum.HIGHLIGHT_TEXT_CSS.replace(".custom-table ", f".{scope} "))
    col_width = COL_WIDTH_BOTH if view.unit == logic_dice.UNIT_BOTH else COL_WIDTH
    return html_sum.TABLE_WRAPPER_TEMPLATE.format(
        column_styles=f"<style>{css}</style>", scope=scope,
        min_width=html_sum.NAME_COL_WIDTH + col_width * len(columns), headers_html="".join(headers), rows_html="".join(rows))
