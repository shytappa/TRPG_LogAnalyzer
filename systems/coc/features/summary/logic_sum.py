from dataclasses import dataclass
import pandas as pd
from ...core import data_coc as data
from ...core import results_coc as results
from ...core import rules_coc as rules

# ==========================================
# 1. 定義・初期化（UIに渡す設計図の作成）
# ==========================================
# サマリーの表示形式（画面の選択肢の名前。ここでだけ定義する）
DISPLAY_BOTH = "パーセント ＋ (回数)"
DISPLAY_PCT = "パーセント（％）のみ"
DISPLAY_COUNT = "回数のみ"
DISPLAY_OPTIONS = [DISPLAY_BOTH, DISPLAY_PCT, DISPLAY_COUNT]
OVERALL_LABEL = "全体"   # 表の一番上の、全員を合わせた行の名前（パラメータ増減・出目の分布・自卓用の表も同じ）

# ハイライト・並び替えの基準（割合で比べるか、回数で比べるか）
BASIS_PCT = "確率（％）"
BASIS_COUNT = "回数"
BASIS_OPTIONS = [BASIS_PCT, BASIS_COUNT]

# 目標値から計算した成功率（logic_coc.expected_success を参照）の列と、
# 「期待との差」の列：実際の成功率 − 目標値から計算した成功率（マイナスもある）
EXPECTED_RATE_KEY = "exp_rate_col"
EXPECTED_KEY = "exp_col"
EXPECTED_LABEL = "期待との差"
SIGNED_KEYS = {EXPECTED_KEY}   # 値がマイナスにもなる列（ハイライトで「0より大きい」の条件を使わない）

# 列のグループ分け：先頭のグループ（総数・成功率・期待・クリファン率）は、どの版でも同じ
_FIRST_GROUP = ["総数", "succ_col", EXPECTED_RATE_KEY, EXPECTED_KEY, "cf_col"]
_GROUPS_BY_EDITION = {
    7: [
        ["1_crit", "クリティカル"],
        ["成功"],
        ["失敗", "ファンブル", "100_fumb"],
    ],
    6: [
        ["1_crit", "決定的", "スペシャル", "成功", "クリティカル"],
        ["失敗", "致命的", "ファンブル", "100_fumb"],
    ],
    None: [   # 版が1つに決まらないルール（再計算しない など）
        ["1_crit", "クリティカル", "決定的", "スペシャル"],
        ["成功"],
        ["失敗", "致命的", "ファンブル", "100_fumb"],
    ],
}

@dataclass
class HighlightConfig:
    """マスの強調表示（ハイライト）の設定（ui_sum の「✨ マスの強調表示」で作る）"""
    use_highlight: bool = True    # ハイライト機能を有効にする
    keys: tuple = ()              # 強調する列のキー
    basis: str = BASIS_PCT        # 判定数値（割合か回数か）
    check_max: bool = True        # 最大値を強調する
    check_min: bool = True        # 最小値を強調する
    include_zero: bool = False    # 最小値に 0 (0%) を含める
    tie_count: int | None = None  # 同じ値がこの人数以上いる場合はハイライトしない（None なら制限なし）
    min_rolls: int = 0            # 総数がこの回数未満のキャラはハイライトしない

def _is_bp_key(k):
    """B/Pダイスの内訳の列（「失敗（クリティカル）」など。救済の列は含めない）"""
    return "（" in k and "（救済）" not in k

def raw_col(key, basis):
    """列の値を、割合で見るか回数で見るかの列名（総数の割合は全員100%になるので、総数は判定数値の設定によらず回数）"""
    use_count = basis == BASIS_COUNT or key == "総数"
    return f'_raw_count_{key}' if use_count else f'_raw_pct_{key}'

def get_checkbox_groups(disp_keys, disp_labels, recalc_rule):
    """ルール(版)に応じて、表示項目のグループ分け構造（設計図）を作成する"""
    key_to_label = dict(zip(disp_keys, disp_labels))
    edition = rules.get_rule(recalc_rule).edition
    group_defs = [_FIRST_GROUP] + _GROUPS_BY_EDITION.get(edition, _GROUPS_BY_EDITION[None])

    assigned_keys = set()
    final_groups = []

    # B/Pダイスの内訳（「失敗（クリティカル）」など）は、キーワードで振り分けずに後で専用のグループにまとめる
    for keywords in group_defs:
        group_keys = []
        for word in keywords:
            for k in disp_keys:
                if k not in assigned_keys and not _is_bp_key(k) and (word in k or word in key_to_label[k]):
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


def get_column_definitions(all_results, recalc_rule, display_mode, hide_detail_columns=True, show_expected=False):
    """
    ログに存在する結果を分類し、列のキーとラベルのリストを生成する
    hide_detail_columns: 最初に表示する列から「1クリ」「100ファン」とBP内訳（括弧書き）の列を外すか
    show_expected: 最初に表示する列に「期待との差」を入れるか（期待成功率の列は最初は出さない）
    """
    final_columns = results.get_sorted_result(all_results, recalc_rule, include_unfound_base=True)

    succ_col_name = "成功数" if display_mode == DISPLAY_COUNT else "成功率"
    cf_col_name = "クリファン数" if display_mode == DISPLAY_COUNT else "クリファン率"
    exp_rate_name = "期待成功数" if display_mode == DISPLAY_COUNT else "期待成功率"

    disp_keys = list(dict.fromkeys(["総数", "succ_col", EXPECTED_RATE_KEY, EXPECTED_KEY, "cf_col", "1_crit", "100_fumb"] + final_columns))
    disp_labels = list(dict.fromkeys(["総数", succ_col_name, exp_rate_name, EXPECTED_LABEL, cf_col_name, "1クリ", "100ファン"] + final_columns))
    final_groups, other_keys, key_to_label = get_checkbox_groups(disp_keys, disp_labels, recalc_rule)

    disp_keys = []
    for group in final_groups:
        disp_keys.extend(group)
    disp_keys.extend(other_keys)
    disp_labels = [key_to_label[k] for k in disp_keys]

    if hide_detail_columns:
        default_keys = [k for k in disp_keys if not (k in ["1_crit", "100_fumb"] or _is_bp_key(k))]
    else:
        default_keys = [k for k in disp_keys if "（救済）" not in k]
    default_keys.remove(EXPECTED_RATE_KEY)
    if not show_expected:
        default_keys.remove(EXPECTED_KEY)

    return final_columns, disp_keys, disp_labels, default_keys

# ==========================================
# 2. 集計・計算（メインのデータ処理）
# ==========================================
# 集計表の各列の値は、回数を _raw_count_○○、割合（総数に対する％）を _raw_pct_○○ に入れる（○○は列のキー）。
# 表示（html_sum）・並び替え・ハイライトは、この2つの列だけを使う
def _flag_counts(df_calc, count):
    """
    成功・クリファンなどの回数。count: 印の列（True/False）から回数を求める関数
    （全体なら合計の数、キャラごとならキャラごとの回数の列が返る）。
    戻り値: ({列のキー: 回数}, クリティカルの回数, ファンブルの回数)
    """
    is_crit = df_calc['_is_crit']
    is_fumb = df_calc['_is_fumb']
    crit = count(is_crit)
    fumb = count(is_fumb)
    counts = {
        'succ_col': count(df_calc['_is_success']),
        'cf_col': crit + fumb,
        '1_crit': count((df_calc['出目'] == 1) & is_crit),
        '100_fumb': count((df_calc['出目'] == 100) & is_fumb),
    }
    return counts, crit, fumb


def _row_stats(total, counts, exp_n, exp_sum, exp_hits):
    """全体または1キャラ分の行。counts: 列のキー → 回数（総数は total から入れる）"""
    row = {'総数': total}
    for key, count in {'総数': total, **counts}.items():
        row[f'_raw_count_{key}'] = count
        row[f'_raw_pct_{key}'] = (count / total * 100) if total else 0
    row.update(_expected_fields(exp_n, exp_sum, exp_hits))
    return row


def calc_overall_stats(df_calc, final_columns):
    """全キャラクターを合算した「全体」の行の集計データを生成する"""
    counts, crit_count, fumb_count = _flag_counts(df_calc, lambda flags: flags.sum())
    result_counts = df_calc['結果'].value_counts().to_dict()
    counts.update({col: result_counts.get(col, 0) for col in final_columns})

    overall_data = _row_stats(len(df_calc), counts, df_calc['_exp_p'].count(), df_calc['_exp_p'].sum(), df_calc['_exp_hit'].sum())
    # 上部のメトリクス（html_sum.build_metrics_html）用
    overall_data.update({'crit_count': crit_count, 'fumb_count': fumb_count,
                         'cf_count': counts['cf_col'], 'succ_count': counts['succ_col']})
    return overall_data


def _expected_fields(n, expected, hits):
    """「期待との差」の列の値。n: 対象のロール数, expected: 成功数の期待値, hits: 実際の成功数"""
    nan = float('nan')
    if not n:
        return {f'_raw_count_{EXPECTED_KEY}': nan, f'_raw_pct_{EXPECTED_KEY}': nan,
                f'_raw_count_{EXPECTED_RATE_KEY}': nan, f'_raw_pct_{EXPECTED_RATE_KEY}': nan,
                '_exp_n': 0}
    return {f'_raw_count_{EXPECTED_KEY}': hits - expected, f'_raw_pct_{EXPECTED_KEY}': (hits - expected) / n * 100,
            f'_raw_count_{EXPECTED_RATE_KEY}': expected, f'_raw_pct_{EXPECTED_RATE_KEY}': expected / n * 100,
            '_exp_n': int(n)}


def calc_char_stats(df_calc, final_columns, sort_key, sort_basis, ascending):
    """キャラクターごとのサマリーデータを集計し、指定された条件でソートする（ascending: 昇順か）"""
    names = df_calc['キャラクター名']

    # キャラごとの集計を列単位でまとめて計算する（キャラごとに表を切り出すと遅いため）
    totals = names.value_counts().sort_index()
    by_char = lambda s: s.groupby(names).sum().reindex(totals.index, fill_value=0)
    flag_counts, _, _ = _flag_counts(df_calc, by_char)
    result_counts_all = pd.crosstab(names, df_calc['結果']).reindex(index=totals.index, fill_value=0)
    first_rows = df_calc.drop_duplicates('キャラクター名').set_index('キャラクター名')
    exp_by_char = df_calc.groupby(names)['_exp_p'].agg(['count', 'sum']).reindex(totals.index, fill_value=0)
    exp_hits = by_char(df_calc['_exp_hit'])
    has_orig_name = '統合前のキャラクター名' in df_calc.columns
    has_file_name = 'ファイル名' in df_calc.columns

    char_stats = []
    for char in totals.index:
        counts = {key: by_key[char] for key, by_key in flag_counts.items()}
        result_counts = result_counts_all.loc[char]
        counts.update({col: int(result_counts.get(col, 0)) for col in final_columns})
        char_stats.append({
            'キャラクター名': char,
            '_orig_name': first_rows.at[char, '統合前のキャラクター名'] if has_orig_name else char,
            '_file_name': first_rows.at[char, 'ファイル名'] if has_file_name else None,
            **_row_stats(int(totals[char]), counts, exp_by_char.at[char, 'count'], exp_by_char.at[char, 'sum'], exp_hits[char]),
        })

    df_chars = pd.DataFrame(char_stats)
    if df_chars.empty:
        return df_chars

    if sort_key == "char_name":
        return df_chars.sort_values(by=['キャラクター名'], ascending=ascending)
    return df_chars.sort_values(by=[raw_col(sort_key, sort_basis), 'キャラクター名'], ascending=[ascending, True])


# ==========================================
# 3. 補助計算（ハイライト等）
# ==========================================
def highlight_eligible(df_chars, min_rolls):
    """ハイライトの対象にするキャラ（総数が min_rolls 回以上）"""
    return df_chars['総数'] >= min_rolls

# 強調するマスの決め方（総合サマリー・パラメータ増減・出目の分布で共通。設定欄は components/highlight_coc）
def highlight_extremes(vals, include_zero=False, tie_count=None, signed=False):
    """
    1つの列の値（比べる行だけ）から、強調する (最大値 または None, 最小値 または None)。
    最小値は 0 を除いて選ぶ（include_zero なら含める。signed：マイナスにもなる列は全員から選ぶ）。
    同じ値が tie_count 人以上いれば、その値は強調しない
    """
    vals = vals.dropna()
    if vals.empty:
        return None, None
    c_max = vals.max()
    min_vals = vals if include_zero or signed else vals[vals > 0]
    c_min = min_vals.min() if not min_vals.empty else None
    if tie_count is not None:
        if (vals == c_max).sum() >= tie_count:
            c_max = None
        if c_min is not None and (vals == c_min).sum() >= tie_count:
            c_min = None
    return c_max, c_min

def highlight_kind(value, c_max, c_min, hl, signed=False):
    """
    1マスの強調（"max"・"min"・None）。c_max・c_min は highlight_extremes の値。
    最大は 0 より大きいときだけ（signed：マイナスにもなる列は除く）、最小は最大と違うときだけ強調する
    """
    if hl.check_max and c_max is not None and (c_max > 0 or signed) and value == c_max:
        return "max"
    if hl.check_min and c_min is not None and c_min != c_max and value == c_min:
        return "min"
    return None

def table_highlight_marks(table, hl):
    """
    列ごとの表（パラメータ増減・出目の分布など）で強調するマス {(行の名前, 列): "max" または "min"}。
    全員同じ値の列は強調しない。最大・最小の決め方は総合サマリーと共通（highlight_extremes・highlight_kind）
    """
    marks = {}
    if not hl.use_highlight:
        return marks
    for col in hl.keys:
        if col not in table.columns:
            continue
        vals = table[col].dropna()
        if len(vals) < 2 or vals.max() == vals.min():
            continue
        c_max, c_min = highlight_extremes(vals, hl.include_zero, hl.tie_count)
        for name, v in vals.items():
            kind = highlight_kind(v, c_max, c_min, hl)
            if kind:
                marks[(name, col)] = kind
    return marks

def get_min_max(df_chars, displayable_columns_keys, include_zero, disable_tie_count=None, min_rolls=0):
    """
    ハイライト（色付け）の基準となる列ごとの最大値・最小値を計算する（総数が min_rolls 回未満のキャラは含めない）。
    戻り値: ({判定数値: {列のキー: 最大値}}, {判定数値: {列のキー: 最小値}})。総数はどちらの判定数値でも回数で比べる（raw_col）
    """
    max_dict = {basis: {} for basis in BASIS_OPTIONS}
    min_dict = {basis: {} for basis in BASIS_OPTIONS}
    if df_chars.empty: return max_dict, min_dict
    df_chars = df_chars[highlight_eligible(df_chars, min_rolls)]

    for k in displayable_columns_keys:
        for basis in BASIS_OPTIONS:
            # 最小値は、マイナスにもなる列なら 0 の扱いの設定によらず全員から選ぶ
            max_dict[basis][k], min_dict[basis][k] = highlight_extremes(
                df_chars[raw_col(k, basis)], include_zero, disable_tie_count, signed=k in SIGNED_KEYS)
    return max_dict, min_dict