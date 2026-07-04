class Colors:
    """アプリ全体で使うカラーパレット（Tailwind CSS準拠の命名）"""
    # ==========================================
    # 1. ベースパレット（原色）
    # ==========================================
    # Slate (グレー系: 基本テキスト・失敗・枠線)
    SLATE_50  = "#f8fafc"
    SLATE_100 = "#f1f5f9"
    SLATE_200 = "#e2e8f0"
    SLATE_400 = "#94a3b8"
    SLATE_700 = "#334155"

    # Amber/Yellow (黄・オレンジ系: クリティカル・最大値ハイライト)
    AMBER_50  = "#fffbeb"
    AMBER_100 = "#fef3c7"
    AMBER_200 = "#fde68a"
    AMBER_600 = "#d97706"
    AMBER_900 = "#92400e"
    AMBER_950 = "#78350f"
    YELLOW_500 = "#eab308"
    YELLOW_900 = "#713f12"

    # Red (赤系: ファンブル)
    RED_50  = "#fef2f2"
    RED_100 = "#fee2e2"
    RED_200 = "#fecaca"
    RED_600 = "#dc2626"
    RED_800 = "#991b1b"
    RED_900 = "#7f1d1d"

    # Green (緑系: 成功)
    GREEN_50  = "#f0fdf4"
    GREEN_100 = "#dcfce7"
    GREEN_200 = "#bbf7d0"
    GREEN_500 = "#10b981"
    GREEN_600 = "#059669"
    GREEN_800 = "#166534"
    GREEN_900 = "#064e3b"

    # Purple (紫系: サマリーのクリファン合算など)
    PURPLE_50  = "#faf5ff"
    PURPLE_100 = "#f3e8ff"
    PURPLE_200 = "#e9d5ff"
    PURPLE_600 = "#7c3aed"
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
    THEME_DEFAULT = (SLATE_50, "#ffffff", SLATE_700)


class Templates:
    """Pythonコード内で使い回すHTMLの骨組み"""
    FILTER_HEADER = f"font-weight:bold; margin-top:6px; color: {Colors.SLATE_700};"

# ==========================================
# 3. CoC専用のグローバルCSS
# ==========================================
COC_GLOBAL_CSS = f"""
<style>
/* 共通パーツ (Export UI) */
.export-btn {{ background-color: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: 0.2s; }}

/* バッジのデザイン */
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 6px; font-size: 0.85em; font-weight: bold; text-align: center; white-space: nowrap; margin-bottom: 2px;}}
.badge-total {{ background-color: {Colors.SLATE_100}; color: {Colors.SLATE_700}; border: 1px solid {Colors.SLATE_200}; }} 
.badge-crit {{ background-color: {Colors.AMBER_100}; color: {Colors.AMBER_900}; border: 1px solid {Colors.AMBER_200}; }}
.badge-succ {{ background-color: {Colors.GREEN_100}; color: {Colors.GREEN_800}; border: 1px solid {Colors.GREEN_200}; }}
.badge-fail {{ background-color: {Colors.SLATE_100};  color: {Colors.SLATE_700}; border: 1px solid {Colors.SLATE_200}; }}
.badge-fumb {{ background-color: {Colors.RED_100}; color: {Colors.RED_800}; border: 1px solid {Colors.RED_200}; }}
.badge-unknown {{ background-color: {Colors.AMBER_200}33; color: {Colors.YELLOW_900}; border: 1px dashed {Colors.YELLOW_500}; }}
.badge-init {{ background-color: #e0f2fe; color: #0369a1; border: 1px dashed #7dd3fc; }}
.badge-name-main {{ letter-spacing: 0; }}
.badge-name-sub {{ color: #94a3b8; font-weight: normal; letter-spacing: 0; }}
.badge-sub-summary {{ font-size: 0.8em; }}
.badge-sub-growth  {{ font-size: 0.7em; margin-left: 8px; }}
.badge-sub-log     {{ font-size: 0.8em; margin-left: 4px; }}
</style>
"""