"""
「📉 パラメータ増減」タブの集計（ログからの読み取りと修正の見分け方は core/param_changes.py）。
自卓用のマッピングツールで保存した直しを当てる部分は systems/coc_shy/param_fixes.py（差し込み口 addon_coc.fix_param_changes から使う）
"""
import re
import pandas as pd

from core import logic_base, param_changes
from ...core import data_coc as data
from ..summary import logic_sum

RULES = param_changes.ParamRules(
    params=data.PARAM_NAMES,
    action_pattern="|".join(map(re.escape, data.PARAM_ACTION_WORDS)),
    threshold=data.PARAM_FIX_DISTANCE,
    outlier=data.PARAM_OUTLIER,
)

START, LOSS, GAIN, END = "開始", "減少", "回復", "終了"

def column_name(param, item):
    return f"{param} {item}"

START_END_COLUMNS = tuple(column_name(p, item) for p in data.PARAM_WITH_RECOVERY for item in (START, END))


def extract(file_dict):
    """読み込んだログ（ファイル名 → 中身）の、パラメータの変化の一覧（読み込んだ順。_seq の列がその順番）"""
    df = param_changes.extract_from_files(file_dict, RULES)
    return df.assign(_seq=range(len(df)))

def adjust_amounts(start, end, loss, gain, new_start, new_end):
    """
    開始・終了を直したときの、減少・回復（戻り値: (減少, 回復)）。
    直した方が多く減っていれば、その差を減少に足し、少なく減っていれば回復に足す
    （ロストでまとめて 0 にした分を戻すときなどは、減少を直接直す）
    """
    diff = (new_start - new_end) - (start - end)
    return (loss + diff, gain) if diff >= 0 else (loss, gain - diff)

def log_amounts(rows):
    """1つのパラメータの変化の行から (開始, 減少, 回復, 終了)（外れ値は減少・回復に数えない）"""
    valid = rows.loc[~rows["外れ値"].astype(bool), "変化"]
    return int(rows["前"].iloc[0]), int(-valid[valid < 0].sum()), int(valid[valid > 0].sum()), int(rows["後"].iloc[-1])

def norm_name(name):
    "名前の照合用（空白を除く）"
    return re.sub(r"\s+", "", str(name))

def select_characters(changes, params, name_rows=None):
    """
    数えるキャラだけにして、画面での名前に揃え、サイドバーで選んだファイル・キャラだけにし、キャラクターの統合・「ファイル名で区別」を反映する。
    name_rows: ロールの表（「ファイル名」「_log_name」（ログに書かれた名前）「キャラクター名」（画面での名前）の列）。
    その表にいるキャラだけを数え、名前をその表の「キャラクター名」にする（PLモードのPL名・表記ブレの統合など）。None ならそのまま
    """
    if changes.empty:
        return changes
    if name_rows is not None:
        pairs = name_rows.drop_duplicates(["ファイル名", "_log_name"])
        name_map = {(f, norm_name(n)): shown for f, n, shown in zip(pairs["ファイル名"], pairs["_log_name"], pairs["キャラクター名"])}
        shown_names = [name_map.get((f, norm_name(n))) for f, n in zip(changes["ファイル名"], changes["キャラクター名"])]
        changes = changes.assign(キャラクター名=shown_names)
        changes = changes[changes["キャラクター名"].notna()]
        if changes.empty:
            return changes
    sel = params.selector
    df = changes.assign(_file_char=changes["ファイル名"] + logic_base.KEY_SEP + changes["キャラクター名"])
    df = df[df["ファイル名"].isin(sel.sel_files) & df["_file_char"].isin(sel.sel_chars)]
    # キャラクターの統合で名前が変わる前の名前も残す（ロールの表と同じく。後から足す機能が名前に印を付けるときに使う）
    df = df.assign(統合前のキャラクター名=df["キャラクター名"])
    return logic_base.rename_characters(df, params).sort_values("_seq", kind="stable")

def summarize(df, fixes=None):
    """
    キャラごとの表（行: キャラクター名。列: 「SAN 開始」「SAN 減少」「SAN 回復」「SAN 終了」「HP 減少」…）。
    減った・回復は、修正をまとめた後の変化を足したもの（外れ値は除く）。開始・終了は、最初の変化の前・最後の変化の後の値。
    fixes: SAN の開始・終了の直し {キャラクター名: (開始 または None, 終了 または None)}。減少・回復は adjust_amounts で合わせる
    """
    fixes = fixes or {}
    records = {}
    for (char, param), g in df.groupby(["キャラクター名", "パラメータ"], sort=False):
        start, loss, gain, end = log_amounts(g)
        if param in data.PARAM_WITH_RECOVERY and char in fixes:
            new_start, new_end = fixes[char]
            new_start = start if new_start is None else int(new_start)
            new_end = end if new_end is None else int(new_end)
            loss, gain = adjust_amounts(start, end, loss, gain, new_start, new_end)
            start, end = new_start, new_end
        row = records.setdefault(char, {})
        if param in data.PARAM_WITH_RECOVERY:
            row.update({column_name(param, START): start, column_name(param, LOSS): loss,
                        column_name(param, GAIN): gain, column_name(param, END): end})
        else:
            row[column_name(param, LOSS)] = loss
    columns = [column_name(p, item) for p in data.PARAM_ORDER
               for item in ((START, LOSS, GAIN, END) if p in data.PARAM_WITH_RECOVERY else (LOSS,))]
    table = pd.DataFrame.from_dict(records, orient="index").reindex(columns=columns).astype("Int64")
    # 減少・回復は、記録が無ければ 0（変化していない）。開始・終了は、記録の無いキャラは空欄で、誰にも無ければ列ごと出さない
    amount_cols = [c for c in columns if is_amount_column(c)]
    table[amount_cols] = table[amount_cols].fillna(0)
    table = table.drop(columns=[c for c in START_END_COLUMNS if table[c].isna().all()])
    table.index.name = "キャラクター名"
    return table

SORT_BY_NAME = "キャラクター名"

def is_amount_column(col):
    """足し合わせられる列（減少・回復の量）か。開始・終了は値なので足さない"""
    return col.endswith((LOSS, GAIN))

def empty_columns(table):
    """全員が 0（か空欄）の列（最初は表示しない）"""
    return [c for c in table.columns if table[c].fillna(0).eq(0).all()]

def sort_table(table, key, ascending):
    """行の並び替え（キャラクター名か列の値。値の無いキャラは最後）"""
    if key == SORT_BY_NAME or key not in table.columns:
        return table.sort_index(ascending=ascending, kind="stable")
    return table.sort_values(key, ascending=ascending, na_position="last", kind="stable")

def totals(table):
    """全体の行。減った・回復した量だけ足す（開始・終了は空欄）"""
    return pd.Series({c: (table[c].sum() if is_amount_column(c) else pd.NA) for c in table.columns})


# マスの強調表示の設定（総合サマリーと共通。設定欄は components/highlight_coc）
HighlightConfig = logic_sum.HighlightConfig

# 強調するマス（列ごとの表で共通。出目の分布も使う）
highlight_marks = logic_sum.table_highlight_marks

def outliers(df):
    """集計から外した変化（1回で大きく動きすぎたもの）"""
    return df[df["外れ値"].astype(bool)] if not df.empty else df
