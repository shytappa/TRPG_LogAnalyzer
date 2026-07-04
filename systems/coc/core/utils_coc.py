import re
import pandas as pd
from . import data_coc as data

# ==========================================
# 1. 基礎ツール：文字列のクリーニング
# ==========================================
def clean_skill_name(skill_name):
    """【 】や末尾の番号(#1)、空白を取り除き、純粋な名前にするクリーニング処理を行う。"""
    name = str(skill_name).upper()
    name = re.sub(r'#\d+$', '', name)
    name = re.sub(r'^【|】$', '', name)
    name = re.sub(r'\s+', '', name)
    name = name.replace("(", "（").replace(")", "）")
    name = re.sub(r'[*×xXｘＸ][0-9]+$', '', name)
    if not name:
        return "---"
    return name

# ==========================================
# 2. ルール判定エンジン：クトゥルフのルール照会
# ==========================================
def get_initial_value(skill_name, recalc_rule):
    """クリーニングされた技能名と版数に基づいて、ルールブックに準拠した初期値を返す。"""
    if "6版" in recalc_rule:
        dicts = [data.INITIAL_VALUES_6E]
        patterns = [data.PATTERN_VALUES_6E]
    elif "7版" in recalc_rule:
        dicts = [data.INITIAL_VALUES_7E]
        patterns = [data.PATTERN_VALUES_7E]
    else:
        dicts = [data.INITIAL_VALUES_7E, data.INITIAL_VALUES_6E]
        patterns = [data.PATTERN_VALUES_7E, data.PATTERN_VALUES_6E]

    for d in dicts:
        if skill_name in d: return d[skill_name]
            
    if "（" not in skill_name: 
        return -1
        
    for p_dict in patterns:
        for pattern, val in p_dict.items():
            if re.match(pattern, skill_name): return val
    return -1

def is_actual_success(res_str): 
    """結果文字列の中にシステム上の「成功・大成功」を示すキーワードが含まれているかを判定する。"""
    if not isinstance(res_str, str): 
        return False
    if any(fail_word in res_str for fail_word in ['失敗', 'ファンブル', '致命的失敗']): 
        return False
    return any(x in res_str for x in ['成功', 'クリティカル', 'スペシャル', '（救済）', '決定的成功'])

# ==========================================
# 3. 表示順序エンジン：UIの並び替え補助
# ==========================================
def get_skill_sort_rank(skill_name, recalc_rule):
    clean_name = clean_skill_name(skill_name)
    
    if "6版" in recalc_rule:
        dicts = [data.SKILL_SORT_ORDER_6E]
    elif "7版" in recalc_rule:
        dicts = [data.SKILL_SORT_ORDER_7E]
    else:
        dicts = [data.SKILL_SORT_ORDER_7E, data.SKILL_SORT_ORDER_6E]

    for d in dicts:
        if clean_name in d: return d[clean_name]
        
    match = re.match(r'^(.*?（)', clean_name)
    if match:
        prefix = match.group(1) 
        for d in dicts:
            if prefix in d: return d[prefix]
            
    for d in dicts:
        for k, v in d.items():
            if clean_name.startswith(k): return v
    return 9999

def get_sorted_result(found_results, recalc_rule, include_unfound_base=False):#sidebar,grows,probabilityで使用
    """結果リストを、クトゥルフのルールブックに準じた美しい順序に並び替える。"""
    if "再計算しない" in recalc_rule:
        always_show = [] 
    elif "6版" in recalc_rule:
        always_show = ['決定的成功', 'スペシャル', '成功', '失敗', '致命的失敗']
    else:
        always_show = ['クリティカル', 'イクストリーム成功', 'ハード成功', 'レギュラー成功', '失敗', 'ファンブル']

    first_part = [
        r for r in data.CORE_RESULT_ORDER 
        if r in found_results or (include_unfound_base and r in always_show)
    ]
    extra = sorted([r for r in found_results if r not in data.CORE_RESULT_ORDER])
    
    return list(dict.fromkeys(first_part + extra))



# ==========================================
# 4. 追加（後で整形）
# ==========================================

def get_ui_condition_mask(df, filter_config):
    """UIで設定された条件を受け取り、DataFrameを絞り込むマスクを返す"""
    if df.empty:
        return pd.Series(False, index=df.index)

    # オーダー表から設定を取り出す
    sel_target_res = filter_config.get("sel_target_res", [])
    logic1 = filter_config.get("logic1", "AND")
    use_init = filter_config.get("use_init", False)
    unk_behav = filter_config.get("unk_behav", "")
    logic2 = filter_config.get("logic2", "AND")
    use_ranges = filter_config.get("use_ranges", False)
    active_ranges = filter_config.get("active_ranges", [])

    # 条件1：結果の合致
    mask_result = df['結果'].isin(sel_target_res)

    # 条件2：初期値以下
    mask_init = pd.Series(False, index=df.index)
    if use_init:
        mask_known = ~df['初期値不明'] & (df['出目'] <= df['初期値'])
        if unk_behav == "目標値を初期値として代用する":
            mask_unk = df['初期値不明'] & (df['出目'] <= df['目標値'])
        elif unk_behav == "初期値を100として扱う (必ず含める)":
            mask_unk = df['初期値不明']
        else:
            mask_unk = False
        mask_init = mask_known | mask_unk

    # 条件3：数値範囲
    mask_range = pd.Series(False, index=df.index)
    if use_ranges and active_ranges:
        for min_v, max_v in active_ranges:
            mask_range = mask_range | ((df['出目'] >= min_v) & (df['出目'] <= max_v))

    # AND/OR ロジックの結合
    true_mask = pd.Series(True, index=df.index)
    false_mask = pd.Series(False, index=df.index)

    eval_cond2 = mask_init if use_init else (true_mask if logic1 == "AND" else false_mask)
    res1_mask = (mask_result & eval_cond2) if logic1 == "AND" else (mask_result | eval_cond2)

    eval_cond3 = mask_range if use_ranges else (true_mask if logic2 == "AND" else false_mask)
    final_mask = (res1_mask & eval_cond3) if logic2 == "AND" else (res1_mask | eval_cond3)

    # コマンド・難易度・BPが config にあれば
    sel_cmds = filter_config.get("sel_cmds")
    if sel_cmds is not None and 'コマンド' in df.columns:
        final_mask = final_mask & df['コマンド'].isin(sel_cmds)

    sel_diffs = filter_config.get("sel_diffs")
    if sel_diffs is not None and '難易度' in df.columns:
        final_mask = final_mask & df['難易度'].isin(sel_diffs)

    exclude_b = filter_config.get("exclude_b", False)
    exclude_p = filter_config.get("exclude_p", False)
    if exclude_b or exclude_p:
        bp_mask = get_bp_exclusion_mask(df, exclude_b, exclude_p)
        final_mask = final_mask & ~bp_mask

    exclude_multi = filter_config.get("exclude_multi", False)
    if exclude_multi and '複数ロール' in df.columns:
        final_mask = final_mask & ~df['複数ロール']

    return final_mask

# ==========================================
# 5. 特殊ルール処理（B/Pダイスなど）
# ==========================================
def get_bp_exclusion_mask(df, exclude_b=False, exclude_p=False):
    """
    B/Pダイスの除外対象となる行のマスク（Trueが除外対象）を返す。
    ※ 成長画面のように「行は残すがマークだけ外す」用途で使用。
    """
    mask = pd.Series(False, index=df.index)
    if not exclude_b and not exclude_p:
        return mask
    if 'B/P' not in df.columns:
        return mask
    
    bp_series = df['B/P'].fillna(0).astype(int)
    if exclude_b: mask = mask | (bp_series > 0)
    if exclude_p: mask = mask | (bp_series < 0)
    return mask

def exclude_bp_rolls(df, exclude_b=False, exclude_p=False):
    """
    データフレームからB/Pダイスを使用したロールを物理的に除外する。
    ※ サイドバーフィルターのように「データから完全に消し去る」用途で使用。
    """
    if not exclude_b and not exclude_p:
        return df
    mask = get_bp_exclusion_mask(df, exclude_b, exclude_p)
    return df[~mask]