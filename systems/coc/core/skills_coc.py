import re
from functools import lru_cache
from . import data_coc as data
from . import rules_coc as rules

# ==========================================
# 技能名の整形と、ルールブックの辞書の照会（初期値・並び順）
# ==========================================
# どれも同じ技能名で何度も呼ばれるので、結果を覚えておく（技能名の種類は数百程度）

def _editions(recalc_rule, prefer_edition=None):
    """引く辞書の版の順番。「再計算しない」では prefer_edition（行のコマンドから判断した版）を先に引く"""
    edition = rules.get_rule(recalc_rule).edition
    if edition is not None:
        return (edition,)
    return (6, 7) if prefer_edition == 6 else (7, 6)

# 公開したときに、いろいろな技能名が来ても覚える数が増え続けないように上限を付ける
_CACHE_SIZE = 4096
# 「心理学｛PC2｝」「近接戦闘[格闘]」の括弧も、（ ）と同じに扱う（括弧の外の技能の初期値を使えるように）
_BRACKETS = str.maketrans({"[": "（", "]": "）", "［": "（", "］": "）", "{": "（", "}": "）", "｛": "（", "｝": "）"})
_PAREN_RE = re.compile(r'^(.*?)（.*）$')      # 「芸術（歌）」→ 括弧の外の「芸術」
_PAREN_HEAD_RE = re.compile(r'^(.*?（)')       # 「運転（自動車）」→ 頭の部分の「運転（」

@lru_cache(maxsize=_CACHE_SIZE)
def clean_skill_name(skill_name):
    """【 】や末尾の番号(#1)、空白を取り除き、全角英数字を半角にして、純粋な名前にする。"""
    name = str(skill_name).translate(data.ZEN2HAN).upper()
    name = re.sub(r'#\d+$', '', name)
    # 【】は外す（「+20【威圧】」のように前に何か付いていても、括弧の片方だけ残らないように両方とも外す）
    name = name.replace('【', '').replace('】', '')
    name = re.sub(r'\s+', '', name)
    name = name.replace("(", "（").replace(")", "）").translate(_BRACKETS)
    name = re.sub(r'[*×xXｘＸ][0-9]+$', '', name)
    if not name:
        return "---"
    return name

@lru_cache(maxsize=_CACHE_SIZE)
def get_initial_value(skill_name, recalc_rule, prefer_edition=None):
    """
    クリーニングされた技能名と再計算ルール（の版）に基づいて、ルールブックに準拠した初期値を返す（辞書に無ければ -1）。
    recalc_rule: 再計算ルールの名前（rules_coc のラベル）
    prefer_edition: 版が1つに決まらないルール（再計算しない など）のとき、どちらの版の初期値を優先するか（6 / 7）
    """
    editions = _editions(recalc_rule, prefer_edition)
    dicts = [data.INITIAL_VALUES_6E if e == 6 else data.INITIAL_VALUES_7E for e in editions]
    paren_dicts = [data.PAREN_INITIAL_VALUES_6E if e == 6 else data.PAREN_INITIAL_VALUES_7E for e in editions]

    for d in dicts:
        if skill_name in d: return d[skill_name]

    # 「芸術（歌）」のような括弧書きは、括弧の外の技能と同じ初期値
    m = _PAREN_RE.match(skill_name)
    if m:
        for d in paren_dicts:
            if m.group(1) in d: return d[m.group(1)]
    # 「SANチェック」「正気度判定」などの表記揺れも、能力値と同じく初期値 0
    if is_sanity_roll(skill_name):
        return 0
    return -1

@lru_cache(maxsize=_CACHE_SIZE)
def get_skill_sort_rank(skill_name, recalc_rule):
    """技能をルールブックの技能表の順に並べるための順位（辞書に無ければ 9999）"""
    clean_name = clean_skill_name(skill_name)
    dicts = [data.SKILL_SORT_ORDER_6E if e == 6 else data.SKILL_SORT_ORDER_7E for e in _editions(recalc_rule)]

    for d in dicts:
        if clean_name in d: return d[clean_name]

    match = _PAREN_HEAD_RE.match(clean_name)
    if match:
        prefix = match.group(1)
        for d in dicts:
            if prefix in d: return d[prefix]

    for d in dicts:
        for k, v in d.items():
            if clean_name.startswith(k): return v
    return 9999

def is_sanity_roll(clean_name):
    """正気度ロールか（クリーニング済みの技能名で判定）"""
    return clean_name in data.SANITY_ROLL_LIST or clean_name.startswith(data.SANITY_ROLL_PREFIXES)
