import html
from ...components.styles_coc import Colors
from ...components import badges_coc
from . import logic_prob

# ==========================================
# 1. テンプレート群（デザイン・構造の骨組み）
# ==========================================
PROB_CSS = f"""
<style>
#capture-prob {{ background: {Colors.WHITE}; padding: 20px; border-radius: 12px; color: {Colors.SLATE_700}; }}
/* 全体の確率（上の大きいカード） */
.prob-big-card {{ background-color: {Colors.GREEN_50}; padding: 25px; border-radius: 12px; border: 2px solid {Colors.GREEN_200}; text-align: center; margin-bottom: 20px; color: {Colors.GREEN_800}; }}
.prob-big-val {{ font-size: 4.5rem; font-weight: 900; line-height: 1.1; margin: 10px 0; }}
.prob-sub {{ font-size: 1.2rem; font-weight: bold; }}
.prob-sub-small {{ font-size: 1.0rem; font-weight: 600; }}
/* キャラクターごとの行（枠は styles_coc の .coc-card。成長チェックのカードと共通） */
.prob-row-card {{ display: flex; align-items: center; padding: 14px 20px; }}
.prob-row-name {{ flex: 0 0 35%; font-weight: 700; font-size: 1.15rem; line-height: 1.3; word-break: break-word; padding-right: 15px; }}
.prob-row-bar-bg {{ flex: 1 1 auto; background-color: {Colors.SLATE_100}; height: 16px; border-radius: 8px; margin: 0 15px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); position: relative; }}
.prob-row-bar-fill {{ height: 100%; border-radius: 8px; position: relative; }}
/* 95%信頼区間（バーの上に重ねる薄い帯） */
.prob-row-ci {{ position: absolute; top: 3px; bottom: 3px; border: 2px solid {Colors.GREEN_800}; border-radius: 4px; background: {Colors.GREEN_200}66; }}
.prob-ci-text {{ font-size: 0.85rem; color: {Colors.SLATE_400}; font-weight: 500; }}
.prob-row-stats {{ flex: 0 0 auto; text-align: right; white-space: nowrap; margin-left: 10px; }}
.prob-row-pct {{ font-size: 1.7rem; font-weight: 800; }}
.prob-row-sub {{ font-size: 0.95rem; color: {Colors.SLATE_400}; margin-left: 8px; font-weight: 500; }}
/* 「%」を数字より小さく */
.pct-unit {{ font-size: 0.65em; margin-left: 2px; }}
</style>
"""

PROB_ROOT_HEADER = """
<div id="capture-prob">
    <div class="prob-big-card">
        <div class="prob-sub">{cond_text}</div>{cmd_html}
        <div class="prob-big-val">{pct:.1f}<span class="pct-unit">%</span></div>
        <div class="prob-sub-small">( {matched} / {total_rolls} 回 ){ci_html}</div>
    </div>
"""
PROB_ROW_CARD = """
<div class="coc-card prob-row-card">
    <div class="prob-row-name">{disp_name}</div>
    <div class="prob-row-bar-bg">
        <div class="prob-row-bar-fill" style="width: {stat_pct:.1f}%; background-color: {bar_color};"></div>{ci_bar}
    </div>
    <div class="prob-row-stats">
        <span class="prob-row-pct" style="color: {pct_color};">{stat_pct:.1f}<span class="pct-unit">%</span></span>
        <span class="prob-row-sub">( {hit_count} / {total_count} 回 )</span>{ci_html}
    </div>
</div>
"""
CI_BAR = '<div class="prob-row-ci" style="left: {low:.1f}%; width: {width:.1f}%;" title="95%信頼区間"></div>'
CI_TEXT = '<br><span class="prob-ci-text">95%区間 {low:.1f}〜{high:.1f}%</span>'


# ==========================================
# 2. HTML構築のメイン（UIから直接呼ばれる関数）
# ==========================================
def build_probability_html(cond_text, pct, matched, total_rolls, char_stats, overall_ci=None, show_ci=False, cmd_notes=()):
    """
    計算済みのデータを受け取り、表示用のHTML文字列を組み立てる
    overall_ci: 全体の95%信頼区間 (下限, 上限) / cmd_notes: ダイスコマンドの条件の説明（条件の下に小さく出す）
    """
    cmd_html = f'<div class="prob-sub-small">{html.escape(" ｜ ".join(cmd_notes))}</div>' if cmd_notes else ""

    # 全体確率のヘッダーを生成
    html_str = PROB_CSS + PROB_ROOT_HEADER.format(
        cond_text=html.escape(cond_text),
        cmd_html=cmd_html,
        pct=pct,
        matched=matched,
        total_rolls=total_rolls,
        ci_html=CI_TEXT.format(low=overall_ci[0], high=overall_ci[1]) if overall_ci else "",
    )

    # 各キャラクターのカードを生成（iterrows は1行ずつ表を作るので遅い。itertuples は「_」で始まる列名を変えてしまうので辞書で回す）
    for stat in char_stats.to_dict('records'):
        disp_name = badges_coc.format_char_name_html(
            stat["キャラクター名"],
            file_name=stat.get("_file_name"),
            mode="summary"
        )

        bar_color = Colors.GREEN_500 if stat[logic_prob.PCT_COL] > 0 else "transparent"
        pct_color = Colors.GREEN_800 if stat[logic_prob.PCT_COL] > 0 else Colors.SLATE_400

        html_str += PROB_ROW_CARD.format(
            disp_name=disp_name,
            stat_pct=stat[logic_prob.PCT_COL],
            bar_color=bar_color,
            pct_color=pct_color,
            hit_count=stat["該当数"],
            total_count=stat["総ロール数"],
            ci_bar=CI_BAR.format(low=stat["_ci_low"], width=stat["_ci_high"] - stat["_ci_low"]) if show_ci else "",
            ci_html=CI_TEXT.format(low=stat["_ci_low"], high=stat["_ci_high"]) if show_ci else "",
        )

    html_str += "</div>"  # capture-prob を閉じる
    return html_str
