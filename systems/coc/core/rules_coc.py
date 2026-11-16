from dataclasses import dataclass
import numpy as np

# ==========================================
# 判定の再計算ルール定義
# ==========================================
# ルール名（UIの表示名）はここでのみ定義し、他のファイルでは文字列を直書きしない。
# session_state やキャッシュにはラベル文字列を渡し、ロジック側で get_rule() で解決する。

@dataclass(frozen=True)
class RecalcRule:
    label: str                      # UIに表示する名前
    edition: int | None             # 7 / 6 / None(再計算しない・行のコマンドで決める)
    crit: int | None = None         # この出目以下でクリティカル（決定的成功）
    fumble: int | None = None       # この出目以上でファンブル（致命的失敗）
    fumble_low: int | None = None   # 目標値50未満のときのファンブル値（7版標準）。None なら常に fumble を使う
    # 行のコマンドで版を決めて再計算するとき：(7版の行に使うルール, 6版の行に使うルール, 6版の CC・CBR・RES の行に使うルール)
    by_command: tuple | None = None

    @property
    def recalc(self):
        """出目から結果を再計算するか"""
        return self.edition is not None or self.by_command is not None

    def fumble_threshold(self, targets):
        """ファンブル値。targets（目標値）は1つの数でも、全行分の配列でもよい"""
        if self.fumble_low is None:
            return self.fumble
        return np.where(np.asarray(targets) < 50, self.fumble_low, self.fumble)


R7        = RecalcRule("7版ルールで再計算", 7, crit=1, fumble=100, fumble_low=96)
R7_CF5    = RecalcRule("クリファン5%（7版）で再計算", 7, crit=5, fumble=96)
R6        = RecalcRule("6版ルールで再計算", 6, crit=1, fumble=100)
R6_CF5    = RecalcRule("クリファン5%（6版）で再計算", 6, crit=5, fumble=96)
# CCB など6版のコマンドの行は6版、それ以外の行は7版で再計算する（版が混ざったログ用）。
# CCB は BCDice でクリティカル・ファンブルが上下5%のコマンドなので、6版の行はクリファン5%で判定する。
# 6版の部屋で振った CC・CBR・RES（B の付かないコマンド）は、BCDice の6版と同じくクリファン1%
AUTO      = RecalcRule("コマンドで版を判定して再計算", None, by_command=(R7, R6_CF5, R6))
AUTO_CF5  = RecalcRule("クリファン5%（コマンドで版を判定）で再計算", None, by_command=(R7_CF5, R6_CF5, R6_CF5))
NO_RECALC = RecalcRule("再計算しない (ログの通り)", None)   # 結果はログの文字列を使うため閾値なし

RULES = [R7, R7_CF5, R6, R6_CF5, AUTO, AUTO_CF5, NO_RECALC]   # サイドバーの表示順
RULE_LABELS = [r.label for r in RULES]
DEFAULT_RULE = R7

_RULE_BY_LABEL = {r.label: r for r in RULES}

def get_rule(label):
    """ラベル文字列から RecalcRule を返す。未定義の名前は KeyError にして、名前のずれを即座に検出する"""
    return _RULE_BY_LABEL[label]
