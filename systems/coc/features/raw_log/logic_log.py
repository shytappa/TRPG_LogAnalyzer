import pandas as pd
from ...core import data_coc as data
from ...core import utils_coc as utils

# ==========================================
# 1. 検索・フィルタリング処理
# ==========================================
def apply_search_filters(df, search_terms):
    """ユーザーが設定した検索条件（AND/OR）に従ってデータフレームを絞り込む"""
    valid_terms = [t for t in search_terms if t["word"].strip()]
    if not valid_terms:
        return df

    mask = pd.Series(True, index=df.index)
    has_orig_name = '統合前のキャラクター名' in df.columns
    empty_series = pd.Series("", index=df.index)

    for i, term in enumerate(valid_terms):
        word = term["word"].strip()
        tgt = term.get("target", "全体から")
        
        orig_name_col = df['統合前のキャラクター名'] if has_orig_name else empty_series

        if tgt == "全体から":
            current_mask = (
                df['生ログ'].str.contains(word, case=False, na=False) | 
                df['キャラクター名'].str.contains(word, case=False, na=False) | 
                orig_name_col.str.contains(word, case=False, na=False) | 
                df['タブ'].str.contains(word, case=False, na=False) | 
                df['結果'].str.contains(word, case=False, na=False) | 
                df['ファイル名'].str.contains(word, case=False, na=False)
            )
        elif tgt == "チャット本文のみ":
            current_mask = df['生ログ'].str.contains(word, case=False, na=False)
        elif tgt == "キャラクター名のみ":
            current_mask = (
                df['キャラクター名'].str.contains(word, case=False, na=False) | 
                orig_name_col.str.contains(word, case=False, na=False)
            )
        elif tgt == "タブのみ":
            current_mask = df['タブ'].str.contains(word, case=False, na=False)
        elif tgt == "結果のみ":
            current_mask = df['結果'].str.contains(word, case=False, na=False)
        elif tgt == "ファイル名のみ":
            current_mask = df['ファイル名'].str.contains(word, case=False, na=False)
        else:
            current_mask = pd.Series(False, index=df.index)
            
        if i == 0:
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
    res_str = str(res)
    if any(x in res_str for x in ["クリティカル", "決定的"]): return "crit"
    if any(x in res_str for x in ["ファンブル", "致命的"]): return "fumb"
    if "失敗" in res_str: return "fail"
    if utils.is_actual_success(res_str): return "succ"
    return "none"

def process_and_sort_log(df, group_keys, final_sort, final_asc, recalc_rule, use_char_code_sort):
    """指定された階層と最終ソート順に従ってデータフレームを並び替える"""
    if df.empty: 
        return df
    
    if "結果" in [k["col"] for k in group_keys]:
        succ_order = {res: i for i, res in enumerate(data.CORE_RESULT_ORDER)}
        df['_succ_rank'] = df['結果'].map(succ_order).fillna(999)
        
    if "技能" in [k["col"] for k in group_keys] and not use_char_code_sort:
        df['_skill_rank'] = df['判定名'].apply(lambda x: utils.get_skill_sort_rank(x, recalc_rule))

    df['_res_category'] = df['結果'].apply(_categorize_result)
    
    sort_cols = []
    sort_ascs = []
    
    for gk in group_keys:
        if gk["col"] == "結果": 
            sort_cols.append('_succ_rank')
            sort_ascs.append(gk["asc"])
        elif gk["col"] == "技能":
            if not use_char_code_sort: 
                sort_cols.append('_skill_rank')
                sort_ascs.append(gk["asc"])
            sort_cols.append('_技能') 
            sort_ascs.append(gk["asc"])
        else: 
            sort_cols.append(gk["col"])
            sort_ascs.append(gk["asc"])
            
    sort_cols.append('No' if final_sort == "時系列 (ログの通り)" else '出目')
    sort_ascs.append(final_asc)

    return df.sort_values(by=sort_cols, ascending=sort_ascs)
