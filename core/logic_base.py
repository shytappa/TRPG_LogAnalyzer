import pandas as pd

# ==========================================
# 内部処理用のプライベート関数
# ==========================================
def _filter_exact_matches(df, params):
    """完全一致フィルター（ファイル名、タブ、キャラクター名、成功度、判定名）"""
    sel_files = params.get('sel_files', [])
    sel_file_tabs = params.get('sel_file_tabs', [])
    sel_chars = params.get('sel_chars', [])
    sel_success_levels = params.get('sel_success_levels', [])
    sel_skills = params.get('sel_skills', [])

    df_filtered = df[
        (df['ファイル名'].isin(sel_files)) & 
        (df['file_tab'].isin(sel_file_tabs)) &
        (df['file_char'].isin(sel_chars)) & 
        (df['結果'].isin(sel_success_levels)) &
        (df['ベース判定名'].isin(sel_skills))
    ].copy()
    # 後のキャラクター統合などで名前が変わる前に、元の名前をバックアップしておく
    df_filtered['統合前のキャラクター名'] = df_filtered['キャラクター名']
    
    return df_filtered


def _filter_range_masks(df, params):
    """出目の数値範囲フィルター"""
    active_ranges = params.get('active_ranges', [])
    if not active_ranges:
        return df

    range_mask = pd.Series(False, index=df.index)
    for min_v, max_v in active_ranges: 
        range_mask = range_mask | ((df['出目'] >= min_v) & (df['出目'] <= max_v))
    return df[range_mask].copy()


def _character_merges(df, params):
    """キャラクターの統合処理"""
    char_merges = params.get('char_merges', [])
    if not char_merges:
        return df

    char_map, file_map = {}, {}
    for merge in char_merges:
        source_files = {tgt.split("<:::>", 1)[0] for tgt in merge['targets']}
        new_file_name = list(source_files)[0] if len(source_files) == 1 else "🌟複数ファイル統合"
        
        for tgt in merge['targets']: 
            char_map[tgt] = merge['name']
            file_map[tgt] = new_file_name
            
    if char_map:
        df_filtered = df.copy()
        is_merged_mask = df_filtered['file_char'].isin(char_map.keys())
        df_filtered.loc[is_merged_mask, 'キャラクター名'] = df_filtered.loc[is_merged_mask, 'file_char'].map(char_map)
        df_filtered.loc[is_merged_mask, 'ファイル名'] = df_filtered.loc[is_merged_mask, 'file_char'].map(file_map)
        df_filtered['file_char'] = df_filtered['ファイル名'] + "<:::>" + df_filtered['キャラクター名']
        
        return df_filtered
    return df


def _separate_char_by_file(df, params):
    """同名キャラのファイル名で区別を処理"""
    if params.get('separate_char_by_file', False):
        df_filtered = df.copy()
        df_filtered['キャラクター名'] = df_filtered['キャラクター名'] + " (" + df_filtered['ファイル名'] + ")"
        return df_filtered
    return df

# ==========================================
# 外部から呼び出されるメイン関数
# ==========================================
def add_search_keys(df):
    """UI検索用の基本結合列（file_charなど）を作成"""
    df_new = df.copy()
    # 連続ロール用の #1 などを削る
    df_new['ベース判定名'] = df_new['判定名'].astype(str).str.replace(r'#\d+$', '', regex=True)

    df_new['file_tab'] = df_new['ファイル名'] + "<:::>" + df_new['タブ']
    df_new['file_char'] = df_new['ファイル名'] + "<:::>" + df_new['キャラクター名']
    return df_new

def universal_filters(df, params):
    """
    ファイル、タブ、キャラクター、判定名、出目の数値範囲など、
    全システム共通の絞り込みをパイプラインで行う
    """
    df = _filter_exact_matches(df, params)
    df = _filter_range_masks(df, params)
    df = _character_merges(df, params)
    df = _separate_char_by_file(df, params)
    return df