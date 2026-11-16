import html
from ...components import badges_coc
from ...components.styles_coc import Colors

# ==========================================
# 1. テンプレート・スタイル定義
# ==========================================
LOG_CSS = f"""
<style>
.chat-container {{ background-color: {Colors.SLATE_50}; color: {Colors.SLATE_800}; padding: 15px 20px; border-radius: 8px; border: 1px solid {Colors.SLATE_200}; max-height: 800px; overflow-y: auto; }}
.chat-message {{ margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px dashed {Colors.SLATE_400}; }}
.chat-message:last-child {{ margin-bottom: 0; padding-bottom: 0; border-bottom: none; }}
.chat-header {{ font-size: 0.9em; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: flex-end; gap: 10px; }}
.header-info {{ flex: 1 1 auto; min-width: 0; line-height: 1.4; }}
.chat-tab {{ color: {Colors.SLATE_500}; }}
.chat-file {{ font-size: 0.85em; opacity: 0.7; }}
.chat-name {{ font-weight: bold; color: {Colors.SLATE_700}; font-size: 1.05em; }}
.header-badges {{ flex: 0 0 auto; display: flex; gap: 6px; align-items: center; }}
.chat-body {{ font-size: 1.05rem; color: {Colors.SLATE_800}; line-height: 1.4; word-break: break-all; font-family: monospace; }}
.res-crit {{ color: {Colors.AMBER_700}; font-weight: bold; }}
.res-succ {{ color: {Colors.GREEN_700}; }}
.res-fail {{ color: {Colors.SLATE_600}; }}
.res-fumb {{ color: {Colors.RED_700}; font-weight: bold; }}
.group-divider {{ font-size: 0.85em; font-weight: bold; color: {Colors.SLATE_500}; background-color: {Colors.SLATE_200}; padding: 4px 10px; border-radius: 4px; margin: 10px 0; display: inline-block;}}
</style>
"""
CHAT_MESSAGE_TEMPLATE = """
<div class="chat-message">
    <div class="chat-header">
        <div class="header-info">
            <span class="chat-tab">{tab_name} <span class="chat-file">(📁 {file_name})</span></span>
            <span class="chat-name">{char_html}</span>
        </div>
        <div class="header-badges">{badges_html}</div>
    </div>
    <div class="chat-body">{safe_log}</div>
</div>
"""

# 結果の分類 → (本文の結果部分の文字色クラス, 結果バッジのクラス)
RES_CLASS_MAP = {
    "crit": ("res-crit", "badge-crit"),
    "fumb": ("res-fumb", "badge-fumb"),
    "succ": ("res-succ", "badge-succ"),
    "fail": ("res-fail", "badge-fail"),
    "none": ("", "badge-total")
}
# グループ化の選択肢 → 見出しに使う列（技能は「#1」などを除いた技能名でまとめる）
GROUP_HEADING_COLUMNS = {"技能": "_clean_skill_name"}

# ==========================================
# 2. メインのHTML構築処理
# ==========================================
def build_log_html(display_df, group_keys, max_heading_depth):
    """整理されたデータフレームから、表示用のHTML文字列を生成する"""
    html_parts = ['<div class="chat-container">']
    
    prev_group_vals = {}
    has_groups = len(group_keys) > 0
    check_depth = min(len(group_keys), max_heading_depth)

    # iterrows は1行ずつ表を作るので遅い。itertuples は「_」で始まる列名を変えてしまうので辞書で回す
    for row in display_df.to_dict('records'):
        res = row['結果']
        
        # グループ見出しの生成
        if has_groups:
            current_group_texts = []
            is_new_group = False
            for idx, gk in enumerate(group_keys):
                target_col = gk["col"]
                actual_val = row[GROUP_HEADING_COLUMNS.get(target_col, target_col)]
                
                if idx < check_depth:
                    current_group_texts.append(str(actual_val))
                    if prev_group_vals.get(target_col) != actual_val:
                        is_new_group = True
                
                prev_group_vals[target_col] = actual_val
                
            if is_new_group and current_group_texts:
                html_parts.append(f'<div class="group-divider">▼ {html.escape(" ＞ ".join(current_group_texts))}</div>')
        
        # バッジの生成
        res_cat = row.get('_res_category', 'none')
        res_class, badge_class = RES_CLASS_MAP.get(res_cat, RES_CLASS_MAP["none"])
        
        badges = []
        badges.append(f'<span class="badge {badge_class}">{html.escape(str(res))}</span>')
        if row.get('_init_unknown', False): 
            badges.append('<span class="badge badge-unknown" title="判定不能">❓初期値不明</span>')
        elif row.get('_is_under_init', False): 
            badges.append('<span class="badge badge-init">🌱初期値以下</span>')
        
        # チャット本文の装飾とエスケープ
        safe_log = html.escape(row['生ログ'])
        last_gt_idx = safe_log.rfind('＞')
        if last_gt_idx != -1:
            prefix = safe_log[:last_gt_idx + 1]
            raw_res_text = safe_log[last_gt_idx + 1:]
            safe_log = f'{prefix}<span class="{res_class}">{raw_res_text}</span>'
        
        # キャラクター名の整形
        char_html = badges_coc.format_char_name_html(
            row['キャラクター名'], 
            row.get('統合前のキャラクター名', ''), 
            file_name=row['ファイル名'],
            mode="log"
        )
        
        badges_html = "".join(badges)
        
        html_parts.append(CHAT_MESSAGE_TEMPLATE.format(
            tab_name=html.escape(str(row["タブ"])),
            file_name=html.escape(str(row["ファイル名"])),
            char_html=char_html,
            badges_html=badges_html,
            safe_log=safe_log
        ))

    html_parts.append('</div>')
    
    return "".join(html_parts)