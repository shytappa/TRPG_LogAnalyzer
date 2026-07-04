import html
from ...components import badges_coc

# ==========================================
# 1. テンプレート・スタイル定義
# ==========================================
LOG_CSS = """
<style>
.control-label { font-size: 0.9em; font-weight: bold; color: #475569; margin-bottom: 4px; }
.chat-container { background-color: #f8fafc; padding: 15px 20px; border-radius: 8px; border: 1px solid #e2e8f0; max-height: 800px; overflow-y: auto; font-family: sans-serif; }
.chat-message { margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px dashed #94a3b8; }
.chat-message:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
.chat-header { font-size: 0.9em; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: flex-end; gap: 10px; flex-wrap: nowrap; }
.header-info { flex: 1 1 auto; min-width: 0; line-height: 1.4; }
.chat-tab { color: #64748b; }
.chat-name { font-weight: bold; color: #334155; font-size: 1.05em; }
.header-badges { flex: 0 0 auto; display: flex; gap: 6px; justify-content: flex-end; align-items: center; }
.chat-body { font-size: 1.05rem; color: #1e293b; line-height: 1.4; word-break: break-all; font-family: monospace; }
.res-crit { color: #b45309; font-weight: bold; }
.res-succ { color: #047857; }
.res-fail { color: #475569; }
.res-fumb { color: #b91c1c; font-weight: bold; }
.group-divider { font-size: 0.85em; font-weight: bold; color: #64748b; background-color: #e2e8f0; padding: 4px 10px; border-radius: 4px; margin: 10px 0; display: inline-block;}
</style>
"""
CHAT_MESSAGE_TEMPLATE = """
<div class="chat-message">
    <div class="chat-header">
        <div class="header-info">
            <span class="chat-tab">{tab_name} 
                <span style="font-size:0.85em; opacity:0.7;">(📁 {file_name})</span>
            </span>
            <span class="chat-name">{char_html}</span>
        </div>
        <div class="header-badges">{badges_html}</div>
    </div>
    <div class="chat-body">{safe_log}</div>
</div>
"""

RES_CLASS_MAP = {
    "crit": ("res-crit", "badge-crit"),
    "fumb": ("res-fumb", "badge-fumb"),
    "succ": ("res-succ", "badge-succ"),
    "fail": ("res-fail", "badge-fail"),
    "none": ("res-none", "badge-total")
}

# ==========================================
# 2. メインのHTML構築処理
# ==========================================
def build_log_html(display_df, group_keys, max_heading_depth):
    """整理されたデータフレームから、表示用のHTML文字列を生成する"""
    html_parts = ['<div class="chat-container">']
    
    prev_group_vals = {}
    has_groups = len(group_keys) > 0
    check_depth = min(len(group_keys), max_heading_depth)

    for _, row in display_df.iterrows():
        res = row['結果']
        
        # グループ見出しの生成
        if has_groups:
            current_group_texts = []
            is_new_group = False
            for idx, gk in enumerate(group_keys):
                target_col = gk["col"]
                df_col = "判定名" if target_col == "技能" else target_col
                actual_val = res if target_col == "結果" else row[df_col]
                
                if idx < check_depth:
                    current_group_texts.append(str(actual_val))
                    if prev_group_vals.get(target_col) != actual_val:
                        is_new_group = True
                
                prev_group_vals[target_col] = actual_val
                
            if is_new_group and current_group_texts:
                html_parts.append(f'<div class="group-divider">▼ {" ＞ ".join(current_group_texts)}</div>')
        
        # バッジの生成
        res_cat = row.get('_res_category', 'none')
        res_class, badge_class = RES_CLASS_MAP.get(res_cat, ("res-none", "badge-total"))
        
        badges = []
        badges.append(f'<span class="badge {badge_class}">{res}</span>')
        if row.get('初期値不明', False): 
            badges.append('<span class="badge badge-unknown" title="判定不能">❓初期値不明</span>')
        elif row.get('is_under_init', False): 
            badges.append('<span class="badge badge-init">🌱初期値</span>')
        
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
            tab_name=row["タブ"],
            file_name=row["ファイル名"],
            char_html=char_html,
            badges_html=badges_html,
            safe_log=safe_log
        ))

    html_parts.append('</div>')
    
    return "".join(html_parts)