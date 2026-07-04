import pandas as pd
import streamlit as st
from . import utils_coc as utils 
from . import data_coc as data

# ==========================================
# 1. 再計算用の計算エンジン（プライベート関数として同じファイルに並べる）
# ==========================================
def _normalize_overall_result(res_str, recalc_rule):
    """ログの「成功/失敗」表記を再計算ルールの版数に合わせて統一する"""
    if recalc_rule == "再計算しない (ログの通り)": return res_str
    res_str = str(res_str).replace("決定的成功/スペシャル", "決定的成功")
    if "6版" in recalc_rule:
        return res_str.replace("イクストリーム成功", "スペシャル")\
                      .replace("ハード成功", "成功")\
                      .replace("レギュラー成功", "成功")\
                      .replace("クリティカル", "決定的成功")\
                      .replace("ファンブル", "致命的失敗")
    elif "7版" in recalc_rule:
        return res_str.replace("決定的成功", "クリティカル")\
                      .replace("致命的失敗", "ファンブル")
    return res_str

def _calculate_single_result(r_val, base_target, actual_target, recalc_rule):
    """出目と目標値から成功度を判定する"""
    crit_threshold, fumble_threshold, is_7e = 1, 100, True
    
    if recalc_rule == "7版ダイスで再計算": fumble_threshold = 96 if actual_target < 50 else 100
    elif recalc_rule == "クリファン5%（7版）で再計算": crit_threshold, fumble_threshold = 5, 96
    elif recalc_rule == "6版ダイスで再計算": is_7e = False
    elif recalc_rule == "クリファン5%（6版）で再計算": is_7e, crit_threshold, fumble_threshold = False, 5, 96
    
    if is_7e:
        if r_val >= fumble_threshold: return 'ファンブル'
        if r_val <= crit_threshold: return 'クリティカル'
        if r_val <= base_target // 5: return 'イクストリーム成功'
        if r_val <= base_target // 2: return 'ハード成功'
        if r_val <= base_target: return 'レギュラー成功'
        return '失敗'
    else:
        if r_val >= fumble_threshold: return '致命的失敗'
        if r_val <= crit_threshold: return '決定的成功'
        if r_val <= base_target // 5: return 'スペシャル'
        if r_val <= base_target: return '成功' 
        return '失敗'

def _determine_final_result(single_res, overall_result, is_bp, diff, rescue_diff, recalc_rule):
    """難易度指定やBP、救済設定を考慮し、最終的な結果文字列を決定する"""
    if recalc_rule == "再計算しない (ログの通り)":
        return overall_result

    has_diff = bool(diff)
    if not (is_bp or has_diff):
        return single_res
    
    single_is_succ = utils.is_actual_success(single_res)
    overall_is_fail = overall_result in ['失敗', 'ファンブル', '致命的失敗']
    
    # 1. 救済オプション
    if rescue_diff and has_diff and overall_is_fail and single_is_succ:
        return f"{single_res}（救済）"
    # 2. B/Pダイス
    if is_bp:
        if overall_result == '成功' and single_is_succ: 
            return single_res 
        elif overall_result == single_res: 
            return single_res 
        else: 
            return f"{overall_result}（{single_res}）" 
    # 3. 通常ロール
    if has_diff and overall_is_fail and single_is_succ:
        return '失敗'
    return single_res


# ==========================================
# 2. 前処理パイプライン（パース直後に実行される）
# ==========================================
def _set_initial_values(df, recalc_rule):
    df_new = df.copy()
    df_new['clean_skill_name'] = df_new['判定名'].apply(utils.clean_skill_name)
    df_new['初期値'] = df_new['clean_skill_name'].apply(lambda x: utils.get_initial_value(x, recalc_rule))
    
    if 'コマンド' in df_new.columns:
        mask = df_new['コマンド'].str.contains('CBR|RES|CANCEL', na=False)
        df_new.loc[mask, '初期値'] = -1

    df_new['初期値不明'] = df_new['初期値'] < 0
    return df_new

def _expand_bp_rolls(df, extract_bp):
    if not extract_bp or '全出目文字列' not in df.columns: return df
    df_new = df.copy()
    df_new['処理用出目リスト'] = df_new.apply(
        lambda row: [int(r.strip()) for r in str(row['全出目文字列']).split(',')] 
        if pd.notna(row['全出目文字列']) and ',' in str(row['全出目文字列']) else [row['出目']], 
        axis=1
    )
    df_new = df_new.explode('処理用出目リスト', ignore_index=True)
    df_new['出目'] = df_new['処理用出目リスト'].astype(int)
    
    def update_raw_log(row):
        if pd.notna(row['全出目文字列']) and ',' in str(row['全出目文字列']):
            return f"{row['生ログ']} (BP抽出: {row['出目']})"
        return row['生ログ']
        
    df_new['生ログ'] = df_new.apply(update_raw_log, axis=1)
    return df_new

def _recalculate_results(df, recalc_rule, rescue_diff):
    df_new = df.copy()
    
    def calc_row(row):
        cmd_id = str(row.get('コマンド', ''))
          
        if 'RES' in cmd_id and '自動' in str(row['結果']):
            return row['結果']

        base_target = row['目標値']
        actual_target = row.get('実目標値', base_target)
        diff = row['難易度'] if row['難易度'] != '通常' else None
        is_bp_roll = pd.notna(row.get('全出目文字列')) and ',' in str(row.get('全出目文字列', ''))
        
        overall_res = _normalize_overall_result(row['結果'], recalc_rule)
        single_res = _calculate_single_result(row['出目'], base_target, actual_target, recalc_rule)
        final_res = _determine_final_result(single_res, overall_res, is_bp_roll, diff, rescue_diff, recalc_rule)

        return final_res

    df_new['結果'] = df_new.apply(calc_row, axis=1)
    return df_new

# 外部から呼ばれる「前処理」の窓口
@st.cache_data(show_spinner=False, max_entries=3)
def preprocess_raw_data(df, extract_bp, rescue_diff, recalc_rule):
    """パース直後の生データに対し、再計算と展開を行う"""
    if df.empty: 
        return df
    
    df = _set_initial_values(df, recalc_rule)
    df = _expand_bp_rolls(df, extract_bp)
    df = _recalculate_results(df, recalc_rule, rescue_diff)
    return df


# ==========================================
# 3. 後処理パイプライン（フィルター時に実行される）
# ==========================================
def _add_initial_value_flag(df):
    if '初期値' not in df.columns or '初期値不明' not in df.columns: 
        return df
    df_filtered = df.copy()
    df_filtered['is_under_init'] = ~df_filtered['初期値不明'] & (df_filtered['出目'] <= df_filtered['初期値'])
    return df_filtered

def _exclude_bp(df, params):
    ex_b = params.get('exclude_b_global', False)
    ex_p = params.get('exclude_p_global', False)
    return utils.exclude_bp_rolls(df, ex_b, ex_p)

def _filter_by_command(df, params):
    sel_cmds = params.get('sel_cmds')
    sel_diffs = params.get('sel_diffs') 
    
    if sel_cmds is not None and 'コマンド' in df.columns:
        df = df[df['コマンド'].isin(sel_cmds)]
    if sel_diffs is not None and '難易度' in df.columns:
        df = df[df['難易度'].isin(sel_diffs)]
        
    return df

def _initial_value_filter(df, params):
    req_init_succ = params.get('req_init_succ', False)
    if not req_init_succ or '初期値' not in df.columns or '初期値不明' not in df.columns or 'is_under_init' not in df.columns: 
        return df
    unk_behav_sb = params.get('unk_behav_sb', "")
    df_filtered = df.copy()
    mask_known = df_filtered['is_under_init']
    
    if unk_behav_sb == "目標値を初期値として代用する" and '目標値' in df_filtered.columns:
        mask_unknown = df_filtered['初期値不明'] & (df_filtered['出目'] <= df_filtered['目標値'])
    elif unk_behav_sb == "初期値を100として扱う (必ず含める)": 
        mask_unknown = df_filtered['初期値不明']
    else: 
        mask_unknown = pd.Series(False, index=df_filtered.index)
    return df_filtered[mask_known | mask_unknown]

def _update_result_integration(df, params):
    chk_int_rescue = params.get('chk_int_rescue', False)
    chk_int_bp = params.get('chk_int_bp', False)
    if params.get('exclude_b_global') and params.get('exclude_p_global'):
        chk_int_bp = False
    if not chk_int_rescue and not chk_int_bp: 
        return df
    df_filtered = df.copy()
    if chk_int_rescue: 
        df_filtered['結果'] = df_filtered['結果'].str.replace(r'（救済）', '', regex=True)
    if chk_int_bp:
        bp_pattern = r'（(?:' + '|'.join(data.BASIC_RESULT_TERMS) + r')）'
        df_filtered['結果'] = df_filtered['結果'].str.replace(bp_pattern, '', regex=True)
    return df_filtered

# 🌟 外部から呼ばれる「後処理」の窓口
def apply_coc_specific_filters(df, params):
    """共通フィルター後のCoC専用調整を行う"""
    df = _add_initial_value_flag(df)
    df = _exclude_bp(df, params)
    df = _filter_by_command(df, params)
    df = _initial_value_filter(df, params)
    df = _update_result_integration(df, params)
    return df