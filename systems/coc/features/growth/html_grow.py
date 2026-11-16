import html
import pandas as pd
from ...components.styles_coc import Colors
from ...components import badges_coc
from ...core import data_coc as data
from ...core import results_coc as results

# ==========================================
# 1. テンプレート群（デザイン・構造の骨組み）
# ==========================================

GROWTH_CSS = f"""
<style>
/* バッジの中の「( 3 )」 */
.badge-bracket {{ font-weight: normal; opacity: 0.6; margin: 0 3px; }}
.badge-val {{ font-size: 1.1em; }}

/* 成長画面専用レイアウト */
.growth-capture-box {{ background: {Colors.WHITE}; padding: 15px; border-radius: 8px; color: {Colors.SLATE_700}; }}
.growth-title-box {{ margin-bottom: 16px; padding: 12px 16px; background-color: {Colors.GREEN_50}; border: 1px solid {Colors.SLATE_200}; border-left: 6px solid {Colors.GREEN_500}; border-radius: 0 8px 8px 0; }}
.growth-title-main {{ font-size: 1.4rem; font-weight: 800; color: {Colors.GREEN_900}; }}
.growth-title-sub {{ font-size: 0.9em; color: {Colors.GREEN_800}; margin-top: 4px; font-weight: 600; }}

/* 技能ごとのカード（枠は styles_coc の .coc-card。確率集計の行と共通） */
.growth-header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}
.growth-skill {{ font-weight: 700; font-size: 1.15rem; overflow-wrap: anywhere; }}
.growth-target {{ font-size: 0.85em; color: {Colors.SLATE_400}; font-weight: normal; margin-left: 6px; }}
.growth-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; flex-grow: 1; }}

/* 詳細内訳部分 */
.growth-details {{ margin-top: 12px; padding-top: 12px; border-top: 1px dashed {Colors.SLATE_200}; font-size: 0.95rem; display: flex; flex-wrap: wrap; gap: 8px; }}
.detail-item {{ background-color: {Colors.SLATE_100}; border: 1px solid {Colors.SLATE_200}; padding: 4px 10px; border-radius: 6px; }}
.detail-val {{ font-weight: bold; margin-left: 4px; }}
.detail-unit {{ font-size: 0.85em; color: {Colors.SLATE_400}; margin-left: 2px; }}

/* ☑ の根拠になったロール */
.growth-basis {{ margin-top: 10px; font-size: 0.85rem; color: {Colors.SLATE_400}; font-family: monospace; line-height: 1.5; overflow-wrap: anywhere; }}
.growth-basis-more {{ font-family: sans-serif; }}
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
<div class="coc-card">
    <div class="growth-header">
        <div class="growth-skill">{check_mark} {safe_skill}{target_str}</div>
        <div class="growth-badges">{badges_html}</div>
    </div>
    {details_html}{basis_html}
</div>"""
GROWTH_DETAIL_ITEM = '<div class="detail-item">{res_name}:<span class="detail-val">{count}</span><span class="detail-unit">回</span></div>'
BASIS_SHOW_MAX = 3   # 根拠のロールは最初の3回まで表示する


# ==========================================
# 2. HTML構築のメイン（UIから呼ばれる関数）
# ==========================================

def _make_badge(label, val, cls_name):
    """個別のバッジHTML（例: 総数 ( 3 )）を生成する裏方"""
    return f"<span class='badge {cls_name}'>{label}<span class='badge-bracket'>(</span><span class='badge-val'>{val}</span><span class='badge-bracket'>)</span></span>"

def _basis_html(logs):
    """☑ の根拠になったロールの本文（多いときは最初の数回と残りの回数）"""
    if not logs:
        return ""
    lines = [f"☑ {html.escape(log)}" for log in logs[:BASIS_SHOW_MAX]]
    if len(logs) > BASIS_SHOW_MAX:
        lines.append(f"<span class='growth-basis-more'>ほか {len(logs) - BASIS_SHOW_MAX} 回</span>")
    return f'<div class="growth-basis">{"<br>".join(lines)}</div>'

def build_cards_html(char_df, selected_char, detail_mode, show_basis=False):
    """計算済みのデータフレームを受け取り、表示用のHTML文字列を組み立てる（show_basis: ☑ の根拠のロールを出すか）"""
    
    disp_char_html = badges_coc.format_char_name_html(selected_char, mode="growth_header")
    html_str = GROWTH_CSS + GROWTH_ROOT_HEADER.format(disp_char_html=disp_char_html)

    # iterrows は1行ずつ表を作るので遅い。itertuples は「_」で始まる列名を変えてしまうので辞書で回す
    for row in char_df.to_dict('records'):
        target_str = f"<span class='growth-target'>(目標値: {row['目標値']})</span>" \
            if pd.notna(row['目標値']) and row['目標値'] != "" else ""
        check_mark = "☑️" if row['チェック'] else "➖"
        
        # 長い技能名は CSS（overflow-wrap）で折り返すので、元の表記のまま表示する
        safe_skill = html.escape(row["技能名"])
        
        badges = [_make_badge("総数", row['総数'], "badge-total")]
        if row['合計成功数'] > 0: badges.append(_make_badge("成功", row['合計成功数'], "badge-succ"))
        if row['クリティカル'] > 0: badges.append(_make_badge("✨クリ", row['クリティカル'], "badge-crit"))
        if row['ファンブル'] > 0: badges.append(_make_badge("💀ファン", row['ファンブル'], "badge-fumb"))
        if row['初期値不明']: badges.append("<span class='badge badge-unknown' title='辞書にない技能のため、初期値以下の出目か判定できません'>❓初期値不明</span>")
        elif row['初期値以下'] > 0: badges.append(_make_badge("🌱初期値以下", row['初期値以下'], "badge-init"))
        
        details_html = ""
        if detail_mode != "表示しない":
            details = row['詳細内訳']
            sorted_res_names = [r for r in data.CORE_RESULT_ORDER if r in details] \
                                + [r for r in details if r not in data.CORE_RESULT_ORDER]
            
            filtered_details = [
                GROWTH_DETAIL_ITEM.format(res_name=html.escape(r), count=details[r])
                for r in sorted_res_names if not (detail_mode == "成功のみ表示" and not results.is_actual_success(r))
            ]
            if filtered_details: 
                details_html = f'<div class="growth-details">{"".join(filtered_details)}</div>'
                
        html_str += GROWTH_CARD_TEMPLATE.format(
            check_mark=check_mark,
            safe_skill=safe_skill,
            target_str=target_str,
            badges_html="".join(badges),
            details_html=details_html,
            basis_html=_basis_html(row['根拠ロール']) if show_basis else "",
        )
        
    html_str += '</div>'
    return html_str