import pandas as pd
from ...core import data_coc as data
from ...core import utils_coc as utils

# ==========================================
# 1. 定義・初期化（UIに渡す設計図の作成）
# ==========================================
def get_column_definitions(all_results, recalc_rule, display_mode):
    """ログに存在する結果を分類し、列のキーとラベルのリストを生成する"""
    base_results = utils.get_sorted_result([], recalc_rule, include_unfound_base=True)
    final_columns = list(dict.fromkeys(base_results + all_results))
    
    succ_col_name = "成功数" if display_mode == "回数のみ" else "成功率"
    cf_col_name = "クリファン数" if display_mode == "回数のみ" else "クリファン率"

    disp_keys = list(dict.fromkeys(["総数", "succ_col", "cf_col", "1_crit", "100_fumb"] + final_columns))
    disp_labels = list(dict.fromkeys(["総数", succ_col_name, cf_col_name, "1クリ", "100ファン"] + final_columns))
    final_groups, other_keys, key_to_label = get_checkbox_groups(disp_keys, disp_labels, recalc_rule)

    disp_keys = []
    for group in final_groups:
        disp_keys.extend(group)
    disp_keys.extend(other_keys)
    disp_labels = [key_to_label[k] for k in disp_keys]

    default_keys = [k for k in disp_keys if not (k in ["1_crit", "100_fumb"] or ("（" in k and "（救済）" not in k))]
    
    return final_columns, disp_keys, disp_labels, default_keys

def get_checkbox_groups(disp_keys, disp_labels, recalc_rule):
    """ルール(版)に応じて、表示項目のグループ分け構造（設計図）を作成する"""
    key_to_label = dict(zip(disp_keys, disp_labels))
    if "7版" in recalc_rule:
        group_defs = [
            ["総数", "succ_col", "cf_col"], 
            ["1_crit", "クリティカル"], 
            ["成功"], 
            ["失敗", "ファンブル", "100_fumb"],
        ]
    elif "6版" in recalc_rule:
        group_defs = [
            ["総数", "succ_col", "cf_col"], 
            ["1_crit", "決定的", "スペシャル", "成功", "クリティカル"], 
            ["失敗", "致命的", "ファンブル", "100_fumb"],
        ]
    else :
        group_defs = [
            ["総数", "succ_col", "cf_col"], 
            ["1_crit", "クリティカル", "決定的", "スペシャル"], 
            ["成功"], 
            ["失敗", "致命的", "ファンブル", "100_fumb"],
        ]
        
    assigned_keys = set()
    final_groups = []
    
    for keywords in group_defs:
        group_keys = []
        for word in keywords:
            for k in disp_keys:
                if k not in assigned_keys and (word in k or word in key_to_label[k]):
                    group_keys.append(k)
                    assigned_keys.add(k)
        if group_keys:
            final_groups.append(group_keys)
    bp_keys = []
    
    for bp_result in data.BP_RESULT_ORDER:
        if bp_result in disp_keys and bp_result not in assigned_keys:
            bp_keys.append(bp_result)
            assigned_keys.add(bp_result)
    if bp_keys:
        final_groups.append(bp_keys)
            
    other_keys = [k for k in disp_keys if k not in assigned_keys]
    other_keys.sort()
    
    return final_groups, other_keys, key_to_label


# ==========================================
# 2. 集計・計算（メインのデータ処理）
# ==========================================
def calc_overall_stats(df_calc, final_columns):
    """全キャラクターを合算した「全体（合計）」の集計データを生成する"""
    total_rolls = len(df_calc)

    def _pct(count):
        return (count / total_rolls * 100) if total_rolls else 0
    
    is_crit = df_calc['_is_crit']
    is_fumb = df_calc['_is_fumb']

    succ_count = df_calc['成功フラグ'].sum() if total_rolls else 0
    crit_count = is_crit.sum()
    fumb_count = is_fumb.sum()
    cf_count = crit_count + fumb_count
    
    total_1crit = len(df_calc[(df_calc['出目'] == 1) & is_crit])
    total_100fumb = len(df_calc[(df_calc['出目'] == 100) & is_fumb])
    
    overall_data = {
        '総数': total_rolls, '_raw_count_総数': total_rolls, '_raw_pct_総数': _pct(total_rolls),
        '_raw_count_succ_col': succ_count, '_raw_pct_succ_col': _pct(succ_count),
        '_raw_count_cf_col': cf_count, '_raw_pct_cf_col': _pct(cf_count),
        '_raw_count_1_crit': total_1crit, '_raw_pct_1_crit': _pct(total_1crit),
        '_raw_count_100_fumb': total_100fumb, '_raw_pct_100_fumb': _pct(total_100fumb),
        'crit_count': crit_count, 'fumb_count': fumb_count, 'cf_count': cf_count, 'succ_count': succ_count
    }
    
    result_counts = df_calc['結果'].value_counts().to_dict()
    for col in final_columns:
        c_cnt = result_counts.get(col, 0)
        overall_data[f'_raw_count_{col}'] = c_cnt
        overall_data[f'_raw_pct_{col}'] = _pct(c_cnt)
    
    return overall_data


def calc_char_stats(df_calc, final_columns, sort_key, sort_basis, sort_order):
    """キャラクターごとのサマリーデータを集計し、指定された条件でソートする"""
    is_crit = df_calc['_is_crit']
    is_fumb = df_calc['_is_fumb']
    
    char_stats = []
    
    for char, group in df_calc.groupby('キャラクター名'):
        c_total = len(group)
        def _pct(count):
            return (count / c_total * 100) if c_total else 0
        
        g_crit = is_crit[group.index]
        g_fumb = is_fumb[group.index]
        c_succ = group['成功フラグ'].sum()
        c_crit = g_crit.sum()
        c_fumb = g_fumb.sum()
        c_cf = c_crit + c_fumb
        c_1crit = len(group[(group['出目'] == 1) & g_crit])
        c_100fumb = len(group[(group['出目'] == 100) & g_fumb])
        
        orig_name = group['統合前のキャラクター名'].iloc[0] if '統合前のキャラクター名' in group.columns else char
        file_name = group['ファイル名'].iloc[0] if 'ファイル名' in group.columns else None
        
        row = {
            'キャラクター名': char, '_orig_name': orig_name, '_file_name': file_name,
            '総数': c_total, '_raw_count_総数': c_total, '_raw_pct_総数': _pct(c_total),
            'succ_col': _pct(c_succ), '_raw_count_succ_col': c_succ, '_raw_pct_succ_col': _pct(c_succ),
            'cf_col': _pct(c_cf), '_raw_count_cf_col': c_cf, '_raw_pct_cf_col': _pct(c_cf),
            '1_crit': _pct(c_1crit), '_raw_count_1_crit': c_1crit, '_raw_pct_1_crit': _pct(c_1crit),
            '100_fumb': _pct(c_100fumb), '_raw_count_100_fumb': c_100fumb, '_raw_pct_100_fumb': _pct(c_100fumb)
        }

        result_counts = group['結果'].value_counts().to_dict()
        for col in final_columns:
            c_cnt = result_counts.get(col, 0)
            row[col] = _pct(c_cnt)
            row[f'_raw_count_{col}'] = c_cnt
            row[f'_raw_pct_{col}'] = _pct(c_cnt)

        char_stats.append(row)

    df_chars = pd.DataFrame(char_stats)
    if df_chars.empty: 
        return df_chars
    
    is_asc = (sort_order == "昇順")
    if sort_key == "char_name":
        df_chars = df_chars.sort_values(by=['キャラクター名'], ascending=is_asc)
    else:
        target_raw_col = f'_raw_count_{sort_key}' if sort_basis == "回数" else f'_raw_pct_{sort_key}'
        df_chars = df_chars.sort_values(by=[target_raw_col, 'キャラクター名'], ascending=[is_asc, True])
        
    return df_chars


# ==========================================
# 3. 補助計算（ハイライト等）
# ==========================================
def get_min_max(df_chars, displayable_columns_keys, include_zero, disable_tie_count=None):
    """ハイライト（色付け）の基準となる列ごとの最大値・最小値を計算する"""
    max_dict = {"確率（％）": {}, "回数": {}}
    min_dict = {"確率（％）": {}, "回数": {}}
    if df_chars.empty: return max_dict, min_dict
    
    for k in displayable_columns_keys:
        for basis in ["確率（％）", "回数"]:
            col = f'_raw_count_{k}' if basis == "回数" else f'_raw_pct_{k}'
            vals = df_chars[col]
            
            # 🌟 最大値の処理
            c_max = vals.max()
            if disable_tie_count is not None and c_max is not None:
                # Pandasの必殺技: (vals == c_max).sum() で最大値と同じ値の人数を数える
                if (vals == c_max).sum() >= disable_tie_count:
                    c_max = None  # 閾値以上いたら「最大値はなし」としてハイライトを消す
            max_dict[basis][k] = c_max
            
            # 🌟 最小値の処理
            min_vals = vals if include_zero else vals[vals > 0]
            c_min = min_vals.min() if not min_vals.empty else None
            if disable_tie_count is not None and c_min is not None:
                if (vals == c_min).sum() >= disable_tie_count:
                    c_min = None  # 閾値以上いたらハイライトを消す
            min_dict[basis][k] = c_min
            
    return max_dict, min_dict