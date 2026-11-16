import re
import zlib
from html import escape
from ...components.styles_coc import Colors
from ...components import badges_coc
from . import logic_sum

# ==========================================
# 1. テンプレート群（デザイン・構造の骨組み）
# ==========================================
NAME_COL_WIDTH = 180    # キャラクター名の列の幅(px)
TOTAL_COL_WIDTH = 60    # 総数の列の幅(px)
MIN_COL_WIDTH = 75      # その他の列の最小幅(px)。列が多いときは表を横スクロールにする

SUMMARY_CSS = f"""
<style>
/* 上部のメトリクス（5つの四角）。画面幅に合わせて1行に入る数だけ並べる */
.metrics-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 30px; }}
.metric-card {{ padding: 16px 10px; border-radius: 8px; background-color: {Colors.WHITE}; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; border: 1px solid {Colors.SLATE_200}; }}
/* カードの種類ごとの色（上の線・見出し・数字） */
.border-total {{ border-top: 4px solid {Colors.SLATE_400}; }}
.border-succ {{ border-top: 4px solid {Colors.GREEN_500}; }}
.border-cf {{ border-top: 4px solid {Colors.PURPLE_500}; }}
.border-crit {{ border-top: 4px solid {Colors.AMBER_500}; }}
.border-fumb {{ border-top: 4px solid {Colors.RED_500}; }}
.border-total .metric-label {{ color: {Colors.SLATE_400}; }} .border-total .metric-value {{ color: {Colors.SLATE_700}; }}
.border-succ .metric-label {{ color: {Colors.GREEN_800}; }}  .border-succ .metric-value {{ color: {Colors.GREEN_900}; }}
.border-cf .metric-label {{ color: {Colors.PURPLE_800}; }}   .border-cf .metric-value {{ color: {Colors.PURPLE_900}; }}
.border-crit .metric-label {{ color: {Colors.AMBER_900}; }}  .border-crit .metric-value {{ color: {Colors.AMBER_950}; }}
.border-fumb .metric-label {{ color: {Colors.RED_800}; }}    .border-fumb .metric-value {{ color: {Colors.RED_900}; }}
.metric-label {{ font-size: 14px; font-weight: 600; margin-bottom: 6px; }}
.metric-value {{ font-size: 28px; font-weight: 800; line-height: 1.1; margin-bottom: 4px; }}
.metric-unit {{ font-size: 14px; font-weight: 600; color: {Colors.SLATE_400}; margin-left: 4px; }}
.metric-sub {{ font-size: 12px; color: {Colors.SLATE_400}; font-weight: 500; }}

/* サマリー表。列が多くて横にスクロールするときは、キャラクター名の列を左に固定する
   （画像として保存するときは、export_coc が固定とスクロールを外して全体を写す） */
.table-scroll {{ overflow-x: auto; }}
.custom-table .char-name {{ position: sticky; left: 0; z-index: 1; }}
.custom-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 15px; color: {Colors.SLATE_700}; }}
.custom-table th, .custom-table td {{ border: 1px solid {Colors.SLATE_200}; padding: 10px 4px; text-align: center; vertical-align: middle; }}
.custom-table td {{ position: relative; }}
.custom-table th {{ padding: 8px 4px; line-height: 1.3; white-space: normal; word-break: keep-all; overflow-wrap: anywhere; }}
.custom-table td {{ font-weight: 500; white-space: nowrap; }}
.custom-table .char-name {{ width: {NAME_COL_WIDTH}px; text-align: left; padding-left: 12px; padding-right: 12px; white-space: normal; word-break: break-all; background: {Colors.WHITE}; }}
.custom-table th.char-name, .custom-table .overall-row .char-name {{ background: {Colors.SLATE_50}; }}
.custom-table .col-total {{ width: {TOTAL_COL_WIDTH}px; }}
.custom-table .overall-row {{ border-bottom: 3px solid {Colors.SLATE_300}; }}
.custom-table .cell-bold {{ font-weight: bold; }}
.custom-table .cell-strong {{ font-weight: 800; }}
.custom-table .unit {{ font-size: 0.85em; margin-left: 2px; }}
.custom-table .unit-count {{ color: {Colors.SLATE_400}; }}
.custom-table .count-sub {{ font-size: 0.8em; opacity: 0.7; }}
.custom-table .head-sub {{ color: {Colors.SLATE_400}; }}
.custom-table .head-rescue {{ color: {Colors.PINK_600}; }}
/* ハイライト（最大・最小）の枠 */
.custom-table .hl-box {{ position: absolute; inset: 0; border: 2px solid; pointer-events: none; }}
.custom-table .hl-box.hl-max {{ border-color: {Colors.YELLOW_500}; }}
.custom-table .hl-box.hl-min {{ border-color: {Colors.SLATE_400}; }}
</style>
"""
# 列ごとの色（背景・文字色）は、マスごとに style を書くと HTML が大きくなるので、表ごとに列のクラス（c0, c1, ...）で指定する。
# ハイライトしたマスの文字色は、列の色より後に書いて上書きする
HIGHLIGHT_TEXT_CSS = (f".custom-table td.cell-max {{ color: {Colors.YELLOW_900}; }}"
                      f".custom-table td.cell-min {{ color: {Colors.SLATE_700}; }}")

SUMMARY_METRICS_TEMPLATE = """
<div class="metrics-container">
    <div class="metric-card border-total">
        <div class="metric-label">総ロール数</div>
        <div class="metric-value">{total_rolls}<span class="metric-unit">回</span></div>
    </div>
    <div class="metric-card border-succ">
        <div class="metric-label">{m_succ_label}</div>
        <div class="metric-value">{m_succ_val}</div>
        <div class="metric-sub">{m_succ_sub}</div>
    </div>
    <div class="metric-card border-cf">
        <div class="metric-label">{m_cf_label}</div>
        <div class="metric-value">{m_cf_val}</div>
        <div class="metric-sub">{m_cf_sub}</div>
    </div>
    <div class="metric-card border-crit">
        <div class="metric-label">{m_crit_label}</div>
        <div class="metric-value">{m_crit_val}</div>
        <div class="metric-sub">{m_crit_sub}</div>
    </div>
    <div class="metric-card border-fumb">
        <div class="metric-label">{m_fumb_label}</div>
        <div class="metric-value">{m_fumb_val}</div>
        <div class="metric-sub">{m_fumb_sub}</div>
    </div>
</div>
"""
TABLE_WRAPPER_TEMPLATE = """
{column_styles}
<div class="table-scroll">
    <table class="custom-table {scope}" style="min-width: {min_width}px;">
        <thead><tr>{headers_html}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
</div>
"""

# 見出しで長い結果名を2行に折る
HEADER_LABELS = {
    "クリファン率": "クリ<br>ファン", "クリファン数": "クリ<br>ファン",
    "期待との差": "期待<br>との差",
    "期待成功率": "期待<br>成功率", "期待成功数": "期待<br>成功数",
    "100ファン": "100<br>ファン",
    'クリティカル': 'クリ<br>ティカル',
    'イクストリーム成功': 'Ex<br>成功',
    'ハード成功': 'ハード<br>成功',
    'レギュラー成功': 'レギュ<br>成功',
    '決定的成功': '決定的<br>成功',
    'スペシャル': 'スペ<br>シャル',
    '致命的失敗': '致命的<br>失敗',
    'ファンブル': 'ファン<br>ブル',
    '決定的成功/スペシャル': '決定的<br><small>/スペ</small>',
}
SUB_RESULT_ABBREV = {'イクストリーム': 'Ex', 'レギュラー': 'レギュ'}   # BP内訳の括弧内の省略


# ==========================================
# 2. セル装飾・文字列整形の裏方関数群
# ==========================================
def _get_color_theme(label, selected_successes):
    """サマリー表のラベル（成功度）に応じたテーマ色セット (見出しの背景, セルの背景, 文字色) を返す"""
    base = str(label).split('（')[0]

    if any(x in label for x in ['成功率', '成功数', 'クリファン', '期待']):
        return Colors.THEME_PURPLE
    if any(x in base for x in ['クリティカル', '決定的', '1クリ']):
        return Colors.THEME_CRIT
    if any(x in base for x in ['ファンブル', '致命的', '100ファン']):
        return Colors.THEME_FUMB
    # 総数などはここで決まる（「成功」の基準で選ばれた結果は緑、それ以外は灰色）
    return Colors.THEME_SUCC if label in selected_successes else Colors.THEME_FAIL


def _get_header_html(col_name):
    """サマリー表のヘッダーのHTML（長い名前は2行にし、BP内訳・救済は小さく添える）"""
    is_rescue = '（救済）' in col_name
    base = col_name.replace('（救済）', '')
    sub_text = ""
    sub_match = re.search(r'（(.*?)）', base)
    if sub_match:
        sub_text = sub_match.group(1)
        for long, short in SUB_RESULT_ABBREV.items():
            sub_text = sub_text.replace(long, short)
        base = base.replace(sub_match.group(0), '')

    # 「再計算しない」では結果がログの文字列そのままなので、HTML として解釈されないようにする
    html = HEADER_LABELS.get(base, escape(base))
    if sub_text:
        html += f"<br><small class='head-sub'>({escape(sub_text)})</small>"
    if is_rescue:
        html += "<br><small class='head-rescue'>（救済）</small>"
    return html


def _get_highlight(col_key, row_data, hl, max_dict, min_dict, df_eligible, flat_cache):
    """
    ハイライトする場合は "max"（最大値）か "min"（最小値）、しない場合は None を返す。
    hl: logic_sum.HighlightConfig / df_eligible: ハイライトの対象にするキャラの行
    """
    if not hl.use_highlight or col_key not in hl.keys or row_data['キャラクター名'] not in flat_cache['_names']:
        return None
    target_raw_col = logic_sum.raw_col(col_key, hl.basis)
    c_val = row_data[target_raw_col]
    # 全員同じ値の列はハイライトしない（列ごとに1回だけ判定して覚えておく）
    if target_raw_col not in flat_cache:
        flat_cache[target_raw_col] = df_eligible[target_raw_col].max() == df_eligible[target_raw_col].min()
    if flat_cache[target_raw_col]:
        return None
    # 最大値・最小値も raw_col と同じ列で求めてある（総数は回数）
    c_max, c_min = max_dict[hl.basis][col_key], min_dict[hl.basis][col_key]
    return logic_sum.highlight_kind(c_val, c_max, c_min, hl, signed=col_key in logic_sum.SIGNED_KEYS)


def _format_expected_cell(row, col_key, display_mode, show_expected_sub):
    """
    期待成功率・「期待との差」のマス（回数は期待値なので小数で出す）。
    show_expected_sub: 「期待との差」の下に期待成功率を小さく添えるか（期待成功率の列を隠しているとき）
    """
    if not row['_exp_n']:
        return "<span class='count-sub'>—</span>"
    sign = "+" if col_key == logic_sum.EXPECTED_KEY else ""
    cnt, pct = row[f'_raw_count_{col_key}'], row[f'_raw_pct_{col_key}']
    cnt_html = f"{cnt:{sign}.1f}<span class='unit unit-count'>回</span>"
    pct_html = f"{pct:{sign}.1f}<span class='unit'>%</span>"
    main = cnt_html if display_mode == logic_sum.DISPLAY_COUNT else pct_html
    if col_key == logic_sum.EXPECTED_KEY:
        if not show_expected_sub:
            return main
        rate = logic_sum.EXPECTED_RATE_KEY
        sub = f"{row[f'_raw_count_{rate}']:.1f} 回" if display_mode == logic_sum.DISPLAY_COUNT else f"{row[f'_raw_pct_{rate}']:.1f}%"
        return f"{main}<br><span class='count-sub'>( 期待 {sub} )</span>"
    if display_mode == logic_sum.DISPLAY_BOTH:
        return f"{pct_html}<br><span class='count-sub'>( {cnt:.1f} 回 )</span>"
    return main

def _format_cell_content(row, col_key, display_mode, show_expected_sub=True):
    if col_key in (logic_sum.EXPECTED_KEY, logic_sum.EXPECTED_RATE_KEY):
        return _format_expected_cell(row, col_key, display_mode, show_expected_sub)
    cnt, pct = row[f'_raw_count_{col_key}'], row[f'_raw_pct_{col_key}']
    cnt_html = f"{cnt}<span class='unit unit-count'>回</span>"
    pct_html = f"{pct:.1f}<span class='unit'>%</span>"
    if col_key == "総数" or display_mode == logic_sum.DISPLAY_COUNT:
        return cnt_html
    if display_mode == logic_sum.DISPLAY_PCT:
        return pct_html
    return f"{pct_html}<br><span class='count-sub'>( {cnt} 回 )</span>"


def _cell_html(content, col_class, classes="", highlight=None):
    """1マス分。col_class: 列の色のクラス / highlight: "max"・"min"（ハイライトの枠）または None"""
    overlay = f"<div class='hl-box hl-{highlight}'></div>" if highlight else ""
    class_attr = f"{col_class} {classes}" if classes else col_class
    return f'<td class="{class_attr}">{overlay}{content}</td>'


# ==========================================
# 3. HTML構築のメイン処理（UIから呼ばれる）
# ==========================================
def build_metrics_html(overall_data, display_mode, succ_col_name, cf_col_name):
    """全体のメトリクスカード（5つの四角）のHTMLを組み立てる"""
    total_rolls = overall_data['総数']

    def card(label_count, label_rate, count):
        """(見出し, 大きい数字, 小さい補足) を表示形式に合わせて作る"""
        if display_mode == logic_sum.DISPLAY_COUNT:
            return label_count, f"{count}<span class='metric-unit'>回</span>", ""
        pct = (count / total_rolls * 100) if total_rolls else 0
        return label_rate, f"{pct:.1f}<span class='metric-unit'>%</span>", f"({count} 回)"

    m_succ_label, m_succ_val, m_succ_sub = card(f"全体{succ_col_name}", f"全体{succ_col_name}", overall_data['succ_count'])
    m_cf_label, m_cf_val, m_cf_sub = card(f"全体{cf_col_name}", f"全体{cf_col_name}", overall_data['cf_count'])
    m_crit_label, m_crit_val, m_crit_sub = card("クリティカル数", "クリティカル率", overall_data['crit_count'])
    m_fumb_label, m_fumb_val, m_fumb_sub = card("ファンブル数", "ファンブル率", overall_data['fumb_count'])

    return SUMMARY_METRICS_TEMPLATE.format(
        total_rolls=total_rolls,
        m_succ_label=m_succ_label, m_succ_val=m_succ_val, m_succ_sub=m_succ_sub,
        m_cf_label=m_cf_label,     m_cf_val=m_cf_val,     m_cf_sub=m_cf_sub,
        m_crit_label=m_crit_label, m_crit_val=m_crit_val, m_crit_sub=m_crit_sub,
        m_fumb_label=m_fumb_label, m_fumb_val=m_fumb_val, m_fumb_sub=m_fumb_sub
    )


def build_table_html(
        overall_data, df_chars, disp_keys, disp_labels,
        selected_columns_keys, selected_successes, display_mode,
        hl, max_dict, min_dict):
    """サマリー内訳表のHTMLを組み立てる（hl: logic_sum.HighlightConfig。総数が hl.min_rolls 回未満のキャラはハイライトしない）"""
    # 表示する列（キー, 見出し, 列のクラス）を先にまとめ、列ごとの色を CSS にする
    columns, rules = [], []
    for k, label in zip(disp_keys, disp_labels):
        if k in selected_columns_keys:
            h_bg, c_bg, c_text = _get_color_theme(label, selected_successes)
            col_class = f"c{len(columns)}"
            rules.append(f".custom-table th.{col_class} {{ background: {h_bg}; color: {c_text}; }}"
                         f".custom-table td.{col_class} {{ background: {c_bg}; color: {c_text}; }}")
            columns.append((k, label, col_class))
    show_expected_sub = logic_sum.EXPECTED_RATE_KEY not in selected_columns_keys

    headers = ['<th class="char-name">キャラクター名</th>']
    for k, label, col_class in columns:
        total_class = " col-total" if k == "総数" else ""
        headers.append(f'<th class="{col_class}{total_class}">{_get_header_html(label)}</th>')

    # 全体（全員の合計）の行
    rows = [f'<tr class="overall-row"><td class="char-name">{logic_sum.OVERALL_LABEL}</td>']
    for k, _, col_class in columns:
        rows.append(_cell_html(_format_cell_content(overall_data, k, display_mode, show_expected_sub), col_class))
    rows.append('</tr>')

    # 各キャラクター行（iterrows は1行ずつ表を作るので遅い。itertuples は「_」で始まる列名を変えてしまうので辞書で回す）
    df_eligible = df_chars[logic_sum.highlight_eligible(df_chars, hl.min_rolls)]
    flat_cache = {'_names': set(df_eligible['キャラクター名'])}
    for row in df_chars.to_dict('records'):
        char_name_html = badges_coc.format_char_name_html(row["キャラクター名"], row["_orig_name"], row["_file_name"], mode="summary")
        rows.append(f'<tr><td class="char-name">{char_name_html}</td>')
        for k, _, col_class in columns:
            highlight = _get_highlight(k, row, hl, max_dict, min_dict, df_eligible, flat_cache)
            classes = f"cell-strong cell-{highlight}" if highlight else ("cell-bold" if k == "cf_col" else "")
            rows.append(_cell_html(_format_cell_content(row, k, display_mode, show_expected_sub), col_class, classes, highlight))
        rows.append('</tr>')
    headers_html, rows_html = "".join(headers), "".join(rows)

    min_width = NAME_COL_WIDTH + sum(TOTAL_COL_WIDTH if k == "総数" else MIN_COL_WIDTH for k, *_ in columns)
    # 同じ画面に別の列構成の表が出ても色が混ざらないよう、列のクラスを表ごとの名前（t○○ の下）に限る
    scope = f"t{zlib.crc32(''.join(rules).encode()):08x}"
    column_css = "".join(rules).replace(".custom-table ", f".{scope} ")
    return TABLE_WRAPPER_TEMPLATE.format(column_styles=f"<style>{column_css}{HIGHLIGHT_TEXT_CSS}</style>", scope=scope,
                                         min_width=min_width, headers_html=headers_html, rows_html=rows_html)
