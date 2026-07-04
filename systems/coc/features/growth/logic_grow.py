import pandas as pd
from ...core import utils_coc as utils
from ...core import data_coc as data

# ==========================================
# 1. データ集計・処理の裏方関数群
# ==========================================
def _prepare_growth_data(df, recalc_rule, check_growth_mask, config):
    """【裏方】データフレームのフィルタリングとフラグ付け"""
    display_df = df.copy()

    if config['hide_non_grow']: 
        if "6版" in recalc_rule:
            target_list = data.NON_GROWABLE_LIST_6E
        elif "7版" in recalc_rule:
            target_list = data.NON_GROWABLE_LIST_7E
        else:
            target_list = data.NON_GROWABLE_LIST_6E
        display_df = display_df[~display_df['clean_skill_name'].isin(target_list)]

    elif config['hide_sanity']: 
        display_df = display_df[~display_df['clean_skill_name'].isin(data.SANITY_ROLL_LIST)]

    if display_df.empty:
        return display_df

    display_df['成長対象'] = check_growth_mask[display_df.index] 


    return display_df

def _aggregate_individuals(display_df, config):
    """【裏方】個人・技能ごとにグループ化し、回数や詳細を集計する"""
    if display_df.empty: 
        return pd.DataFrame()

    group_cols = ['キャラクター名', 'clean_skill_name']
    if not config['ignore_target']: 
        group_cols.append('目標値')

    aggregated = []
    for keys, group in display_df.groupby(group_cols):
        char, clean_skill = keys[0], keys[1]
        
        if clean_skill == "---":
            display_skill = " （技能名未入力）"
            has_growth_mark = False
        else:
            display_skill = f"【{clean_skill}】"
            has_growth_mark = group['成長対象'].any()

        if config['ignore_target']:
            unique_targets = group['目標値'].dropna().unique()
            if len(unique_targets) > 1: 
                target_val = "変動"
            elif len(unique_targets) == 1: 
                target_val = unique_targets[0]
            else: target_val = None
        else: 
            target_val = keys[2]

        if config['only_growth'] and not has_growth_mark: 
            continue
            
        details = group['結果'].value_counts().to_dict()
        total_succ = sum(count for res, count in details.items() if utils.is_actual_success(res))
        crit_count = sum(count for res, count in details.items() if "クリティカル" in res or "決定的" in res)
        fumb_count = sum(count for res, count in details.items() if "ファンブル" in res or "致命的" in res)
        init_succ = group['is_under_init'].sum() if 'is_under_init' in group else 0
            
        aggregated.append({
            "キャラクター名": char, 
            "技能名": display_skill, 
            "_clean_skill_name": clean_skill,
            "目標値": target_val,
            "総数": len(group), 
            "合計成功数": total_succ, 
            "クリティカル": crit_count, 
            "ファンブル": fumb_count,
            "初期値成功": init_succ, 
            "初期値不明": group['初期値不明'].any(), 
            "チェック": has_growth_mark,
            "詳細内訳": details
        })

    return pd.DataFrame(aggregated)

def _add_all_character(df_agg):
    """【裏方】複数人いる場合、末尾に「🌟 ALL (全員)」の合算データを追加する"""
    if df_agg.empty: 
        return df_agg
    unique_chars = df_agg['キャラクター名'].unique()
    if len(unique_chars) <= 1: 
        return df_agg 
        
    all_agg = []
    for skill, group in df_agg.groupby('_clean_skill_name'):
        merged_details = {}
        for d in group['詳細内訳']:
            for k, v in d.items():
                merged_details[k] = merged_details.get(k, 0) + v
                
        unique_targets = group['目標値'].dropna().unique()
        if "変動" in unique_targets or len(unique_targets) > 1:
            target_val = "変動"
        elif len(unique_targets) == 1:
            target_val = unique_targets[0]
        else:
            target_val = None

        display_skill = group['技能名'].iloc[0]

        all_agg.append({
            "キャラクター名": "🌟 ALL (全員)", 
            "技能名": display_skill, 
            "_clean_skill_name": skill, 
            "目標値": target_val, 
            "総数": group['総数'].sum(), 
            "合計成功数": group['合計成功数'].sum(), 
            "クリティカル": group['クリティカル'].sum(), 
            "ファンブル": group['ファンブル'].sum(),
            "初期値成功": group['初期値成功'].sum(), 
            "初期値不明": group['初期値不明'].any(),
            "チェック": group['チェック'].any(), 
            "詳細内訳": merged_details
        })
        
    df_all = pd.DataFrame(all_agg)
    return pd.concat([df_agg, df_all], ignore_index=True)


# ==========================================
# 2. データ集計・処理の司令塔
# ==========================================
def process_growth_data(df, recalc_rule, check_growth_mask, config):
    """成長チェックの対象データを処理し、集計結果を返すメイン関数"""
    
    # 1. 不要なデータを除外し、成長対象フラグを立てる
    display_df = _prepare_growth_data(df, recalc_rule, check_growth_mask, config)
    # 2. キャラクター・技能ごとに集計する
    df_agg = _aggregate_individuals(display_df, config)
    # 3. 複数人いれば「ALL(全員)」の行を合算して末尾に追加する
    return _add_all_character(df_agg)


# ==========================================
# 3. UI表示用ロジック（並べ替え・テキスト生成）
# ==========================================
def sort_growth_data(char_df, sort_check_top, sort_basis, sort_order, recalc_rule, use_char_code_sort):
    """キャラクターごとの集計データを、指定された条件で並び替える"""
    df_sorted = char_df.copy()
    
    def _get_skill_sort_key(skill_name):
        if use_char_code_sort:
            return "\xff\xff\xff" if skill_name == " （技能名未入力）" else str(skill_name)
        else:
            return 999999 if skill_name == " （技能名未入力）" else utils.get_skill_sort_rank(skill_name, recalc_rule)

    df_sorted['_skill_rank'] = df_sorted['技能名'].apply(_get_skill_sort_key)
    df_sorted['_is_unentered'] = df_sorted['技能名'] == " （技能名未入力）"
    
    by_cols = []
    asc_specs = []
    
    if sort_check_top:
        by_cols.append('チェック')
        asc_specs.append(False) 
        
    by_cols.append('_is_unentered')
    asc_specs.append(True)
    
    is_asc = (sort_order == "昇順")
    if "技能順" in sort_basis:
        by_cols.append('_skill_rank')
        asc_specs.append(is_asc)
    elif "総数順" in sort_basis:
        by_cols.append('総数')
        asc_specs.append(is_asc)
    elif "合計成功数順" in sort_basis:
        by_cols.append('合計成功数')
        asc_specs.append(is_asc)
        
    by_cols.append('_clean_skill_name')
    asc_specs.append(True)
    by_cols.append('目標値')
    asc_specs.append(True)
    
    return df_sorted.sort_values(
        by=by_cols, 
        ascending=asc_specs, 
        key=lambda col: col.astype(str) if col.name == '目標値' else col)

def generate_copy_text(char_df, selected_char):
    """成長チェック一覧のコピペ用テキストを生成する"""
    growth_skills = char_df[char_df['チェック']]['技能名'].tolist()
    if not growth_skills:
        return "※成長チェックがついた技能はありません。"
    
    header = "【成長技能：全体】" if "ALL" in selected_char else f"【成長技能：{selected_char}】"
    return header + "\n" + "\n".join([f"・{s}" for s in growth_skills])