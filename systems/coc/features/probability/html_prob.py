from ...components.styles_coc import Colors
from ...components import badges_coc

# ==========================================
# 1. テンプレート群（デザイン・構造の骨組み）
# ==========================================
PROB_CSS = f"""
<style>
/* 確率画面専用のレイアウト設定 */
.prob-big-card {{ background-color: {Colors.GREEN_50}; padding: 25px; border-radius: 12px; border: 2px solid {Colors.GREEN_200}; box-shadow: 0 4px 6px rgba(22,101,52,0.05); text-align: center; }}
.prob-big-val {{ font-size: 4.5rem !important; font-weight: 900 !important; color: {Colors.GREEN_800} !important; line-height: 1.1; margin: 10px 0; }}
.prob-sub {{ font-size: 1.2rem !important; color: {Colors.GREEN_800} !important; font-weight: bold; }}
.prob-sub-small {{ font-size: 1.0rem !important; color: #15803d !important; font-weight: 600; }}
.prob-row-card {{ display: flex; align-items: center; background-color: #ffffff; border: 1px solid {Colors.SLATE_200}; border-radius: 8px; padding: 14px 20px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }}
.prob-row-name {{ flex: 0 0 35%; font-weight: 700; color: {Colors.SLATE_700}; font-size: 1.15rem; line-height: 1.3; word-break: break-word; padding-right: 15px; }} 
.prob-row-bar-bg {{ flex: 1 1 auto; background-color: {Colors.SLATE_100}; height: 16px; border-radius: 8px; margin: 0 15px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }} 
.prob-row-bar-fill {{ height: 100%; transition: width 0.5s ease; border-radius: 8px; }}
.prob-row-stats {{ flex: 0 0 auto; min-width: max-content; text-align: right; white-space: nowrap; margin-left: 10px; }}
.prob-row-pct {{ font-size: 1.7rem; font-weight: 800; }} 
.prob-row-sub {{ font-size: 0.95rem; color: {Colors.SLATE_400}; margin-left: 8px; font-weight: 500; letter-spacing: 0; }}
.prob-val-num {{ display: inline-block; padding-right: 2px; }}
.prob-val-pct {{ display: inline-block; font-size: 0.7em; }}
</style>
"""

PROB_ROOT_HEADER = """
<div id="capture-prob" style="background: #ffffff; padding: 20px; border-radius: 12px; font-family: sans-serif;">
    <div class="prob-big-card" style="margin-bottom: 20px;">
        <div class="prob-sub">{cond_text}</div>
        <div class="prob-big-val">
            <span style="display:inline-block; padding-right:4px;">{pct:.1f}</span>
            <span style="display:inline-block; font-size:0.6em;">%</span>
        </div>
        <div class="prob-sub-small">
            <span style="display:inline-block; letter-spacing:0;">( {matched} / {total_rolls} 回 )</span>
        </div>
    </div>
"""
PROB_ROW_CARD = """
<div class="prob-row-card">
    <div class="prob-row-name">{disp_name}</div>
    <div class="prob-row-bar-bg">
        <div class="prob-row-bar-fill" style="width: {stat_pct:.1f}%; background-color: {bar_color};"></div>
    </div>
    <div class="prob-row-stats">
        <span class="prob-row-pct" style="color: {pct_color};">
            <span class="prob-val-num">{stat_pct:.1f}</span>
            <span class="prob-val-pct">%</span>
        </span>
        <span class="prob-row-sub">
            <span class="prob-val-num">( {hit_count} / {total_count} 回 )</span>
        </span>
    </div>
</div>
"""


# ==========================================
# 2. HTML構築のメイン（UIから直接呼ばれる関数）
# ==========================================
def build_probability_html(cond_text, pct, matched, total_rolls, char_stats):
    """計算済みのデータを受け取り、表示用のHTML文字列を組み立てる"""
    
    # 全体確率のヘッダーを生成
    html_str = PROB_CSS + PROB_ROOT_HEADER.format(
        cond_text=cond_text, 
        pct=pct, 
        matched=matched, 
        total_rolls=total_rolls 
    )
    
    # 各キャラクターのカードを生成
    for _, stat in char_stats.iterrows():
        disp_name = badges_coc.format_char_name_html(
            stat["キャラクター名"], 
            file_name=stat.get("_file_name"), 
            mode="summary" 
        )
        
        bar_color = Colors.GREEN_500 if stat["確率（％）"] > 0 else "transparent"
        pct_color = Colors.GREEN_800 if stat["確率（％）"] > 0 else Colors.SLATE_400
        
        html_str += PROB_ROW_CARD.format(
            disp_name=disp_name,
            stat_pct=stat["確率（％）"],
            bar_color=bar_color,
            pct_color=pct_color,
            hit_count=stat["該当数"], 
            total_count=stat["総ロール数"] 
        )
        
    html_str += "</div></div>"
    return html_str