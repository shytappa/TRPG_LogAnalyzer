"""「🎯 出目の分布」タブの集計（キャラごとに、出目が 1〜10、11〜20、… のどこに何回入ったか）"""
import pandas as pd
from ...core.logic_coc import first_row_of_each_roll
from ..summary import logic_sum

WIDTHS = (10, 5)        # 区切りの幅の選択肢
TOTAL = "総数"
MEAN = "平均出目"
MEAN_EXPECTED = 50.5    # 1〜100 が同じ確率で出るときの平均
# 表示形式（区切りのマスの中身）は総合サマリーと同じ選択肢・順番
UNIT_BOTH, UNIT_PCT, UNIT_COUNT = logic_sum.DISPLAY_BOTH, logic_sum.DISPLAY_PCT, logic_sum.DISPLAY_COUNT
UNITS = tuple(logic_sum.DISPLAY_OPTIONS)
SORT_BY_NAME = "名前"


def bin_labels(width):
    """区切りの列名（「1〜10」「11〜20」…「91〜100」）"""
    return [f"{lo}〜{lo + width - 1}" for lo in range(1, 101, width)]

def expected_pct(width):
    """1〜100 が同じ確率で出るときの、1つの区切りの割合（％）"""
    return float(width)

def _valid_rolls(df):
    """数える出目の行と出目。組み合わせロール（目標値ごとに行がある）は、出目は1回なので1行だけ数える"""
    df = first_row_of_each_roll(df)
    rolls = pd.to_numeric(df["出目"], errors="coerce")
    ok = rolls.between(1, 100)
    return df[ok], rolls[ok].astype(int)

def distribution(df, width, by="キャラクター名"):
    """
    by の列（キャラクター名など）ごとの、区切りごとの回数の表。
    列: 総数, 平均出目, 「1〜10」…（回数）。1〜100 以外の出目は数えない
    """
    labels = bin_labels(width)
    rows, rolls = _valid_rolls(df)
    if rows.empty:
        return pd.DataFrame(columns=[TOTAL, MEAN] + labels)
    bins = (rolls - 1) // width
    counts = pd.crosstab(rows[by], bins).reindex(columns=range(len(labels)), fill_value=0)
    counts.columns = labels
    table = pd.concat([rolls.groupby(rows[by]).size().rename(TOTAL), rolls.groupby(rows[by]).mean().rename(MEAN), counts], axis=1)
    table.index.name = by
    return table

def overall(df, width, label=logic_sum.OVERALL_LABEL):   # 行の名前は、総合サマリーなどの全体の行と同じ
    """全体（全員の合計）の1行の表（distribution と同じ列。行の名前は label）"""
    return distribution(df.assign(_all=label), width, by="_all")

def bin_columns(table):
    return [c for c in table.columns if c not in (TOTAL, MEAN)]

def percentages(table):
    """区切りの列を、総数に対する割合（％）にした表（総数が 0 の行は空欄）"""
    cols = bin_columns(table)
    out = table.astype({c: float for c in cols})
    out[cols] = table[cols].div(table[TOTAL].where(table[TOTAL] > 0), axis=0) * 100
    return out

def sort_table(table, key, ascending):
    """並び替え（名前か列の値。名前は index の順）"""
    if key == SORT_BY_NAME or key not in table.columns:
        return table.sort_index(ascending=ascending, kind="stable")
    return table.sort_values(key, ascending=ascending, na_position="last", kind="stable")

def deviation(pct, width):
    """区切りの割合が、偏りの無いときの割合からどれだけ離れているか（−1〜。0 で期待どおり、1 で期待の2倍）"""
    return pct / expected_pct(width) - 1
