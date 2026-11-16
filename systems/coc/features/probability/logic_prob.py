import math
import pandas as pd

PCT_COL = "確率（％）"   # キャラごとの集計の、条件に当てはまった割合の列
SORT_BY_NAME = "キャラクター名"   # ほかのタブの並び替えと同じ名前
SORT_BASIS_OPTIONS = ["確率", "該当数", "総ロール数", SORT_BY_NAME]
# 並び替えの基準 → 並べる列（同じ値のキャラは次の列、それも同じなら名前順。元の表の順番で並びが変わらないように）
_SORT_COLUMNS = {
    "確率": [PCT_COL, "該当数"],
    "該当数": ["該当数", PCT_COL],
    "総ロール数": ["総ロール数", PCT_COL],
}

def wilson_interval(hits, total, z=1.96):
    """
    確率の95%信頼区間（ウィルソンの方法。回数が少なくても 0〜100% からはみ出さない）を (下限%, 上限%) で返す。
    例: 10回中3回 → 約 11〜60%。回数が少ないほど幅が広い＝偶然の影響が大きい
    """
    if not total:
        return 0.0, 0.0
    p = hits / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, center - half) * 100, min(1.0, center + half) * 100

def calc_char_stats(full_df, target_df, sort_basis, ascending):
    """キャラクターごとの確率データ（合計、該当数、確率）を計算し、指定順でソートする（ascending: 昇順か）"""
    if full_df.empty: 
        return pd.DataFrame()

    total_counts = full_df['キャラクター名'].value_counts()
    hit_counts = target_df['キャラクター名'].value_counts() if not target_df.empty else pd.Series(dtype=int)
    # キャラごとの最初のファイル名（キャラごとに全件を検索し直さないよう、先に1回で求める）
    first_file = full_df.drop_duplicates('キャラクター名').set_index('キャラクター名')['ファイル名'] \
        if 'ファイル名' in full_df.columns else {}
    char_stats = []

    # 1. キャラクターごとに集計
    for char, c_total in total_counts.items():
        c_hit = hit_counts.get(char, 0)
        file_name = first_file.get(char)   # ファイル名の列が無ければ {} なので None
        ci_low, ci_high = wilson_interval(c_hit, c_total)
        char_stats.append({
            "キャラクター名": char,
            PCT_COL: (c_hit / c_total * 100),
            "該当数": c_hit,
            "総ロール数": c_total,
            "_ci_low": ci_low,
            "_ci_high": ci_high,
            "_file_name": file_name
        })

    # 2. 指定された条件で並び替え（ソート）
    df_stats = pd.DataFrame(char_stats)
    if sort_basis == SORT_BY_NAME:
        return df_stats.sort_values(by=["キャラクター名"], ascending=ascending)
    if sort_basis in _SORT_COLUMNS:
        return df_stats.sort_values(by=_SORT_COLUMNS[sort_basis] + ["キャラクター名"], ascending=[ascending, ascending, True])
    return df_stats