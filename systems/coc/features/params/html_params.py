"""「📉 パラメータ増減」タブの表のHTML（見た目は総合サマリーの表と同じ。CSS は html_sum.SUMMARY_CSS を使う）"""
import zlib
from html import escape
import pandas as pd
from ...components.styles_coc import Colors
from ...components import badges_coc
from ..summary import html_sum

# パラメータごとの列の色（見出しの背景, マスの背景, 文字色）
PARAM_THEMES = {"SAN": Colors.THEME_PURPLE, "HP": Colors.THEME_FUMB, "MP": Colors.THEME_SKY, "幸運": Colors.THEME_CRIT}
COL_WIDTH = 80   # 数字の列の最小幅(px)。列が多いときは表を横スクロールにする


def _cell(value, col_class, highlight=None, decimal=False):
    content = "" if pd.isna(value) else (f"{float(value):.1f}" if decimal else f"{int(value)}")
    overlay = f"<div class='hl-box hl-{highlight}'></div>" if highlight else ""
    classes = f"{col_class} cell-strong cell-{highlight}" if highlight else col_class
    return f'<td class="{classes}">{overlay}{content}</td>'

def name_cell_html(name, name_files=None):
    """
    名前のマス。総合サマリーと同じく、名前の末尾の括弧の中身や「ファイルごとに区別」のファイル名は、2段目に小さく出す。
    name_files: 名前 → その名前のロールがあったファイル名（「名前 (ファイル名)」のファイル名を見分ける。無ければ括弧の中身として出す）
    """
    return badges_coc.format_char_name_html(str(name), None, (name_files or {}).get(name), mode="summary")

def name_cell(name, name_files=None):
    """名前のマス（<td>）。title に元の名前をそのまま入れる（2段に分けて出しても、マウスを乗せると元の名前が分かるように）"""
    return f'<td class="char-name" title="{escape(str(name))}">{name_cell_html(name, name_files)}</td>'

def build_table_html(table, columns, marks, total_row, name_header="キャラクター名", total_label=html_sum.logic_sum.OVERALL_LABEL,
                     decimal_columns=(), name_files=None):
    """
    table: キャラごとの表（logic_params.summarize の形） / columns: 出す列（並び順どおり）
    marks: 強調するマス（logic_params.highlight_marks） / total_row: 全体の行（logic_params.totals）
    name_header: 名前の列の見出し / total_label: 全体の行の名前 / decimal_columns: 小数1桁で出す列（平均など）
    name_files: 名前の見せ方に使う、名前 → ファイル名（name_cell_html）
    """
    rules, cols = [], []
    for col in columns:
        param, _, item = col.partition(" ")
        h_bg, c_bg, c_text = PARAM_THEMES.get(param, Colors.THEME_FAIL)
        col_class = f"c{len(cols)}"
        rules.append(f".custom-table th.{col_class} {{ background: {h_bg}; color: {c_text}; }}"
                     f".custom-table td.{col_class} {{ background: {c_bg}; color: {c_text}; }}")
        cols.append((col, f"{escape(param)}<br>{escape(item)}", col_class))

    headers = [f'<th class="char-name">{escape(name_header)}</th>'] + [f'<th class="{c}">{label}</th>' for _, label, c in cols]
    rows = [f'<tr class="overall-row"><td class="char-name">{escape(total_label)}</td>']
    rows += [_cell(total_row.get(col), c, decimal=col in decimal_columns) for col, _, c in cols]
    rows.append('</tr>')
    for char, row in table.iterrows():
        rows.append(f'<tr>{name_cell(char, name_files)}')
        rows += [_cell(row[col], c, marks.get((char, col)), col in decimal_columns) for col, _, c in cols]
        rows.append('</tr>')

    scope = f"t{zlib.crc32(''.join(rules).encode()):08x}"   # 同じ画面のほかの表と列の色が混ざらないように
    column_css = "".join(rules).replace(".custom-table ", f".{scope} ")
    return html_sum.TABLE_WRAPPER_TEMPLATE.format(
        column_styles=f"<style>{column_css}{html_sum.HIGHLIGHT_TEXT_CSS}</style>", scope=scope,
        min_width=html_sum.NAME_COL_WIDTH + COL_WIDTH * len(cols), headers_html="".join(headers), rows_html="".join(rows))
