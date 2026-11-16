import pandas as pd
from core.logic_base import NO_DICE_COL
from ...core import data_coc as data
from ...core import skills_coc as skills
from ...core import results_coc as results

# ==========================================
# 1. 検索・フィルタリング処理
# ==========================================
# 検索対象の選択肢（画面の選択肢の名前。この順に並べる）→ 探す列
SEARCH_ALL = "全体から"
SEARCH_TARGET_COLUMNS = {
    SEARCH_ALL: ['生ログ', 'キャラクター名', '統合前のキャラクター名', 'タブ', '結果', 'ファイル名'],
    "チャット本文のみ": ['生ログ'],
    "キャラクター名のみ": ['キャラクター名', '統合前のキャラクター名'],
    "タブのみ": ['タブ'],
    "結果のみ": ['結果'],
    "ファイル名のみ": ['ファイル名'],
}

LOGIC_NOT = "NOT"   # 「この語を含まない」（AND NOT）

# 一番下の並び順の選択肢
FINAL_SORT_TIME = "時系列 (ログの通り)"
FINAL_SORT_OPTIONS = [FINAL_SORT_TIME, "出目順"]

def apply_search_filters(df, search_terms):
    """ユーザーが設定した検索条件（AND/OR/NOT）に従ってデータフレームを絞り込む"""
    valid_terms = [t for t in search_terms if t["word"].strip()]
    if not valid_terms:
        return df

    mask = pd.Series(True, index=df.index)
    for i, term in enumerate(valid_terms):
        word = term["word"].strip()
        current_mask = pd.Series(False, index=df.index)
        for col in SEARCH_TARGET_COLUMNS.get(term.get("target", SEARCH_ALL), []):
            if col in df.columns:
                # regex=False: 「(」「.」「*」なども、記号としてそのまま探す
                current_mask |= df[col].astype(str).str.contains(word, case=False, na=False, regex=False)

        if term["logic"] == LOGIC_NOT:
            mask = mask & ~current_mask   # 1つ目が NOT なら「全体からその語を含むものを除く」
        elif i == 0:
            mask = current_mask
        elif term["logic"] == "AND":
            mask = mask & current_mask
        elif term["logic"] == "OR":
            mask = mask | current_mask

    return df[mask]


# ==========================================
# 2. 並べ替え・グループ化処理
# ==========================================
def _categorize_result(res):
    """その出目単体の結果で色分けする（BP内訳の括弧内＝ロール全体の結果は見ない）"""
    if results.is_crit(res): return "crit"
    if results.is_fumble(res): return "fumb"
    if "失敗" in str(results.primary_result(res)): return "fail"
    if results.is_actual_success(res): return "succ"
    return "none"

def process_and_sort_log(df, group_keys, final_sort, final_asc, recalc_rule, use_char_code_sort):
    """指定された階層と最終ソート順に従ってデータフレームを並び替える（並び替え用の列を足した、別の表を返す）"""
    if df.empty:
        return df

    df = df.copy(deep=False)   # 渡された表は書き換えない（pandas 3 では、足した列だけが増える）
    group_cols = [k["col"] for k in group_keys]
    if "結果" in group_cols:
        succ_order = {res: i for i, res in enumerate(data.CORE_RESULT_ORDER)}
        df['_succ_rank'] = df['結果'].map(succ_order).fillna(999)

    if "技能" in group_cols and not use_char_code_sort:
        df['_skill_rank'] = results.map_unique(df['判定名'], lambda s: skills.get_skill_sort_rank(s, recalc_rule))

    df['_res_category'] = results.map_unique(df['結果'], _categorize_result)
    
    sort_cols = []
    sort_ascs = []
    
    for gk in group_keys:
        if gk["col"] == "結果": 
            sort_cols.append('_succ_rank')
            sort_ascs.append(gk["asc"])
            # 並び順の一覧に無い結果（自動成功など）は同じ順位になるので、結果の名前でも並べて、同じ結果をまとめる
            sort_cols.append('結果')
            sort_ascs.append(gk["asc"])
        elif gk["col"] == "技能":
            if not use_char_code_sort: 
                sort_cols.append('_skill_rank')
                sort_ascs.append(gk["asc"])
            sort_cols.append('_clean_skill_name')
            sort_ascs.append(gk["asc"])
        else:
            sort_cols.append(gk["col"])
            sort_ascs.append(gk["asc"])

    if final_sort != FINAL_SORT_TIME and NO_DICE_COL in df.columns:
        sort_cols.append(NO_DICE_COL)   # ダイスを振っていない行（出目0）は、昇順でも降順でも末尾に回す
        sort_ascs.append(True)
    sort_cols.append('No' if final_sort == FINAL_SORT_TIME else '出目')
    sort_ascs.append(final_asc)
    if sort_cols[-1] != 'No':
        sort_cols.append('No')   # 同じ出目どうしは時系列順に並べる
        sort_ascs.append(True)

    return df.sort_values(by=sort_cols, ascending=sort_ascs, kind="stable")
