import re
from ...components.styles_coc import Colors
from ...components import badges_coc

# ==========================================
# 1. テンプレート群（デザイン・構造の骨組み）
# ==========================================

SUMMARY_CSS = """
<style>
/* サマリー画面専用のレイアウト設定 */
.dashboard-wrapper { width: 100%; margin: 0 auto; padding: 0; font-family: sans-serif; }
.metrics-container { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 30px; }
@media (max-width: 1000px) { .metrics-container { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 600px) { .metrics-container { grid-template-columns: repeat(2, 1fr); } }

/* メトリクス（上部の四角）カードのデザイン */
.metric-card { padding: 16px 10px; border-radius: 8px; background-color: #ffffff; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.border-total { border-top: 4px solid #94a3b8; } 
.border-succ { border-top: 4px solid #10b981; } 
.border-cf { border-top: 4px solid #8b5cf6; } 
.border-crit { border-top: 4px solid #f59e0b; } 
.border-fumb { border-top: 4px solid #ef4444; }

.metric-label { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
.metric-value { font-size: 28px; font-weight: 800; line-height: 1.1; margin-bottom: 4px; }
.metric-unit { font-size: 14px; font-weight: 600; color: #94a3b8; margin-left: 4px; } 
.metric-sub { font-size: 12px; color: #94a3b8; font-weight: 500; }

/* テーブルのデザイン */
.table-scroll { overflow-x: auto; max-width: 100%; border: none; margin-bottom: 0px; }
.custom-table { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 15px; min-width: 800px; border-bottom: 1px solid #e0e0e0; }
.custom-table th, .custom-table td { border: 1px solid #e0e0e0; padding: 10px 4px; text-align: center; vertical-align: middle; font-weight: 500; position: relative; }
.custom-table .char-name, .custom-table th:first-child { text-align: left; padding-left: 12px; padding-right: 12px; white-space: normal; word-break: break-all; min-width: 140px; max-width: 200px; width: 18%; }
.overall-row { border-bottom: 3px solid #cbd5e1; }
</style>
"""

SUMMARY_METRICS_TEMPLATE = """
<div class="metrics-container">
    <div class="metric-card border-total">
        <div class="metric-label" style="color: {c_label_def};">総ロール数</div>
        <div class="metric-value" style="color: {c_val_def};">{total_rolls}
            <span class="metric-unit">回</span>
        </div>
    </div>
    <div class="metric-card border-succ">
        <div class="metric-label" style="color: {c_succ_lbl};">{m_succ_label}</div>
        <div class="metric-value" style="color: {c_succ_val};">{m_succ_val}</div>
        <div class="metric-sub">{m_succ_sub}</div>
    </div>
    <div class="metric-card border-cf">
        <div class="metric-label" style="color: {c_cf_lbl};">{m_cf_label}</div>
        <div class="metric-value" style="color: {c_cf_val};">{m_cf_val}</div>
        <div class="metric-sub">{m_cf_sub}</div>
    </div>
    <div class="metric-card border-crit">
        <div class="metric-label" style="color: {c_crit_lbl};">{m_crit_label}</div>
        <div class="metric-value" style="color: {c_crit_val};">{m_crit_val}</div>
        <div class="metric-sub">{m_crit_sub}</div>
    </div>
    <div class="metric-card border-fumb">
        <div class="metric-label" style="color: {c_fumb_lbl};">{m_fumb_label}</div>
        <div class="metric-value" style="color: {c_fumb_val};">{m_fumb_val}</div>
        <div class="metric-sub">{m_fumb_sub}</div>
    </div>
</div>
"""
TABLE_WRAPPER_TEMPLATE = """
<div class="dashboard-wrapper">
    <div class="table-scroll">
        <table class="custom-table">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
</div>
"""
TABLE_CELL_TEMPLATE = """
<td style="background-color: {bg_col}; color: {text_col}; {width_style} {font_weight}">{overlay_html}
    <div style="position: relative; z-index: 1;">{content_html}</div>
</td>
"""
CLEAN_TAGS_RE = re.compile(r'<[^>]+>')

# ==========================================
# 2. セル装飾・文字列整形の裏方関数群
# ==========================================
def _get_color_theme(label, selected_successes=None):
    """サマリー表のラベル（成功度）に応じたテーマ色セットを返す"""
    clean_label = CLEAN_TAGS_RE.sub('', str(label))
    base = clean_label.split('（')[0]
    
    if any(x in clean_label for x in ['成功率', '成功数', 'クリファン']): 
        return Colors.THEME_PURPLE
    if any(x in base for x in ['クリティカル', '決定的', '1クリ']):
        return Colors.THEME_CRIT
    elif any(x in base for x in ['ファンブル', '致命的', '100ファン']): 
        return Colors.THEME_FUMB
        
    if selected_successes is not None:
        if str(label) in selected_successes or clean_label in selected_successes:
            return Colors.THEME_SUCC
        else:
            return Colors.THEME_FAIL
            
    if '失敗' in base:
        return Colors.THEME_FAIL
    elif any(x in base for x in ['成功', 'スペシャル']):
        return Colors.THEME_SUCC
        
    return Colors.THEME_DEFAULT


def _get_header_html(col_name):
    """サマリー表のヘッダー用のHTMLを生成する"""
    if col_name == "総数": return "<div style='line-height: 1.3;'><b>総数</b></div>"
    if col_name in ["成功率", "成功数"]: return f"<div style='line-height: 1.3;'><b>{col_name}</b></div>"
    if col_name in ["クリファン率", "クリファン数", "クリファン"]: return "<div style='line-height: 1.3;'><b>クリ<br>ファン</b></div>"
    
    is_rescue = '（救済）' in col_name
    base = col_name.replace('（救済）', '')
    sub_text, sub_match = "", re.search(r'（(.*?)）', base)
    
    if sub_match:
        sub_text = sub_match.group(1).replace('イクストリーム', 'Ex').replace('ハード', 'ハード').replace('レギュラー', 'レギュ')
        base = base.replace(f'（{sub_match.group(1)}）', '')

    disp = {
        'クリティカル': 'クリ<br>ティカル', 
        'イクストリーム成功': 'Ex<br>成功', 
        'ハード成功': 'ハード<br>成功', 
        'レギュラー成功': 'レギュ<br>成功', 
        '決定的成功': '決定的<br>成功', 
        'スペシャル': 'スペ<br>シャル', 
        '致命的失敗': '致命的<br>失敗', 
        'ファンブル': 'ファン<br>ブル', 
        '決定的成功/スペシャル': '決定的<br><small>/スペ</small>'
    }.get(base, base)
    
    return f"<div style='white-space: normal; word-break: keep-all; overflow-wrap: anywhere; line-height: 1.3;'><b>{disp}</b>" \
            + (f"<br><small style='color: {Colors.SLATE_400};'>({sub_text})</small>" if sub_text else "") \
            + (f"<br><small style='color:#d63384;'>（救済）</small>" if is_rescue else "") + "</div>"


def _get_cell_style(col_key, row_data, bg_color, text_color, is_check_max, is_check_min, df_chars, sel_highlights, max_dict, min_dict, use_highlight, hl_basis):
    if not use_highlight or col_key not in sel_highlights: return bg_color, text_color, None
    basis = "回数" if col_key == "総数" else hl_basis
    target_raw_col = f'_raw_count_{col_key}' if basis == "回数" else f'_raw_pct_{col_key}'
    c_val = row_data[target_raw_col]
    if df_chars[target_raw_col].max() == df_chars[target_raw_col].min(): return bg_color, text_color, None
    c_max, c_min = max_dict[basis][col_key], min_dict[basis][col_key]
    if is_check_max and c_max is not None and c_max > 0 and c_val == c_max: return bg_color, Colors.YELLOW_900, Colors.YELLOW_500
    if is_check_min and c_min is not None and c_min != c_max and c_val == c_min: return bg_color, Colors.SLATE_700, Colors.SLATE_400
    return bg_color, text_color, None


def _format_cell_content(row, col_key, display_mode):
    cnt, pct = row[f'_raw_count_{col_key}'], row[f'_raw_pct_{col_key}']
    if row['総数'] == 0: return f"<span style='color:{Colors.SLATE_200};'>0</span>"
    cnt_html = f"<span style='display:inline-block;'>{cnt}</span><span style='display:inline-block; font-size:0.85em; color:{Colors.SLATE_400}; margin-left:2px;'>回</span>"
    pct_html = f"<span style='display:inline-block;'>{pct:.1f}</span><span style='display:inline-block; font-size:0.85em; margin-left:2px;'>%</span>"
    if col_key == "総数": return cnt_html
    if display_mode == "回数のみ": return cnt_html
    if display_mode == "パーセント（％）のみ": return pct_html
    return f"{pct_html}<br><span style='font-size: 0.8em; opacity: 0.7; display:inline-block; margin-top:2px; letter-spacing:0;'>( {cnt} 回 )</span>"


# ==========================================
# 3. HTML構築のメイン処理（UIから呼ばれる）
# ==========================================
def build_metrics_html(overall_data, display_mode, succ_col_name, cf_col_name):
    """全体のメトリクスカード（5つの四角）のHTMLを組み立てる"""
    total_rolls = overall_data['総数']
    succ_count = overall_data['succ_count']
    crit_count = overall_data['crit_count']
    fumb_count = overall_data['fumb_count']
    cf_count = overall_data['cf_count']

    succ_rate = (succ_count / total_rolls * 100) if total_rolls else 0
    cf_rate = (cf_count / total_rolls * 100) if total_rolls else 0
    crit_rate = (crit_count / total_rolls * 100) if total_rolls else 0
    fumb_rate = (fumb_count / total_rolls * 100) if total_rolls else 0

    if display_mode == "回数のみ":
        m_succ_label, m_succ_val, m_succ_sub = f"全体{succ_col_name}", f"{succ_count}<span class='metric-unit'>回</span>", ""
        m_cf_label, m_cf_val, m_cf_sub = f"全体{cf_col_name}", f"{cf_count}<span class='metric-unit'>回</span>", ""
        m_crit_label, m_crit_val, m_crit_sub = f"クリティカル数", f"{crit_count}<span class='metric-unit'>回</span>", ""
        m_fumb_label, m_fumb_val, m_fumb_sub = f"ファンブル数", f"{fumb_count}<span class='metric-unit'>回</span>", ""
    else:
        m_succ_label, m_succ_val, m_succ_sub = f"全体{succ_col_name}", f"{succ_rate:.1f}<span class='metric-unit'>%</span>", f"({succ_count} 回)"
        m_cf_label, m_cf_val, m_cf_sub = f"全体{cf_col_name}", f"{cf_rate:.1f}<span class='metric-unit'>%</span>", f"({cf_count} 回)"
        m_crit_label, m_crit_val, m_crit_sub = f"クリティカル率", f"{crit_rate:.1f}<span class='metric-unit'>%</span>", f"({crit_count} 回)"
        m_fumb_label, m_fumb_val, m_fumb_sub = f"ファンブル率", f"{fumb_rate:.1f}<span class='metric-unit'>%</span>", f"({fumb_count} 回)"

    return SUMMARY_METRICS_TEMPLATE.format(
        total_rolls=total_rolls,
        c_label_def=Colors.SLATE_400,
        c_val_def=Colors.SLATE_700,
        m_succ_label=m_succ_label, c_succ_lbl=Colors.GREEN_800,  m_succ_val=m_succ_val, c_succ_val=Colors.GREEN_900,  m_succ_sub=m_succ_sub,
        m_cf_label=m_cf_label,     c_cf_lbl=Colors.PURPLE_800, m_cf_val=m_cf_val,     c_cf_val=Colors.PURPLE_900, m_cf_sub=m_cf_sub,
        m_crit_label=m_crit_label, c_crit_lbl=Colors.AMBER_900,  m_crit_val=m_crit_val, c_crit_val=Colors.AMBER_950,  m_crit_sub=m_crit_sub,
        m_fumb_label=m_fumb_label, c_fumb_lbl=Colors.RED_800,    m_fumb_val=m_fumb_val, c_fumb_val=Colors.RED_900,    m_fumb_sub=m_fumb_sub
    )


def build_table_html(
        overall_data, df_chars, disp_keys, disp_labels, 
        selected_columns_keys, selected_successes, display_mode, 
        check_max, check_min, sel_highlights, 
        max_dict, min_dict, use_highlight, hl_basis):
    """サマリー内訳表のHTMLを組み立てる"""
    
    col_theme_cache = {}
    col_header_cache = {}
    for k, label in zip(disp_keys, disp_labels):
        if k in selected_columns_keys:
            display_label = "100<br>ファン" if label == "100ファン" else label
            h_bg, c_bg, c_text = _get_color_theme(label, selected_successes)
            col_theme_cache[k] = {"h_bg": h_bg, "c_bg": c_bg, "c_text": c_text}
            col_header_cache[k] = _get_header_html(display_label)

    headers_html = f'<th style="background: {Colors.SLATE_50};">キャラクター名</th>'
    for k, label in zip(disp_keys, disp_labels):
        if k in selected_columns_keys:
            theme = col_theme_cache[k]
            width_style = "min-width: 50px; width: 6%;" if k == "総数" else "min-width: 75px; width: auto;"
            headers_html += f'<th style="background: {theme["h_bg"]}; color: {theme["c_text"]}; padding: 8px 4px; {width_style}">{col_header_cache[k]}</th>'

    rows_html = ""
    
    # 全体（合計）行
    rows_html += f'<tr class="overall-row"><td class="char-name" style="background: {Colors.SLATE_50};">全体 (合計)</td>'
    for k, label in zip(disp_keys, disp_labels):
        if k in selected_columns_keys:
            theme = col_theme_cache[k]
            content = _format_cell_content(overall_data, k, display_mode)
            width_style = "min-width: 50px; width: 6%;" if k == "総数" else "min-width: 75px; width: auto;"
            rows_html += TABLE_CELL_TEMPLATE.format(bg_col=theme["c_bg"], text_col=theme["c_text"], width_style=width_style, font_weight="", overlay_html="", content_html=content)
    rows_html += '</tr>'

    # 各キャラクター行
    for _, row in df_chars.iterrows():
        rows_html += '<tr>'
        char_name_html = badges_coc.format_char_name_html(row["キャラクター名"], row["_orig_name"], row["_file_name"], mode="summary")
        rows_html += f'<td class="char-name" style="background: #ffffff;">{char_name_html}</td>'
        
        for k, label in zip(disp_keys, disp_labels):
            if k in selected_columns_keys:
                theme = col_theme_cache[k]
                bg_col, text_col, border_col = _get_cell_style(k, row, theme["c_bg"], theme["c_text"], check_max, check_min, df_chars, sel_highlights, max_dict, min_dict, use_highlight, hl_basis)
                
                font_weight = "font-weight: 800;" if border_col else ""
                if k == "cf_col": font_weight = "font-weight: 800;" if border_col else "font-weight: bold;"
                
                overlay = f"<div style='position: absolute; top: 0; left: 0; right: 0; bottom: 0; border: 2px solid {border_col}; pointer-events: none;'></div>" if border_col else ""
                content = _format_cell_content(row, k, display_mode)
                
                width_style = "min-width: 50px; width: 6%;" if k == "総数" else "min-width: 75px; width: auto;"
                rows_html += TABLE_CELL_TEMPLATE.format(bg_col=bg_col, text_col=text_col, width_style=width_style, font_weight=font_weight, overlay_html=overlay, content_html=content)
                
        rows_html += '</tr>'
    return TABLE_WRAPPER_TEMPLATE.format(headers_html=headers_html, rows_html=rows_html)