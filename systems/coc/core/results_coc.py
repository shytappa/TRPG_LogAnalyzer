import re
from . import data_coc as data
from . import rules_coc as rules

# ==========================================
# 1. 判定結果の分類（成功・クリティカル・ファンブル）
# ==========================================
_BP_SUFFIX_RE = re.compile(r'（[^（）]*）$')
FAIL_RESULTS = ['失敗', 'ファンブル', '致命的失敗']   # 失敗を表す結果（7版・6版）
# 組み合わせロールの全体の結果で、目標値の片方だけ成功したもの（「組み合わせロールの結果を分割」OFF で出る）。成功に数える
PARTIAL_SUCCESS = '部分的成功'

def primary_result(res_str):
    """
    BP内訳の「A（B）」表記から、その出目単体の結果 A を取り出す（B はロール全体の結果なので判定に使わない）。
    「（救済）」は結果の一部なのでそのまま残す。
    """
    if not isinstance(res_str, str) or res_str.endswith('（救済）'):
        return res_str
    return _BP_SUFFIX_RE.sub('', res_str)

def is_actual_success(res_str):
    """その出目単体の結果が「成功・大成功」かを判定する。"""
    res_str = primary_result(res_str)
    if not isinstance(res_str, str):
        return False
    if any(fail_word in res_str for fail_word in FAIL_RESULTS):
        return False
    return any(x in res_str for x in ['成功', 'クリティカル', 'スペシャル', '（救済）'])   # 「決定的成功」は「成功」で当てはまる

def is_crit(res_str):
    """その出目単体の結果がクリティカル（決定的成功）か"""
    res_str = primary_result(res_str)
    return isinstance(res_str, str) and ('クリティカル' in res_str or '決定的' in res_str)

def is_fumble(res_str):
    """その出目単体の結果がファンブル（致命的失敗）か"""
    res_str = primary_result(res_str)
    return isinstance(res_str, str) and ('ファンブル' in res_str or '致命的' in res_str)

def map_unique(series, func):
    """同じ値が何度も出てくる列に関数を適用する（値の種類ごとに1回だけ計算する）"""
    return series.map({v: func(v) for v in series.unique()})

def map_results(series, func):
    """結果列に判定関数を適用する（結果の種類は少ないので、種類ごとに1回だけ計算する）"""
    return map_unique(series, func).astype(bool)


# ==========================================
# 2. 結果の並び順
# ==========================================
def get_sorted_result(found_results, recalc_rule, include_unfound_base=False):
    """
    結果リストを、ルールブックの成功度の順（クリティカル → … → ファンブル）に並び替える。
    include_unfound_base=True なら、ログに出てこなかった基本の結果も含める（チェックボックスの項目用）。
    """
    edition = rules.get_rule(recalc_rule).edition
    if edition is None:
        always_show = []
    elif edition == 6:
        always_show = ['決定的成功', 'スペシャル', '成功', '失敗', '致命的失敗']
    else:
        always_show = ['クリティカル', 'イクストリーム成功', 'ハード成功', 'レギュラー成功', '失敗', 'ファンブル']

    first_part = [
        r for r in data.CORE_RESULT_ORDER
        if r in found_results or (include_unfound_base and r in always_show)
    ]
    extra = sorted([r for r in found_results if r not in data.CORE_RESULT_ORDER])

    return list(dict.fromkeys(first_part + extra))

def result_options(df, recalc_rule):
    """表の結果の列から、チェックボックスの選択肢（ログに無い基本の結果も含め、成功度の順）を作る"""
    return get_sorted_result(list(df['結果'].unique()), recalc_rule, include_unfound_base=True)

def success_results(result_list):
    """結果のリストのうち「成功」に数えるもの（「成功」の基準の初期値）"""
    return [r for r in result_list if is_actual_success(r)]
