import re
from dataclasses import dataclass, field
from functools import lru_cache
import numpy as np
import pandas as pd
from core.logic_base import FilterParams, NO_DICE_COL, ORIG_FILE_COL, rolled_mask
from . import skills_coc as skills
from . import results_coc as results
from . import conditions_coc as conditions
from . import data_coc as data
from . import rules_coc as rules

# ==========================================
# 1. 再計算用の計算エンジン
# ==========================================
def _success_6e(rolls, targets):
    """6版の成否（BCDice の Cthulhu と同じく、目標値以下で、出目100は目標値が100以上でも失敗）"""
    return (rolls <= targets) & (rolls < 100)

def _calculate_results(rolls, base_targets, actual_targets, rule, index):
    """
    出目と目標値から成功度を判定する（全行をまとめて計算する）。
    - 成功／失敗の境目は難易度・補正適用後の目標値（実目標値）、成功度の段階は元の目標値で決める
      （例: CC<=50h で出目8 → 25以下なので成功、50の1/5以下なのでイクストリーム成功）
      （例: CCB<=80-10 で出目15 → 70以下なので成功、80の1/5以下なのでスペシャル）
    - ファンブル値は実目標値で判定する（BCDiceと同じ）
    - 6版は BCDice の CCB と同じく、決定的成功は成功したときだけ、致命的失敗は失敗したときだけ。
      出目100は目標値が100以上でも失敗（_success_6e）
      （「決定的成功/スペシャル」のような両方を満たす結果は作らず、決定的成功を優先する）
    - 難易度を無視して判定したいとき（救済の判定用）は actual_targets に base_targets を渡す
    """
    r = np.asarray(rolls)
    base = np.asarray(base_targets)
    actual = np.asarray(actual_targets)
    fumble_threshold = rule.fumble_threshold(actual)

    # 上から順に判定し、最初に当てはまったものを採用する
    if rule.edition != 6:
        conds = [r >= fumble_threshold, r <= rule.crit, r > actual, r <= base // 5, r <= base // 2]
        labels = ['ファンブル', 'クリティカル', '失敗', 'イクストリーム成功', 'ハード成功']
        default = 'レギュラー成功'
    else:
        succ = _success_6e(r, actual)
        conds = [succ & (r <= rule.crit), ~succ & (r >= fumble_threshold), ~succ, r <= base // 5]
        labels = ['決定的成功', '致命的失敗', '失敗', 'スペシャル']
        default = '成功'
    return pd.Series(np.select(conds, labels, default=default), index=index, dtype=object)

def _calculate_by_rule(rolls, base_targets, actual_targets, rule, df):
    """_calculate_results を、行ごとの版の違い（コマンドで版を判定するルール）も含めて行う"""
    if rule.by_command is None:
        return _calculate_results(rolls, base_targets, actual_targets, rule, df.index)
    is_6e = is_6e_rows(df).to_numpy()
    is_6e_1pct = is_6e_1pct_rows(df).to_numpy()
    rolls, base_targets, actual_targets = np.asarray(rolls), np.asarray(base_targets), np.asarray(actual_targets)
    out = pd.Series(None, index=df.index, dtype=object)
    # 版ごとに、その版の行だけを計算する（6版の CC・CBR・RES は、CCB などと違ってクリファン1%）
    rule_7e, rule_6e, rule_6e_1pct = rule.by_command
    for mask, edition_rule in ((~is_6e, rule_7e), (is_6e & ~is_6e_1pct, rule_6e), (is_6e_1pct, rule_6e_1pct)):
        if mask.any():
            out[mask] = _calculate_results(rolls[mask], base_targets[mask], actual_targets[mask], edition_rule, df.index[mask])
    return out

def _edition_rules(rule):
    """
    (7版の行に使うルール, 6版の行に使うルール)。「再計算しない」は各版の標準ルール。
    成功確率（expected_success）と難易度 c の判定に使う
    """
    if rule.by_command is not None:
        # 6版の成否は目標値だけで決まる（クリファン値で変わらない）ので、6版の CC も CCB と同じルールでよい
        rule_7e, rule_6e, _ = rule.by_command
        return rule_7e, rule_6e
    if rule.recalc:
        return rule, rule
    return rules.R7, rules.R6


# ==========================================
# 2. 前処理パイプライン（パース直後に実行される）
# ==========================================
# BCDice の6版（Cthulhu）と7版（Cthulhu7th）のコマンド（ココフォリアの両方の部屋で確かめたもの）:
#   6版だけ：CCB・CBRB・RES・RESB（7版の部屋では振れない）
#   両方：CC（7版の出力には必ず SEVENTH_EDITION_MARK が付く）・CBR（結果の書き方で見分ける）
SIXTH_EDITION_COMMANDS = r'CCB|CBRB|RES'   # RESB も含む
# 7版（Cthulhu7th）の CC の出力には必ず付く表記。6版でも使える CC や、1D100・取り消しの行の版を、これで見分ける
SEVENTH_EDITION_MARK = 'ボーナス・ペナルティダイス['
# 組み合わせロール（CBR）の目標値ごとの結果に出てくる、その版だけの成功度
_CBR_7E_WORDS = r'\[[^\]]*(?:レギュラー|ハード|イクストリーム|クリティカル|ファンブル)'
_CBR_6E_WORDS = r'\[[^\]]*(?:スペシャル|決定的|致命的)'
IS_6E_COL = '_is_6e'             # 6版として扱う行か（前処理で1回だけ求めて持っておく）
IS_6E_1PCT_COL = '_is_6e_1pct'   # そのうち、クリファン1%の6版のコマンド（CC・CBR・RES。B の付かないもの）の行か

def _log_contains(df, pattern, regex=True):
    if '生ログ' not in df.columns:
        return pd.Series(False, index=df.index)
    return df['生ログ'].astype(str).str.contains(pattern, regex=regex)

def _command(df):
    """コマンド（シークレットの s を除いて大文字にしたもの）"""
    return df['コマンド'].astype(str).str.upper().str.removeprefix('S')

_CMDS_1PCT = ['CC', 'CBR', 'RES']      # 6版で B の付かない（クリファン1%の）コマンド
_CMDS_5PCT = ['CCB', 'CBRB', 'RESB']   # 6版で B の付く（クリファン5%の）コマンド

def is_6e_1pct_rows(df):
    """
    6版の行のうち、クリファン1%で判定する行。
    - B の付かないコマンド（CC・CBR・RES）の行
    - 1D100・取り消しなど、コマンドでは決まらない行は、同じファイルの6版の行で
      CC・CBR・RES の方が CCB・CBRB・RESB より多ければ1%（同数・どちらも無ければ5%）
    """
    if IS_6E_1PCT_COL in df.columns:
        return df[IS_6E_1PCT_COL]
    if 'コマンド' not in df.columns:
        return pd.Series(False, index=df.index)
    is_6e = is_6e_rows(df)
    cmd = _command(df)
    is_1pct = is_6e & cmd.isin(_CMDS_1PCT)
    is_5pct = is_6e & cmd.isin(_CMDS_5PCT)
    undecided = is_6e & ~is_1pct & ~is_5pct
    if not undecided.any() or 'ファイル名' not in df.columns:
        return is_1pct
    votes = (is_1pct.astype(int) - is_5pct.astype(int)).groupby(df['ファイル名']).transform('sum')
    return is_1pct | (undecided & (votes > 0))

def is_6e_rows(df):
    """
    6版として扱う行。
    - 6版だけのコマンド（CCB・CBRB・RES・RESB）、7版の表記（ボーナス・ペナルティダイス[n]）の無い CC、
      結果に6版の成功度（スペシャルなど）が出ている CBR の行は6版。
    - 7版の表記がある行と、結果に7版の成功度（レギュラー成功など）が出ている CBR の行は7版。
    - それ以外（1D100・取り消し、両方とも「成功／失敗」だけの CBR など）は、
      同じファイルで6版の行の方が多いファイルの行なら6版（同数・どちらも無いときは7版）
    """
    if IS_6E_COL in df.columns:
        return df[IS_6E_COL]   # 前処理で求めておいた値
    if 'コマンド' not in df.columns:
        return pd.Series(False, index=df.index)
    cmd = _command(df)
    has_mark = _log_contains(df, SEVENTH_EDITION_MARK, regex=False)
    is_cbr = cmd == 'CBR'
    is_6e = (cmd.str.contains(SIXTH_EDITION_COMMANDS) | ((cmd == 'CC') & ~has_mark)
             | (is_cbr & _log_contains(df, _CBR_6E_WORDS)))
    is_7e = ~is_6e & (has_mark | (is_cbr & _log_contains(df, _CBR_7E_WORDS)))
    neutral = ~is_6e & ~is_7e
    if not neutral.any() or 'ファイル名' not in df.columns:
        return is_6e
    votes = (is_6e.astype(int) - is_7e.astype(int)).groupby(df['ファイル名']).transform('sum')
    return is_6e | (neutral & (votes > 0))

def _set_initial_values(df, recalc_rule):
    df_new = df.copy()
    df_new[IS_6E_COL] = is_6e_rows(df_new)
    df_new[IS_6E_1PCT_COL] = is_6e_1pct_rows(df_new)
    df_new['判定名'] = df_new['判定名'].astype(str)
    df_new['_clean_skill_name'] = results.map_unique(df_new['判定名'], skills.clean_skill_name)
    names = df_new['_clean_skill_name']
    df_new['初期値'] = results.map_unique(names, lambda x: skills.get_initial_value(x, recalc_rule))

    # 版が1つに決まらないルール（再計算しない・コマンドで版を判定）では、6版のコマンドの行は6版の初期値を使う
    if rules.get_rule(recalc_rule).edition is None:
        is_6e = is_6e_rows(df_new)
        if is_6e.any():
            init_6e = results.map_unique(names[is_6e], lambda x: skills.get_initial_value(x, recalc_rule, prefer_edition=6))
            df_new.loc[is_6e, '初期値'] = init_6e

    if 'コマンド' in df_new.columns:
        # （_command で整えなくても、「s」付き・大文字小文字の違いはこの判定に影響しない。整える方が遅いので、そのまま探す）
        mask = df_new['コマンド'].str.contains('CBR|RES|CANCEL', na=False)
        df_new.loc[mask, '初期値'] = -1

    df_new['_init_unknown'] = df_new['初期値'] < 0
    return df_new

def is_broken(result_col):
    """6版の故障ナンバーで、ログの結果が「故障」「致命的失敗/故障」になったロール"""
    return result_col.astype(str).str.contains('故障', regex=False)

def is_bp_roll(df):
    """ボーナス・ペナルティダイスで複数の出目を振ったロールか"""
    s = df['全出目文字列']
    return s.notna() & s.astype(str).str.contains(',', regex=False)

def _expand_bp_rolls(df, extract_bp):
    if not extract_bp or '全出目文字列' not in df.columns: return df
    df_new = df.copy()
    df_new['_roll_id'] = np.arange(len(df_new))   # 展開しても、元の1回のロールが分かるように
    is_bp = is_bp_roll(df_new)
    rolls = [[r] for r in df_new['出目']]
    for i, s in zip(np.flatnonzero(is_bp.to_numpy()), df_new.loc[is_bp, '全出目文字列']):
        rolls[i] = [int(r.strip()) for r in str(s).split(',')]
    df_new['_roll_list'] = rolls
    df_new['_bp_adopted_roll'] = df_new['出目']
    df_new = df_new.explode('_roll_list', ignore_index=True)
    df_new['出目'] = df_new['_roll_list'].astype(int)

    is_bp = is_bp_roll(df_new)
    df_new.loc[is_bp, '生ログ'] = [f"{log} (BP抽出: {r})" for log, r in zip(df_new.loc[is_bp, '生ログ'], df_new.loc[is_bp, '出目'])]
    return df_new

def _critical_only_targets(df, targets, rule_7e):
    """
    難易度 c（CC<=50c：クリティカルでのみ成功）のロールは、成功に必要な値をクリティカル値にする。
    難易度は7版にしか無いので、7版の行に使うルール（_edition_rules の1つ目）のクリティカル値を使う
    """
    is_c = df['難易度'] == 'c'
    if not is_c.any():
        return targets
    return targets.where(~is_c, rule_7e.crit)

def _rescue(res, rolls, base_t, has_diff, calc_rule, df):
    """
    救済：難易度には届かなかったが、元の目標値なら成功していたロール。
    戻り値: (救済になる行, その行の「○○（救済）」の結果のリスト)
    """
    base_res = _calculate_by_rule(rolls, base_t, base_t, calc_rule, df)    # 難易度を無視した結果
    mask = has_diff & res.isin(results.FAIL_RESULTS) & results.map_results(base_res, results.is_actual_success)
    return mask, [f"{b}（救済）" for b in base_res[mask]]

def _recalculate_results(df, recalc_rule, rescue_diff):
    df_new = df.copy()
    rule = rules.get_rule(recalc_rule)
    is_bp_extracted = '_bp_adopted_roll' in df_new.columns
    # 「再計算しない」でもBP内訳の出目単体の結果はログに無いため、7版標準ルールで計算する（BPは7版にしか無い）
    calc_rule = rule if rule.recalc else rules.R7

    log_res = df_new['結果']
    rolls = df_new['出目']
    base_t = df_new['目標値']
    actual_t = _critical_only_targets(df_new, df_new['実目標値'], _edition_rules(calc_rule)[0])
    adopted = df_new['_bp_adopted_roll'] if is_bp_extracted else rolls
    is_bp = is_bp_roll(df_new)
    # 難易度指定(h/e)に加え、目標値の補正（CCB<=80-10、CC<=60/2 など）も難易度と同様に扱い、救済の対象にする
    has_diff = (df_new['難易度'] != '通常') | (base_t != actual_t)

    row_res = _calculate_by_rule(rolls, base_t, actual_t, calc_rule, df_new)       # その出目単体（難易度あり）
    overall_res = _calculate_by_rule(adopted, base_t, actual_t, calc_rule, df_new) if rule.recalc else log_res  # ロール全体として採用された結果
    final = row_res.copy()

    # 1. B/Pダイスの内訳：出目単体の結果と、ロール全体の結果が異なれば併記する
    bp_mask = is_bp & (row_res != overall_res)
    final[bp_mask] = [f"{a}（{b}）" for a, b in zip(row_res[bp_mask], overall_res[bp_mask])]

    # 2. 救済オプション：難易度には届かなかったが、元の目標値なら成功していた（BP併記より優先）
    rescue_mask = pd.Series(False, index=df_new.index)
    if rescue_diff and rule.recalc:
        rescue_mask, rescued = _rescue(row_res, rolls, base_t, has_diff, calc_rule, df_new)
        final[rescue_mask] = rescued
        # ロール全体の結果（B/Pダイスで採用された出目）にも救済を付ける（成長チェックで「ロール全体の結果で判定」するとき用）
        overall_rescue, overall_rescued = _rescue(overall_res, adopted, base_t, has_diff, calc_rule, df_new)
        overall_res = overall_res.copy()
        overall_res[overall_rescue] = overall_rescued

    # 3. 再計算しない：ログの結果をそのまま使う（BP内訳の採用されなかった出目だけ、上で求めた単体結果を使う）
    if not rule.recalc:
        keep_log = ~(is_bp & is_bp_extracted) | (rolls == adopted)
        final[keep_log] = log_res[keep_log]

    # 4. 対抗ロールの自動成功・自動失敗はログの通り（ダイスを振っていないので、出目に関わる機能では除く）
    res_auto = pd.Series(False, index=df_new.index)
    if 'コマンド' in df_new.columns:
        # （「s」付きのコマンドも RES を含むので、_command で整えずに探す。整える方が遅い）
        res_auto = df_new['コマンド'].astype(str).str.contains('RES', regex=False) & log_res.astype(str).str.contains('自動', regex=False)
        final[res_auto] = log_res[res_auto]
    df_new[NO_DICE_COL] = res_auto
    # 5. 6版の故障ナンバー（CC90<=80 の 90）は補助の数字なので、結果は「故障」ではなく目標値で決める。
    #    再計算するルールでは上で計算済み。再計算しないときも、6版のルール（B の付くコマンドは5%）で決める
    broken = is_broken(log_res)
    if broken.any() and not rule.recalc:
        is_b = _command(df_new).str.endswith('B')
        for mask, edition_rule in ((broken & ~is_b, rules.R6), (broken & is_b, rules.R6_CF5)):
            if mask.any():
                final[mask] = _calculate_results(rolls[mask], base_t[mask], actual_t[mask], edition_rule, df_new.index[mask])

    df_new['結果'] = final.astype(log_res.dtype)   # 元の列と同じ型（文字列型）に揃える
    # 「通常結果に統合」で表記が消えても成長チェックなどで使えるよう、ロール全体の結果と救済の有無を残しておく
    df_new['_roll_result'] = overall_res.where(is_bp & is_bp_extracted, df_new['結果'])
    df_new['_is_rescued'] = rescue_mask
    return df_new

from .parser_coc import ROLL_PART_COL, ROLL_NO_COL, ROLL_OVERALL_COL   # 読み込むときに作る列（名前は parser_coc の1か所で決める）

def first_row_of_each_roll(df):
    """
    1回のロールにつき1行にする（組み合わせロールの目標値ごとの行のうち、残っている最初の1行だけ）。
    B/Pダイスの内訳を抽出した行は、出目ごとの行なので全部残す。キャラ統合で同じロールを2つの統合に入れたときは、統合ごとに残す
    """
    if ROLL_PART_COL not in df.columns or ROLL_NO_COL not in df.columns:
        return df
    parts = df[ROLL_PART_COL].fillna(0)
    if not (parts > 0).any():
        return df
    file_col = ORIG_FILE_COL if ORIG_FILE_COL in df.columns else 'ファイル名'
    first_part = parts.groupby([df[file_col], df[ROLL_NO_COL], df['キャラクター名']], dropna=False).transform('min')
    return df[parts == first_part]

def _merge_combined_rolls(df):
    """
    「組み合わせロールの結果を分割」を OFF にしたとき：組み合わせロール（CBR(30,60) など。目標値ごとに行がある）を1行にまとめる。
    結果はログに書かれたロール全体の結果（成功・部分的成功・失敗）。目標値は大きい方
    （「部分的成功」も成功に数えるので、成功する出目の範囲は大きい方の目標値まで）
    """
    if not {ROLL_PART_COL, ROLL_NO_COL, ROLL_OVERALL_COL, 'ファイル名'} <= set(df.columns):
        return df
    parts = df[ROLL_PART_COL].fillna(0)
    if not (parts > 0).any():
        return df
    keys = [df['ファイル名'], df[ROLL_NO_COL]]
    is_multi = parts.groupby(keys).transform('max') > 0
    out = df.copy()
    for col in ('目標値', '実目標値'):
        out[col] = out[col].where(~is_multi, df.groupby(keys)[col].transform('max'))
    first = parts == 0
    out, is_multi = out[first], is_multi[first]
    for col in ('結果', '_roll_result'):
        if col in out.columns:
            out.loc[is_multi, col] = out.loc[is_multi, ROLL_OVERALL_COL]
    if '_is_rescued' in out.columns:
        out.loc[is_multi, '_is_rescued'] = False
    return out

# 外部から呼ばれる「前処理」の窓口（結果は app_coc がセッションの中で使い回す）
def preprocess_raw_data(df, extract_bp, rescue_diff, recalc_rule, split_combined=True):
    """
    パース直後の生データに対し、再計算と展開を行う。
    split_combined: 組み合わせロールを目標値ごとに数えるか（サイドバーの「組み合わせロールの結果を分割」。False なら1回のロールとして1行）
    """
    if df.empty:
        return df

    df = _set_initial_values(df, recalc_rule)
    df = _expand_bp_rolls(df, extract_bp)
    df = _recalculate_results(df, recalc_rule, rescue_diff)
    if not split_combined:
        df = _merge_combined_rolls(df)
    return df


# ==========================================
# 3. 後処理パイプライン（フィルター時に実行される）
# ==========================================
@dataclass
class CocFilterParams(FilterParams):
    """CoCのサイドバーの絞り込み条件（共通の条件に、初期値とダイスコマンドの条件を足したもの）"""
    req_init_succ: bool = False                      # 初期値以下の出目のみを含める
    unk_behav: str = conditions.UNK_USE_TARGET       # 辞書にない技能の扱い
    command: conditions.CommandFilter = field(default_factory=conditions.CommandFilter)
    target: conditions.TargetFilter | None = None    # 目標値の絞り込み（None なら絞り込まない）

def _add_initial_value_flag(df):
    """
    初期値以下の出目だった印（成長チェックの🌱初期値以下・生ログの色分け用）。
    絞り込みと同じ判定（conditions.under_initial_mask）で、初期値が分からない技能には付けない（そちらは「❓初期値不明」と表示する）
    """
    if '初期値' not in df.columns or '_init_unknown' not in df.columns:
        return df
    df_filtered = df.copy(deep=False)
    df_filtered['_is_under_init'] = conditions.under_initial_mask(df_filtered, conditions.UNK_NEVER)
    return df_filtered

def _initial_value_filter(df, params):
    if not params.req_init_succ or '初期値' not in df.columns or '_init_unknown' not in df.columns:
        return df
    return df[conditions.under_initial_mask(df, params.unk_behav)]

# 🌟 外部から呼ばれる「後処理」の窓口
def apply_coc_specific_filters(df, params):
    """共通フィルター後のCoC専用調整を行う（params: CocFilterParams）"""
    df = _add_initial_value_flag(df)
    df = df[conditions.command_mask(df, params.command) & conditions.target_mask(df, params.target)]   # コマンド・難易度・B/P・複数ロール・目標値
    df = _initial_value_filter(df, params)
    return df


# ==========================================
# 4. 結果の表記の統合（サイドバーの成功度フィルターより前に実行する）
# ==========================================
def integrate_results(df, chk_int_bp, chk_int_rescue):
    """
    「B/Pダイスの内訳を通常結果に統合」「救済結果を通常結果に統合」：
    「クリティカル（イクストリーム成功）」→「クリティカル」、「ハード成功（救済）」→「ハード成功」のように表記をまとめる。
    成功度フィルターの選択肢も統合後の表記になるよう、絞り込みの前に行う。
    """
    if df.empty or (not chk_int_bp and not chk_int_rescue):
        return df

    def integrate(label):
        if not isinstance(label, str):
            return label
        if chk_int_rescue:
            label = label.replace('（救済）', '')
        if chk_int_bp:
            label = _BP_PART_RE.sub('', label)
        return label

    df_new = df.copy(deep=False)   # 結果の列を置き換えるだけなので、中身までは複製しない
    # 成長チェックの「ロール全体の結果で判定」が使う _roll_result も同じようにまとめる
    for col in ('結果', '_roll_result'):
        if col in df_new.columns:
            # 結果の種類は少ないので、種類ごとに1回だけ変換する
            df_new[col] = results.map_unique(df_new[col], integrate).astype(df_new[col].dtype)
    return df_new

# 「通常結果に統合」で外す B/P の内訳（「（ハード成功）」など）
_BP_PART_RE = re.compile(r'（(?:' + '|'.join(data.BASIC_RESULT_TERMS) + r')）')


# ==========================================
# 5. 目標値から見た成功確率（「期待との差」用）
# ==========================================
def _success_prob(targets, rule):
    """目標値（難易度・補正後）で振ったときに成功する確率（0〜1）"""
    a = np.clip(targets, 0, 100)
    if rule.edition == 6:
        # 6版は目標値以下なら成功（決定的成功・致命的失敗は成否を変えない）。出目100は必ず失敗なので最大99%
        return np.minimum(a, 99) / 100
    f = rule.fumble_threshold(a)
    return np.maximum(rule.crit, np.minimum(a, f - 1)) / 100   # 7版はクリティカルなら必ず成功、ファンブルなら必ず失敗

def _success_hit(rolls, targets, rule):
    """目標値（難易度・補正後）に対して成功したか（救済は含めない）"""
    if rule.edition == 6:
        return _success_6e(rolls, targets)
    return (rolls <= rule.crit) | ((rolls <= targets) & (rolls < rule.fumble_threshold(targets)))

@lru_cache(maxsize=64)
def _bp_roll_distribution(bp):
    """
    ボーナス（bp > 0）・ペナルティ（bp < 0）ダイスを bp 個使ったときの、採用される出目（1〜100）の確率（添字が出目）。
    一の位は1個、十の位は bp+1 個振り、ボーナスなら小さい方・ペナルティなら大きい方を採用する（「00」と「0」は100）
    """
    n_tens = abs(bp) + 1
    dist = np.zeros(101)
    for unit in range(10):
        # この一の位のときに出うる値（十の位 0〜9）を小さい順に
        values = sorted(100 if (t == 0 and unit == 0) else t * 10 + unit for t in range(10))
        if bp < 0:
            values = values[::-1]
        # 採用されるのが j 番目の値 ＝ 全部が j 番目以降で、全部が j+1 番目以降ではない
        for j, v in enumerate(values):
            dist[v] += (((10 - j) / 10) ** n_tens - ((9 - j) / 10) ** n_tens) / 10
    return dist

def _success_prob_bp(targets, rule, bp):
    """B/Pダイスを使ったときの成功確率（目標値ごと）"""
    dist = _bp_roll_distribution(int(bp))
    values = np.arange(101)
    probs = {t: dist[_success_hit(values, t, rule)].sum() for t in np.unique(targets)}
    return np.array([probs[t] for t in targets])

def expected_success(df, recalc_rule, rescue=False):
    """
    各ロールの成功確率と、実際に成功したかを返す: (確率の列, 成功したかの列)。
    確率は再計算ルールの版・クリファン値で計算する（「再計算しない」は行のコマンドの版の標準ルール）。
    - B/Pダイスのロールは、B/Pダイスを使ったときの確率で計算する。B/Pの内訳を抽出している行は、その出目1つ分（B/Pなしと同じ確率）
    - 対抗ロールの自動成功・自動失敗（ダイスを振っていない）は、確率 100%・0% として数える
    - rescue: 救済（難易度に届かなくても、元の目標値なら成功）を成功に含めるか（サイドバーの救済の設定。成功率と揃える）
    目標値の分からないロールは対象外で、確率が NaN になる。
    """
    rule = rules.get_rule(recalc_rule)
    rule_7e, rule_6e = _edition_rules(rule)
    targets = _critical_only_targets(df, pd.to_numeric(df['実目標値'], errors='coerce'), rule_7e)
    if rescue and rule.recalc:
        targets = np.maximum(targets, pd.to_numeric(df['目標値'], errors='coerce'))   # 救済で成功になる値まで
    rolls = pd.to_numeric(df['出目'], errors='coerce')
    is_6e = is_6e_rows(df)
    valid = targets.notna() & rolls.notna()
    t = targets.fillna(0).clip(0, 100).astype(int)

    prob = pd.Series(_success_prob(t, rule_6e), index=df.index).where(is_6e, _success_prob(t, rule_7e))
    hit = pd.Series(_success_hit(rolls, t, rule_6e), index=df.index).where(is_6e, _success_hit(rolls, t, rule_7e))

    # B/Pダイス：内訳を抽出していないときは、採用された出目の確率（ボーナスなら上がり、ペナルティなら下がる）
    bp = df['B/P'].fillna(0).astype(int) if 'B/P' in df.columns else pd.Series(0, index=df.index)
    extracted = is_bp_roll(df) &('_bp_adopted_roll' in df.columns)
    for value in bp[(bp != 0) & ~extracted].unique():
        rows = (bp == value) & ~extracted
        p6 = _success_prob_bp(t[rows].to_numpy(), rule_6e, value)
        p7 = _success_prob_bp(t[rows].to_numpy(), rule_7e, value)
        prob[rows] = np.where(is_6e[rows], p6, p7)

    # 対抗ロールの自動成功・自動失敗
    no_dice = ~rolled_mask(df)
    if no_dice.any():
        auto_success = results.map_results(df.loc[no_dice, '結果'], results.is_actual_success)
        prob[no_dice] = auto_success.astype(float)
        hit[no_dice] = auto_success
        valid |= no_dice & targets.notna()
    return prob.where(valid), hit.astype(bool) & valid