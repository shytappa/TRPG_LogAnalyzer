"""
ステータス（パラメータ）の増減を、ココフォリアのログから読む部分（どのシステムでも同じ）。

ココフォリアでは、駒のステータスを変えると「[ キャラ名 ] SAN : 50 → 44」のようなシステムのメッセージが残る。
これを順に拾い、押し間違いなどの修正（すぐ逆向きに直したもの）は前の変化と差し引いて1回にまとめる。
どのパラメータを数えるか・何を「回復・ダメージの行為」とみなすかは、各システムから ParamRules で受け取る
（例: systems/coc/core/data_coc.py の PARAM_RULES）。
"""
import re
import bisect
from dataclasses import dataclass

import pandas as pd

from core import ccfolia_reader

# 「[ キャラ名 ] パラメータ : 前 → 後」
CHANGE_PATTERN = re.compile(r'\[\s*(?P<name>.+?)\s*\]\s*(?P<param>[^\s:：\[\]]+)\s*[:：]\s*(?P<before>-?\d+)\s*→\s*(?P<after>-?\d+)')
# ダイスを振った発言（「1d6」「CC<=50 (1D100<=50) ＞ …」など。結果の「＞」があるもの）
ROLL_PATTERN = re.compile(r'\d*[dD]\d+.*[＞>]')

KIND_LOGGED = "記録"          # システムのメッセージとして残っている変化
KIND_UNLOGGED = "手入力"      # 記録に残っていない変化（前の記録の「後」と、次の記録の「前」が食い違っている）

COLUMNS = ["順番", "キャラクター名", "パラメータ", "前", "後", "変化", "種類", "まとめた数", "外れ値"]


@dataclass(frozen=True)
class ParamRules:
    """
    params: ログに書かれる名前 → 集計での名前（例: {"SAN": "SAN", "正気度": "SAN", "HP": "HP"}）。ここに無いものは数えない
    action_pattern: 回復・ダメージの行為とみなすロールの本文（正規表現）。誰のロールでも、これが前の変化との間にあれば修正とみなさない
    threshold: 修正とみなすのは、前の変化から何発言以内か
    outlier: 1回でこれ以上動いた変化は、集計から外す（ふざけた値への切り替えなど）
    """
    params: dict
    action_pattern: str
    threshold: int = 6
    outlier: int = 1000


def _norm(name):
    """名前の比べ方（空白の違いは無視する）"""
    return re.sub(r'\s+', '', name or '')

def extract_changes(messages, rules):
    """
    発言の一覧（タブ, 名前, 本文）から、パラメータの変化の一覧を作る。
    同じキャラ・同じパラメータで、前の変化と逆向きの変化が次の3つをすべて満たすときは「修正」とみなし、前の変化と差し引いて1回にまとめる:
      1. 前の変化から今までに、回復・ダメージの行為（rules.action_pattern に当てはまるロール。誰のものでも）が無い
      2. その間に、そのキャラ自身のロールが無い
      3. 前の変化から rules.threshold 発言以内
    戻り値: COLUMNS の表（1行が、修正をまとめた後の1回の変化）
    """
    action = re.compile(rules.action_pattern)
    rows = []
    last = {}          # (キャラ, パラメータ) → 修正の相手になる直前の変化の行（rows の中の辞書）
    last_value = {}    # (キャラ, パラメータ) → 直前の記録の「後」の値
    rolls = []         # ダイスを振った発言: (順番, 名前（空白なし）, 行為か)
    for idx, (_tab, speaker, body) in enumerate(messages):
        if speaker != ccfolia_reader.SYSTEM_NAME and ROLL_PATTERN.search(body):
            rolls.append((idx, _norm(speaker), bool(action.search(body))))
        for m in CHANGE_PATTERN.finditer(body):
            param = rules.params.get(m.group("param"))
            if param is None:
                continue
            name, before, after = m.group("name"), int(m.group("before")), int(m.group("after"))
            key = (_norm(name), param)
            changes = []
            if key in last_value and last_value[key] != before:
                changes.append((KIND_UNLOGGED, last_value[key], before))
            if before != after:
                changes.append((KIND_LOGGED, before, after))
            last_value[key] = after
            for kind, x, y in changes:
                delta = y - x
                if abs(delta) >= rules.outlier:
                    rows.append(dict(順番=idx, キャラクター名=name, パラメータ=param, 前=x, 後=y, 変化=delta, 種類=kind, まとめた数=1, 外れ値=True))
                    last.pop(key, None)   # 外れ値は修正の相手にしない
                    continue
                prev = last.get(key)
                if prev is not None and (prev["変化"] > 0) != (delta > 0) and _is_fix(prev["順番"], idx, key[0], rolls, rules.threshold):
                    prev.update(順番=idx, 後=y, 変化=prev["変化"] + delta, まとめた数=prev["まとめた数"] + 1)
                    if prev["変化"] == 0:     # 押し間違いをそのまま戻しただけ（変化なし）
                        rows = [r for r in rows if r is not prev]
                        last.pop(key, None)
                    continue
                row = dict(順番=idx, キャラクター名=name, パラメータ=param, 前=x, 後=y, 変化=delta, 種類=kind, まとめた数=1, 外れ値=False)
                rows.append(row)
                last[key] = row
    return pd.DataFrame(rows, columns=COLUMNS)

def _is_fix(prev_idx, idx, name, rolls, threshold):
    """前の変化（prev_idx）から今（idx）までが、修正とみなせる間か（行為・本人のロールが無く、近い）"""
    if idx - prev_idx > threshold:
        return False
    start = bisect.bisect_right(rolls, prev_idx, key=lambda r: r[0])   # rolls は順番の順に並んでいる
    for r_idx, r_name, is_action in rolls[start:]:
        if r_idx >= idx:
            break
        if is_action or r_name == name:
            return False
    return True

def extract_from_files(file_dict, rules):
    """
    読み込んだファイル（ファイル名 → 中身。ZIP も可）すべての、パラメータの変化の一覧（「ファイル名」の列付き）。
    読めないファイルは飛ばす（読み込みの注意は、ロールの読み込みのほうで出している）
    """
    def parse_one(fname, content):
        return extract_changes(ccfolia_reader.log_messages(fname, content, include_system=True), rules)
    df, _ = ccfolia_reader.parse_files(file_dict, parse_one)
    return df if not df.empty else pd.DataFrame(columns=COLUMNS + ["ファイル名"])
