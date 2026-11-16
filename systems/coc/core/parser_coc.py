"""
CoC のダイスロールの読み取り（1発言からロールの行を作る）。
ココフォリアのログのファイル（HTML・テキスト・JSON・ZIP）を発言に分けるのは core/ccfolia_reader.py で、
ここはその発言ごとに呼ばれる _records_from_message を渡している。
"""
import streamlit as st
import re
import ast
import operator
from core import ccfolia_reader as reader
from core.ccfolia_reader import TAB_MAP
from .data_coc import ZEN2HAN

# ==========================================
# 正規表現パターン
# ==========================================
COMMAND_PATTERN = re.compile(
    # 英単語の一部（「Success CCB」の cc など）をコマンドと見ないよう、直前が英字でないところから探す
    # （繰り返しの「x2 CC」、シークレットの「sCC」は、間に空白がある・s もコマンドに含めるので当てはまる）
    r'(?<![A-Za-z])(?P<command>'
    r'(?:s?CC[^\s]*'       # CC, CCB, CC<=50, CC<=(10+20) など
    r'|s?1?d100[^\s]*'     # 1d100<=50 など
    r'|s?RES[^\s]*'        # RES, RESB など
    r'|s?CBR[^\s]*'        # CBR, CBRB など
    r'))'
    r'\s*(?P<skill>.*?)\s*'
    r'(?=(?:#\d+\s*)?\((?:1d100)<=)',
    re.IGNORECASE 
)
ROLL_PATTERN = re.compile(
    r'\((?:1d100)<=(?P<actual_target>-?\d+(?:,\d+)?)\).*?>' 
    r'(?:\s+(?:(?P<all_rolls>[\d,\s]+)>\s+)?(?P<roll>\d+)(?:\[(?P<each_results>.*?)\])?\s+>)?'
    r'\s+(?P<result>[^\s]+)',
    re.IGNORECASE
)
BP_PATTERN = re.compile(r'ボーナス・ペナルティダイス\[(?P<bp>[-\d]+)\]')
# コマンドの B/P ダイスの数（CC1・CC-1、括弧で書いた CC(1)・CC(-1)）
_CMD_BP = r'(?:[+-]?\d+|\([+-]?\d+\))?'
BASE_PATTERN = re.compile(
    rf'(?:CC[a-z]*{_CMD_BP}|1d100)<=(?P<base_target>\d+)(?P<diff>[chre])?(?P<times>\*)?',
    re.IGNORECASE
)
# 目標値を括弧の式で書いたもの（7版で掛け算するときの書き方。CC<=(13*5)h など）
BASE_EXPR_PATTERN = re.compile(
    rf'(?:CC[a-z]*{_CMD_BP}|1d100)<=\((?P<expr>[\d+\-*/\s]+)\)(?P<diff>[chre])?',
    re.IGNORECASE
)
# 難易度ごとの、元の目標値から実際の目標値への計算（BCDice の Cthulhu7th と同じ）
# （難易度 c はクリティカルでのみ成功なので、ログの実目標値は「(1D100<=0)」になる）
_DIFF_TARGET = {None: lambda t: t, 'r': lambda t: t, 'h': lambda t: t // 2, 'e': lambda t: t // 5, 'c': lambda t: 0}

# 読み込み方の版。読み込み結果が変わる修正をしたら1つ上げる（履歴フォルダのキャッシュが自動で作り直される）
#   2: 2026年10月からのココフォリアのHTMLログ（<article class="message">）に対応
#   3: 同じ形式でタブごとに書き出したログ（発言にタブ名が無い）は、メインタブとして扱う
#   4: 括弧の式で書いた目標値（CC<=(13*5)h）の元の目標値と難易度を読む。ZIP内の同名ファイルを区別する
#   5: 組み合わせロール（CBR）の行ごとの結果、CC(1)<=50h の難易度、英単語の中の cc をコマンドと見ない
#   6: ココフォリアの JSON 出力（.json）を読む
#   7: 括弧の式で書いた難易度 c（CC<=(13*5)c）の元の目標値と難易度を読む
#   8: タブごとに書き出したログのタブ名を題名から読む。ロールごとの番号（_roll_no）・目標値の何番目か（_roll_part）・
#      組み合わせロールの全体の結果（_roll_overall）の列を足す
#   （core/ccfolia_reader.py の読み取りを変えたときも上げる）
PARSER_VERSION = 8

# 1回のロールの何番目の目標値の行か（組み合わせロール CBR(30,60) は目標値ごとに1行になる。0 が1つ目）。
# 同じロールの行を1つに数えるとき（出目の分布、「組み合わせロールの結果を分割」OFF）に使う
ROLL_PART_COL = '_roll_part'
ROLL_NO_COL = '_roll_no'            # ファイルの中でのロールの番号（同じロールの行は同じ番号）
ROLL_OVERALL_COL = '_roll_overall'  # ログに書かれたロール全体の結果（組み合わせロールなら「部分的成功」など）

# ==========================================
# 1. ダイスロール1回分のデータ行を作る
# ==========================================
def _get_command_id(raw_cmd):
    cmd_upper = raw_cmd.upper()
    is_secret = cmd_upper.startswith('S')
    core = cmd_upper[1:] if is_secret else cmd_upper

    for base in ('CBRB', 'CBR', 'RESB', 'RES', 'CCB', 'CC'):
        if core.startswith(base):
            break
    else:
        base = '1D100'   # COMMAND_PATTERN に当てはまるのは上のどれかか 1d100 だけ

    return f"s{base}" if is_secret else base

def _eval_int_expr(expr):
    """「13*5」「50+10」のような整数の式を計算する（割り算は BCDice と同じく切り捨て）。計算できなければ None"""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -ev(node.operand)
        if isinstance(node, ast.BinOp):
            ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv}
            op = ops.get(type(node.op))
            if op:
                return op(ev(node.left), ev(node.right))
        raise ValueError(expr)
    try:
        return ev(ast.parse(expr.replace('/', '//'), mode='eval').body)
    except (SyntaxError, ValueError, ZeroDivisionError, RecursionError):
        return None

def _base_target_and_diff(body, actual_target):
    """コマンドに書かれた元の目標値（技能値）と難易度。分からなければ (None, None)"""
    # 括弧の式を先に見る（BASE_PATTERN だと、後ろのダイスの結果「(1D100<=32)」の方に当たってしまうため）
    e_match = BASE_EXPR_PATTERN.search(body)
    if e_match:
        diff = e_match.group('diff').lower() if e_match.group('diff') else None
        base = _eval_int_expr(e_match.group('expr'))
        # 計算した値と難易度から、ログの実目標値になることを確かめてから使う
        if base is not None and diff in _DIFF_TARGET and _DIFF_TARGET[diff](base) == actual_target:
            return base, diff
        return None, None
    b_match = BASE_PATTERN.search(body)
    # CC<=13*5 のような掛け算は「元の技能値 13」ではないので、元の目標値は実目標値（65）と同じとみなす
    if b_match and not b_match.group('times'):
        diff = b_match.group('diff').lower() if b_match.group('diff') else None
        return int(b_match.group('base_target')), diff
    return None, None

def _message_params(norm_body):
    """発言1つの中で共通の情報（コマンド・B/Pダイス）。複数回ロールでも1回だけ調べる"""
    bp_match = BP_PATTERN.search(norm_body)
    return {
        'cmd_match': COMMAND_PATTERN.search(norm_body),
        'bp_val': int(bp_match.group('bp')) if bp_match else 0,
    }

def _extract_roll_params(match, body, message):
    """正規表現を使って文字列から情報を引っこ抜く"""
    d = match.groupdict()
    cmd_match = message['cmd_match']

    # コマンドが見つからない（結果だけが書かれた）行はロールの取り消し（CANCEL）扱い
    prefix = body[:match.start()].strip()
    cmd_id = 'OTHER' if prefix else 'CANCEL'
    if cmd_match:
        cmd_id = _get_command_id(cmd_match.group('command').strip())

    actual_target_str = d['actual_target']
    if ',' in actual_target_str:
        actual_target_vals = [int(x) for x in actual_target_str.split(',')]
    else:
        actual_target_vals = [int(actual_target_str)]

    base_target, diff = None, None
    if len(actual_target_vals) == 1:
        if 'base' not in message:   # 複数回ロールでも同じなので、1回だけ調べる
            message['base'] = _base_target_and_diff(body, actual_target_vals[0])
        base_target, diff = message['base']

    roll_val = int(d['roll']) if d['roll'] else 0

    return {
        'cmd_id': cmd_id,
        'bp_val': message['bp_val'],
        'base_target': base_target,
        'actual_targets': actual_target_vals,
        'diff': diff,
        'result_str': d['result'],
        'each_results': d.get('each_results'),
        'all_rolls_str': d.get('all_rolls'),
        'roll_val': roll_val
    }

def _build_roll_records(match, norm_body, raw_body, tab, name, message, i=0, multiple_rolls=False, base_cmd=""):
    """1回のロールにつき、目標値の数だけ行（辞書）を作ってリストで返す。message: _message_params の戻り値"""
    cmd_match = message['cmd_match']
    params = _extract_roll_params(match, norm_body, message)

    start, end = match.span()
    raw_log = raw_body

    # 判定名は全角を半角にする前の本文から取る（表示用。比較するときは skills.clean_skill_name で揃える）
    skill_name = '---'
    if cmd_match and cmd_match.group('skill').strip():
        s_start, s_end = cmd_match.span('skill')
        skill_name = raw_body[s_start:s_end].strip()

    if multiple_rolls:
        roll_text = raw_body[start:end]
        raw_log = f"{base_cmd} #{i+1} {roll_text}"
        skill_name = f"{skill_name}#{i+1}"
        
    display_tab = TAB_MAP.get(tab, tab)
    
    # 組み合わせロール（CBR(30,60) → 「30[レギュラー成功,ハード成功] ＞ 成功」）は目標値ごとに1行にし、
    # 結果は全体の結果（部分的成功など）ではなく、その目標値に対する結果にする
    targets = params['actual_targets']
    each = [r.strip() for r in (params['each_results'] or "").split(',')]
    each_results = each if len(targets) > 1 and len(each) == len(targets) else [params['result_str']] * len(targets)

    records = []
    for part, (target_val, result) in enumerate(zip(targets, each_results)):
        records.append({
            'タブ': display_tab, 
            'キャラクター名': name, 
            'コマンド': params['cmd_id'],
            '判定名': skill_name,
            '目標値': params['base_target'] if params['base_target'] is not None else target_val, 
            '実目標値': target_val,
            '難易度': params['diff'] if params['diff'] else '通常',
            'B/P': params['bp_val'], 
            '出目': params['roll_val'],
            '全出目文字列': params['all_rolls_str'],
            '結果': result,
            '生ログ': raw_log,
            '複数ロール': multiple_rolls,
            ROLL_PART_COL: part,
            ROLL_OVERALL_COL: params['result_str'],
        })
    return records


# ==========================================
# 2. チャット1発言からロールの行を作る（core/ccfolia_reader.py から発言ごとに呼ばれる）
# ==========================================
def _extract_base_command(body, first_match):
    base_cmd_raw = body[:first_match.start()].strip()
    return re.sub(r'#\s*1\s*$', '', base_cmd_raw).strip()

def _records_from_message(tab, name, raw_body):
    """チャット1発言分から、含まれるダイスロールの行をすべて作る（ロールが無ければ空）"""
    norm_body = raw_body.translate(ZEN2HAN)
    matches = list(ROLL_PATTERN.finditer(norm_body))
    multiple = len(matches) > 1
    if not matches:
        return []
    base_cmd = _extract_base_command(raw_body, matches[0]) if multiple else ""
    message = _message_params(norm_body)
    records = []
    for i, match in enumerate(matches):
        records.extend(_build_roll_records(match, norm_body, raw_body, tab, name, message, i, multiple, base_cmd))
    return records

# ==========================================
# 3. ログの読み込み（ココフォリアの形式ごとの読み取りは core/ccfolia_reader.py で共通）
# ==========================================
# 同じファイルを読み込み直したときに使い回す（ページを開き直したときなど）。
# 全員で共有されるので、溜まりすぎないように件数と期間に上限を付ける。
# 使い回しはこの関数（CoC の読み込み）ごとなので、ほかのシステムが同じファイルを読んでも混ざらない
@st.cache_data(show_spinner=False, max_entries=128 if reader.IS_LOCAL else 32, ttl="6h" if reader.IS_LOCAL else "1h")
def _process_single_content(fname, content):
    df = reader.parse_content(fname, content, _records_from_message)
    if not df.empty:
        df[ROLL_NO_COL] = (df[ROLL_PART_COL] == 0).cumsum() - 1   # 同じロールの行（目標値ごとの行）は続いて並んでいる
    return df


# ==========================================
# 4. 🌟 外部から呼ばれる窓口
# ==========================================
def parse_files(file_dict):
    """
    読み込んだファイル（ファイル名 → 中身。ZIP も可）をすべて解析して1つの表にする。
    戻り値: (解析結果, 読み込めなかったファイルについての説明のリスト)
    画面への表示はしない（表示は呼び出し側で行う）。
    """
    return reader.parse_files(file_dict, _process_single_content)