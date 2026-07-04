import re
import html
import pandas as pd
from ...components.styles_coc import Colors
from ...components import badges_coc
from ...core import data_coc as data
from ...core import utils_coc as utils

# ==========================================
# 1. テンプレート群（デザイン・構造の骨組み）
# ==========================================

GROWTH_CSS = f"""
<style>
/* バッジ */
.badge-bracket {{ font-weight: normal; opacity: 0.6; }}
.badge-val {{ font-size: 1.1em; }}

/* 成長画面専用レイアウト */
.growth-capture-box {{ background: white; padding: 15px; border-radius: 8px; font-family: sans-serif; }}
.growth-title-box {{ margin-bottom: 16px; padding: 12px 16px; background-color: {Colors.GREEN_50}; border: 1px solid {Colors.SLATE_200}; border-left: 6px solid {Colors.GREEN_500}; border-radius: 0 8px 8px 0; }}
.growth-title-main {{ font-size: 1.4rem; font-weight: 800; color: {Colors.GREEN_900}; }}
.growth-title-sub {{ font-size: 0.9em; color: {Colors.GREEN_800}; margin-top: 4px; font-weight: 600; }}

.growth-card {{ background-color: #ffffff; border: 1px solid {Colors.SLATE_200}; border-radius: 8px; padding: 12px 20px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); font-family: sans-serif;}}
.growth-header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}
.growth-skill {{ font-weight: 700; color: {Colors.SLATE_700}; font-size: 1.15rem; }}
.growth-target {{ font-size: 0.85em; color: {Colors.SLATE_400}; font-weight: normal; margin-left: 6px; }}
.growth-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; flex-grow: 1; }}

/* 詳細内訳部分 */
.growth-details {{ margin-top: 12px; padding-top: 12px; border-top: 1px dashed {Colors.SLATE_200}; font-size: 0.95rem; color: {Colors.SLATE_400}; display: flex; flex-wrap: wrap; gap: 8px; }}
.detail-item {{ background-color: {Colors.SLATE_100}; border: 1px solid {Colors.SLATE_200}; padding: 4px 10px; border-radius: 6px; }}
.detail-name {{ color: {Colors.SLATE_700}; }}
.detail-val {{ font-weight: bold; color: {Colors.SLATE_700}; display: inline-block; }}
.detail-unit {{ font-size: 0.85em; display: inline-block; letter-spacing: 0; }}
</style>
"""

GROWTH_ROOT_HEADER = """
<div id="capture-growth" class="growth-capture-box">
    <div class="growth-title-box">
        <div class="growth-title-main">👤 {disp_char_html}</div>
        <div class="growth-title-sub">📈 成長チェック一覧</div>
    </div>
"""
GROWTH_CARD_TEMPLATE = """
<div class="growth-card">
    <div class="growth-header">
        <div class="growth-skill">{check_mark} {safe_skill}{target_str}</div>
        <div class="growth-badges">{badges_html}</div>
    </div>
    {details_html}
</div>"""
GROWTH_DETAIL_ITEM = """
<div class="detail-item">
    <span class="detail-name">{res_name}:</span>&nbsp;
    <span class="detail-val">{count}</span>&nbsp;
    <span class="detail-unit">回</span>
</div>
"""


# ==========================================
# 2. HTML構築のメイン（UIから呼ばれる関数）
# ==========================================

def _make_badge(label, val, cls_name):
    """個別のバッジHTMLを生成する裏方"""
    return f"<span class='badge {cls_name}'>{label}&nbsp;<span class='badge-bracket'>(</span>&nbsp;<span class='badge-val'>{val}</span>&nbsp;<span class='badge-bracket'>)</span></span>"

def build_cards_html(char_df, selected_char, detail_mode):
    """計算済みのデータフレームを受け取り、表示用のHTML文字列を組み立てる"""
    
    disp_char_html = badges_coc.format_char_name_html(selected_char, mode="growth_header")
    html_str = GROWTH_CSS + GROWTH_ROOT_HEADER.format(disp_char_html=disp_char_html)

    for _, row in char_df.iterrows():
        target_str = f"<span class='growth-target'>(目標値: {row['目標値']})</span>" \
            if pd.notna(row['目標値']) and row['目標値'] != "" else ""
        check_mark = "☑️" if row['チェック'] else "➖"
        
        safe_skill = re.sub(
            r'\s+', ' ', 
            html.escape(row["技能名"])
                .replace("（", " ( ").replace("）", " ) ")
                .replace("(", " ( ").replace(")", " ) ")
                .replace("｛", " { ").replace("｝", " } ")
                .replace("{", " { ").replace("}", " } ")).strip() 
        
        badges = [_make_badge("総数", row['総数'], "badge-total")]
        if row['合計成功数'] > 0: badges.append(_make_badge("成功", row['合計成功数'], "badge-succ"))
        if row['クリティカル'] > 0: badges.append(_make_badge("✨クリ", row['クリティカル'], "badge-crit"))
        if row['ファンブル'] > 0: badges.append(_make_badge("💀ファン", row['ファンブル'], "badge-fumb"))
        if row['初期値不明']: badges.append("<span class='badge badge-unknown' title='辞書にない技能のため初期値成功が判定できません'>❓初期値不明</span>")
        elif row['初期値成功'] > 0: badges.append(_make_badge("🌱初期値", row['初期値成功'], "badge-init"))
        
        details_html = ""
        if detail_mode != "表示しない":
            details = row['詳細内訳']
            sorted_res_names = [r for r in data.CORE_RESULT_ORDER if r in details] \
                                + [r for r in details if r not in data.CORE_RESULT_ORDER]
            
            filtered_details = [
                GROWTH_DETAIL_ITEM.format(res_name=r, count=details[r])
                for r in sorted_res_names if not (detail_mode == "成功のみ表示" and not utils.is_actual_success(r))
            ]
            if filtered_details: 
                details_html = f'<div class="growth-details">{"".join(filtered_details)}</div>'
                
        html_str += GROWTH_CARD_TEMPLATE.format(
            check_mark=check_mark,
            safe_skill=safe_skill,
            target_str=target_str,
            badges_html="".join(badges),
            details_html=details_html
        )
        
    html_str += '</div>'
    return html_str