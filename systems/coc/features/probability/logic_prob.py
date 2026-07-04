import pandas as pd
SORT_BASIS_OPTIONS = ["確率", "該当数", "総ロール数", "名前"]

def calc_char_stats(full_df, target_df, sort_basis, sort_order):
    """キャラクターごとの確率データ（合計、該当数、確率）を計算し、指定順でソートする"""
    if full_df.empty: 
        return pd.DataFrame()

    total_counts = full_df['キャラクター名'].value_counts()
    hit_counts = target_df['キャラクター名'].value_counts() if not target_df.empty else pd.Series(dtype=int)
    char_stats = []
    
    # 1. キャラクターごとに集計
    for char, c_total in total_counts.items():
        c_hit = hit_counts.get(char, 0)
        file_name = full_df[full_df['キャラクター名'] == char]['ファイル名'].iloc[0] if 'ファイル名' in full_df.columns else None
        char_stats.append({
            "キャラクター名": char, 
            "確率（％）": (c_hit / c_total * 100), 
            "該当数": c_hit, 
            "総ロール数": c_total, 
            "_file_name": file_name 
        })

    # 2. 指定された条件で並び替え（ソート）
    df_stats = pd.DataFrame(char_stats)
    is_asc = (sort_order == "昇順")
    if sort_basis == "確率": 
        df_stats = df_stats.sort_values(by=["確率（％）", "該当数"], ascending=[is_asc, is_asc])
    elif sort_basis == "該当数": 
        df_stats = df_stats.sort_values(by=["該当数", "確率（％）"], ascending=[is_asc, is_asc])
    elif sort_basis == "総ロール数": 
        df_stats = df_stats.sort_values(by=["総ロール数", "確率（％）"], ascending=[is_asc, is_asc])
    elif sort_basis == "名前": 
        df_stats = df_stats.sort_values(by=["キャラクター名"], ascending=is_asc)
            
    return df_stats