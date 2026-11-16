# ==========================================
# 1. 色の定義
# ==========================================
class Colors:
    """アプリ全体で使うカラーパレット（Tailwind CSS準拠の命名）"""
    # ==========================================
    # 1. ベースパレット（原色）
    # ==========================================
    WHITE = "#ffffff"   # カード・表・画像の背景

    # Slate (グレー系: 基本テキスト・失敗・枠線)
    SLATE_50  = "#f8fafc"
    SLATE_100 = "#f1f5f9"
    SLATE_200 = "#e2e8f0"
    SLATE_300 = "#cbd5e1"
    SLATE_400 = "#94a3b8"
    SLATE_500 = "#64748b"
    SLATE_600 = "#475569"
    SLATE_700 = "#334155"
    SLATE_800 = "#1e293b"

    # Amber/Yellow (黄・オレンジ系: クリティカル・最大値ハイライト)
    AMBER_50  = "#fffbeb"
    AMBER_100 = "#fef3c7"
    AMBER_200 = "#fde68a"
    AMBER_500 = "#f59e0b"
    AMBER_700 = "#b45309"
    AMBER_900 = "#92400e"
    AMBER_950 = "#78350f"
    YELLOW_500 = "#eab308"
    YELLOW_900 = "#713f12"

    # Red (赤系: ファンブル)
    RED_50  = "#fef2f2"
    RED_100 = "#fee2e2"
    RED_200 = "#fecaca"
    RED_500 = "#ef4444"
    RED_700 = "#b91c1c"
    RED_800 = "#991b1b"
    RED_900 = "#7f1d1d"

    # Sky (水色系: 初期値バッジ、画像保存・コピーのボタン)
    SKY_50  = "#f0f9ff"
    SKY_100 = "#e0f2fe"
    SKY_200 = "#bae6fd"
    SKY_300 = "#7dd3fc"
    SKY_700 = "#0369a1"

    # Pink (救済)
    PINK_600 = "#d63384"

    # Green (緑系: 成功)
    GREEN_50  = "#f0fdf4"
    GREEN_100 = "#dcfce7"
    GREEN_200 = "#bbf7d0"
    GREEN_500 = "#10b981"
    GREEN_600 = "#059669"
    GREEN_700 = "#047857"
    GREEN_800 = "#166534"
    GREEN_900 = "#064e3b"

    # Purple (紫系: サマリーのクリファン合算など)
    PURPLE_50  = "#faf5ff"
    PURPLE_100 = "#f3e8ff"
    PURPLE_500 = "#8b5cf6"
    PURPLE_800 = "#6b21a8"
    PURPLE_900 = "#4c1d95"

    # ==========================================
    # 2. テーマパレット（用途に合わせて原色を組み合わせる）
    # ==========================================
    THEME_CRIT    = (AMBER_100, AMBER_50, AMBER_900)
    THEME_FUMB    = (RED_100, RED_50, RED_800)
    THEME_SUCC    = (GREEN_100, GREEN_50, GREEN_800)
    THEME_FAIL    = (SLATE_100, SLATE_50, SLATE_700)
    THEME_PURPLE  = (PURPLE_100, PURPLE_50, PURPLE_800)
    THEME_SKY     = (SKY_100, SKY_50, SKY_700)


# ==========================================
# 2. 画像保存・コピーのボタン（st.iframe の中に表示するので、そのページ用のCSSを丸ごと持つ）
# ==========================================
ACTION_BUTTON_CSS = f"""
<style>
    /* ブラウザ既定の余白や、幅の狭い画面での文字のはみ出しで、スクロールバーが出ないようにする */
    html, body {{ margin: 0; overflow: hidden; }}
    .action-btn {{
        /* 高さを決めておく（絵文字のフォントによって行の高さが変わり、枠（42px）からはみ出してスクロールできてしまうため） */
        box-sizing: border-box;
        height: 38px;
        line-height: 20px;
        background-color: {Colors.SKY_50};
        border: 1px solid {Colors.SKY_200};
        color: {Colors.SKY_700};
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        font-weight: 600;
        border-radius: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        font-family: sans-serif;
        display: block;   /* 文字の行の下に隙間ができないようにする（できると枠からはみ出す） */
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;   /* 入りきらない文字は「…」で省略 */
    }}
    .action-btn:hover {{ background-color: {Colors.SKY_100}; border-color: {Colors.SKY_300}; }}
    .action-btn:active {{ transform: translateY(1px); }}
    .action-btn.success {{ background-color: {Colors.GREEN_500}; color: {Colors.WHITE}; border-color: {Colors.GREEN_600}; }}
</style>
"""

# ==========================================
# 3. CoC専用のグローバルCSS
# ==========================================
COC_GLOBAL_CSS = f"""
<style>
/* バッジのデザイン */
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 0.85em; font-weight: bold; text-align: center; white-space: nowrap; margin-bottom: 2px;}}
.badge-total, .badge-fail {{ background-color: {Colors.SLATE_100}; color: {Colors.SLATE_700}; border: 1px solid {Colors.SLATE_200}; }}
.badge-crit {{ background-color: {Colors.AMBER_100}; color: {Colors.AMBER_900}; border: 1px solid {Colors.AMBER_200}; }}
.badge-succ {{ background-color: {Colors.GREEN_100}; color: {Colors.GREEN_800}; border: 1px solid {Colors.GREEN_200}; }}
.badge-fumb {{ background-color: {Colors.RED_100}; color: {Colors.RED_800}; border: 1px solid {Colors.RED_200}; }}
.badge-unknown {{ background-color: {Colors.AMBER_200}33; color: {Colors.YELLOW_900}; border: 1px dashed {Colors.YELLOW_500}; }}
.badge-init {{ background-color: {Colors.SKY_100}; color: {Colors.SKY_700}; border: 1px dashed {Colors.SKY_300}; }}
.badge-name-sub {{ color: {Colors.SLATE_400}; font-weight: normal; }}
.badge-sub-summary {{ font-size: 0.8em; }}
.badge-sub-growth  {{ font-size: 0.7em; margin-left: 8px; }}
.badge-sub-log     {{ font-size: 0.8em; margin-left: 4px; }}

/* 確率集計のキャラごとの行と、成長チェックの技能ごとのカードで共通の枠（中の並べ方は各画面で指定） */
.coc-card {{ background-color: {Colors.WHITE}; border: 1px solid {Colors.SLATE_200}; border-radius: 8px; padding: 12px 20px; margin-bottom: 10px; }}

/* 見出しの「ℹ️ 使い方」ボタン（app_coc._render_header）：狭い画面でも折り返さず、入りきらない分は「…」にする */
.st-key-manual_button button {{ min-width: 0; padding-left: 0.5rem; padding-right: 0.5rem; }}
.st-key-manual_button button div,
.st-key-manual_button button p {{ min-width: 0; max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
</style>
"""