from dataclasses import dataclass
import numpy as np
import pandas as pd
from ...core import skills_coc as skills
from ...core import results_coc as results
from ...core import data_coc as data
from ...core import rules_coc as rules
from ...core.logic_coc import is_6e_rows

ALL_CHAR_NAME = "🌟 ALL (全員)"           # 全員を合算した行のキャラクター名
UNENTERED_SKILL = " （技能名未入力）"       # 技能名の無いロール（CC<=50 だけなど）の表示名

@dataclass
class GrowthConfig:
    """成長チェックの表示・絞り込みの設定（ui_grow の「⚙️ 成長チェックの表示・絞り込み設定」で作る）"""
    hide_non_grow: bool = True    # 成長しない項目（アイデア、幸運など）を除外
    hide_sanity: bool = True      # 正気度ロールを除外
    ignore_target: bool = True    # 目標値の違いを無視（同じ技能を1行にまとめる）
    only_growth: bool = False     # 成長チェックがついた技能のみ表示

# ==========================================
# 1. データ集計・処理の裏方関数群
# ==========================================
def _non_growable_mask(df, recalc_rule):
    """成長しない項目（能力値・幸運・アイデア・正気度ロールなど）の行。「再計算しない」では行のコマンドで版を決める"""
    names = df['_clean_skill_name']
    edition = rules.get_rule(recalc_rule).edition
    if edition is None:
        is_6e = is_6e_rows(df)   # コマンドの列が無ければ全行 False（7版）
        mask = names.isin(data.NON_GROWABLE_LIST_6E).where(is_6e, names.isin(data.NON_GROWABLE_LIST_7E))
    else:
        mask = names.isin(data.NON_GROWABLE_LIST_6E if edition == 6 else data.NON_GROWABLE_LIST_7E)
    return mask | _sanity_mask(df)

def _sanity_mask(df):
    return results.map_unique(df['_clean_skill_name'], skills.is_sanity_roll).astype(bool)

def _target_label(n_targets, first_target, varies=False):
    """目標値の表示。複数の目標値がある（varies: すでに「変動」の行がある）なら「変動」、1つならその値、無ければ None"""
    if varies or n_targets > 1:
        return "変動"
    if n_targets == 1:
        return first_target
    return None

def _prepare_growth_data(df, recalc_rule, check_growth_mask, config):
    """【裏方】データフレームのフィルタリングとフラグ付け"""
    # この後で列を足すので、元の表とは別の表にする（絞り込んだ表はもともと別の表。pandas 3 では、足した列だけが増える）
    if config.hide_non_grow:
        display_df = df[~_non_growable_mask(df, recalc_rule)]
    elif config.hide_sanity:
        display_df = df[~_sanity_mask(df)]
    else:
        display_df = df.copy(deep=False)

    if display_df.empty:
        return display_df

    display_df['_is_growth_target'] = check_growth_mask[display_df.index]
    return display_df

def _aggregate_individuals(display_df, config):
    """【裏方】個人・技能ごとにグループ化し、回数や詳細を集計する"""
    if display_df.empty: 
        return pd.DataFrame()

    group_cols = ['キャラクター名', '_clean_skill_name']
    if not config.ignore_target:
        group_cols.append('目標値')

    # グループ（キャラ×技能(×目標値)）ごとの集計を列単位でまとめて計算する
    # （約5000グループを1つずつ切り出して数えると数秒かかるため）
    df = display_df.dropna(subset=group_cols)   # groupby と同じく、キーが欠けた行は除外
    gb = df.groupby(group_cols, sort=True)
    sizes = gb.size()
    keys_list = sizes.index.tolist()
    res = df['結果']
    flags = pd.DataFrame({
        'succ': results.map_results(res, results.is_actual_success),
        'crit': results.map_results(res, results.is_crit),
        'fumb': results.map_results(res, results.is_fumble),
        'mark': df['_is_growth_target'].astype(bool),
        'unknown': df['_init_unknown'].astype(bool),
        'init': df['_is_under_init'].astype(bool) if '_is_under_init' in df else False,
    }, index=df.index)
    sums = flags.groupby([df[c] for c in group_cols], sort=True).agg(
        succ=('succ', 'sum'), crit=('crit', 'sum'), fumb=('fumb', 'sum'),
        mark=('mark', 'any'), unknown=('unknown', 'any'), init=('init', 'sum'))
    # 結果ごとの回数（詳細内訳）：グループ × 結果 の表を作ってから、グループごとの辞書にする
    counts = pd.crosstab([df[c] for c in group_cols], res).reindex(sizes.index, fill_value=0)
    count_cols = list(counts.columns)
    count_vals = counts.to_numpy()
    if config.ignore_target:
        n_targets = gb['目標値'].nunique()
        first_target = gb['目標値'].first()
    # ☑ の根拠になったロール（成長対象のロールの本文）
    marked = df[flags['mark']]
    if marked.empty:
        basis_logs = pd.Series(None, index=sizes.index, dtype=object)
    else:
        basis_logs = marked['生ログ'].astype(str).groupby([marked[c] for c in group_cols]).agg(list).reindex(sizes.index)

    aggregated = []
    for i, keys in enumerate(keys_list):
        char, clean_skill = keys[0], keys[1]
        s = sums.iloc[i]

        if clean_skill == "---":
            display_skill = UNENTERED_SKILL
            has_growth_mark = False
        else:
            display_skill = f"【{clean_skill}】"
            has_growth_mark = bool(s['mark'])

        target_val = _target_label(n_targets.iloc[i], first_target.iloc[i]) if config.ignore_target else keys[2]

        if config.only_growth and not has_growth_mark:
            continue

        # 回数の多い順（value_counts と同じ並び）の辞書にする
        row_counts = count_vals[i]
        details = {count_cols[j]: int(row_counts[j]) for j in sorted(np.flatnonzero(row_counts), key=lambda j: -row_counts[j])}
        total_succ = int(s['succ'])
        crit_count = int(s['crit'])
        fumb_count = int(s['fumb'])
        init_succ = int(s['init']) if '_is_under_init' in df else 0

        aggregated.append({
            "キャラクター名": char, 
            "技能名": display_skill, 
            "_clean_skill_name": clean_skill,
            "目標値": target_val,
            "総数": int(sizes.iloc[i]),
            "合計成功数": total_succ,
            "クリティカル": crit_count,
            "ファンブル": fumb_count,
            "初期値以下": init_succ,
            "初期値不明": bool(s['unknown']),
            "チェック": has_growth_mark,
            "詳細内訳": details,
            "根拠ロール": basis_logs.iloc[i] if has_growth_mark and isinstance(basis_logs.iloc[i], list) else [],
        })

    return pd.DataFrame(aggregated)

def _add_all_character(df_agg):
    """【裏方】複数人いる場合、末尾に「🌟 ALL (全員)」の合算データを追加する"""
    if df_agg.empty: 
        return df_agg
    unique_chars = df_agg['キャラクター名'].unique()
    if len(unique_chars) <= 1: 
        return df_agg 
        
    # 技能ごとの合算を列単位でまとめて計算する
    gb = df_agg.groupby('_clean_skill_name', sort=True)
    sums = gb[['総数', '合計成功数', 'クリティカル', 'ファンブル', '初期値以下']].sum()
    anys = gb[['初期値不明', 'チェック']].any()
    first_skill = gb['技能名'].first()
    targets = df_agg['目標値']
    has_var = targets.eq("変動").groupby(df_agg['_clean_skill_name'], sort=True).any()
    n_targets = gb['目標値'].nunique()
    first_target = gb['目標値'].first()
    # 詳細内訳（結果→回数の辞書）は、表に展開して技能ごとに足し合わせる
    detail_table = pd.DataFrame(list(df_agg['詳細内訳']), index=df_agg.index).fillna(0)
    detail_sums = detail_table.groupby(df_agg['_clean_skill_name'], sort=True).sum()
    detail_cols = list(detail_sums.columns)
    basis_logs = gb['根拠ロール'].agg(lambda lists: [log for logs in lists for log in logs])

    all_agg = []
    for i, skill in enumerate(sums.index):
        merged_details = {detail_cols[j]: int(v) for j, v in enumerate(detail_sums.iloc[i].to_numpy()) if v}

        all_agg.append({
            "キャラクター名": ALL_CHAR_NAME,
            "技能名": first_skill.iloc[i],
            "_clean_skill_name": skill,
            "目標値": _target_label(n_targets.iloc[i], first_target.iloc[i], has_var.iloc[i]),
            "総数": sums['総数'].iloc[i],
            "合計成功数": sums['合計成功数'].iloc[i],
            "クリティカル": sums['クリティカル'].iloc[i],
            "ファンブル": sums['ファンブル'].iloc[i],
            "初期値以下": sums['初期値以下'].iloc[i],
            "初期値不明": anys['初期値不明'].iloc[i],
            "チェック": anys['チェック'].iloc[i],
            "詳細内訳": merged_details,
            "根拠ロール": basis_logs.iloc[i],
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
def sort_growth_data(char_df, sort_check_top, sort_basis, ascending, recalc_rule, use_char_code_sort):
    """キャラクターごとの集計データを、指定された条件で並び替える（ascending: 昇順か）"""
    df_sorted = char_df.copy()   # 並び替え用の列を足すので、渡された表とは別の表にする

    # 技能名の未入力の行は、下の _is_unentered で必ず最後に回すので、技能名の順位は他の行と同じ求め方でよい
    if use_char_code_sort:
        sort_key = str
    else:
        sort_key = lambda skill_name: skills.get_skill_sort_rank(skill_name, recalc_rule)
    # 1キャラ分の技能名はほとんど重複しないので、種類ごとにまとめず（results.map_unique の方が遅い）1行ずつ求める
    df_sorted['_skill_rank'] = df_sorted['技能名'].apply(sort_key)
    df_sorted['_is_unentered'] = df_sorted['技能名'] == UNENTERED_SKILL

    by_cols = []
    asc_specs = []

    if sort_check_top:
        by_cols.append('チェック')
        asc_specs.append(False)

    by_cols.append('_is_unentered')
    asc_specs.append(True)

    if "技能名順" in sort_basis:
        by_cols.append('_skill_rank')
        asc_specs.append(ascending)
    elif "総数順" in sort_basis:
        by_cols.append('総数')
        asc_specs.append(ascending)
    elif "合計成功数順" in sort_basis:
        by_cols.append('合計成功数')
        asc_specs.append(ascending)
        
    by_cols.append('_clean_skill_name')
    asc_specs.append(True)
    by_cols.append('目標値')
    asc_specs.append(True)
    
    return df_sorted.sort_values(
        by=by_cols,
        ascending=asc_specs,
        key=lambda col: _target_sort_key(col) if col.name == '目標値' else col)

def _target_sort_key(targets):
    """目標値を数の小さい順に（「変動」は最後に）"""
    return pd.to_numeric(targets, errors='coerce').fillna(float('inf'))

def generate_copy_text(char_df, selected_char):
    """成長チェック一覧のコピペ用テキストを生成する"""
    # 「目標値の違いを無視」を外すと同じ技能が目標値ごとに複数行になるので、1つにまとめる
    growth_skills = list(dict.fromkeys(char_df[char_df['チェック']]['技能名']))
    if not growth_skills:
        return "※成長チェックがついた技能はありません。"

    header = "【成長技能：全体】" if selected_char == ALL_CHAR_NAME else f"【成長技能：{selected_char}】"
    return header + "\n" + "\n".join([f"・{s}" for s in growth_skills])