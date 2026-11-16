from dataclasses import dataclass, field
import pandas as pd
from core.logic_base import range_mask, rolled_mask

# ==========================================
# 1. 初期値以下の出目
# ==========================================
# 「辞書にない技能（初期値不明）の扱い」の選択肢
UNK_USE_TARGET = "目標値を初期値として代用する"
UNK_ALWAYS     = "初期値を100として扱う (必ず含める)"
UNK_NEVER      = "初期値を0として扱う (除外する)"
UNKNOWN_INIT_OPTIONS = [UNK_USE_TARGET, UNK_ALWAYS, UNK_NEVER]

def under_initial_mask(df, unk_behav):
    """出目が技能の初期値以下だったロールのマスク。初期値が分からない技能は unk_behav に従う。ダイスを振っていない行は含めない"""
    mask_known = ~df['_init_unknown'] & (df['出目'] <= df['初期値'])
    if unk_behav == UNK_USE_TARGET and '目標値' in df.columns:
        mask_unknown = df['_init_unknown'] & (df['出目'] <= df['目標値'])
    elif unk_behav == UNK_ALWAYS:
        mask_unknown = df['_init_unknown']
    else:
        mask_unknown = pd.Series(False, index=df.index)
    return (mask_known | mask_unknown) & rolled_mask(df)


# ==========================================
# 1-2. 目標値の条件
# ==========================================
# 「目標値で絞り込む」の選択肢
TARGET_BASE      = "補正前の目標値（技能値）が範囲内"
TARGET_ACTUAL    = "補正後の目標値（難易度・補正の反映後）が範囲内"
TARGET_OVER_INIT = "補正前の目標値が初期値より上"
TARGET_OPTIONS = [TARGET_BASE, TARGET_ACTUAL, TARGET_OVER_INIT]
# 目標値として入力できる値（難易度 c の実目標値は0。上は決めない：補正で100を超えるほか、冗談の「POW 2131」などもある）
TARGET_LIMITS = (0, None)
TARGET_DEFAULT_RANGE = (10, 100)   # 範囲の初期値（最大は空欄にすると上限なし）

@dataclass
class TargetFilter:
    """
    目標値の絞り込み（layouts/sidebar_coc と各画面の条件設定で作る。補正前＝技能値、補正後＝難易度・補正を反映した値）。
    ranges: 範囲 [(最小, 最大), ...]。いずれかに入っていれば当てはまる（最大が None なら上限なし。「初期値より上」では使わない）
    """
    mode: str = TARGET_BASE
    ranges: list = field(default_factory=lambda: [TARGET_DEFAULT_RANGE])

def target_mask(df, tf):
    """
    目標値の条件に当てはまる行。「初期値より上」には、初期値が分からない技能と、
    初期値0の項目（能力値・幸運・SAN・クトゥルフ神話・技能名の無いロールなど。伸ばす技能ではない）を含めない
    """
    if tf is None:
        return pd.Series(True, index=df.index)
    if tf.mode == TARGET_OVER_INIT:
        return ~df['_init_unknown'] & (df['初期値'] > 0) & (df['目標値'] > df['初期値'])
    col = '実目標値' if tf.mode == TARGET_ACTUAL else '目標値'
    return range_mask(df[col], tf.ranges)

def describe_range(min_v, max_v):
    """範囲の短い説明（「30〜60」、最大が無ければ「50以上」）"""
    return f"{min_v}以上" if max_v is None else f"{min_v}〜{max_v}"

def describe_target(tf):
    """目標値の条件の短い説明（例：「補正前の目標値 50以上」「補正後の目標値 30〜60・90以上」）"""
    if tf.mode == TARGET_OVER_INIT:
        return tf.mode
    label = "補正後の目標値" if tf.mode == TARGET_ACTUAL else "補正前の目標値"
    return f"{label} " + "・".join(describe_range(a, b) for a, b in tf.ranges)


# ==========================================
# 2. ダイスコマンド・難易度・B/Pダイス・複数ロールの条件
# ==========================================
@dataclass
class CommandFilter:
    """ダイスコマンドの絞り込み（components/filters_coc.render_adv_filters で作る）"""
    sel_cmds: list | None = None    # 対象にするコマンド（None なら絞り込まない）
    sel_diffs: list | None = None   # 対象にする難易度（None なら絞り込まない）
    exclude_b: bool = False         # ボーナスダイスを使ったロールを除く
    exclude_p: bool = False         # ペナルティダイスを使ったロールを除く
    exclude_multi: bool = False     # 複数回ロール（x5 など）を除く

def get_bp_exclusion_mask(df, exclude_b=False, exclude_p=False):
    """B/Pダイスの除外対象となる行（Trueが除外対象）"""
    mask = pd.Series(False, index=df.index)
    if (not exclude_b and not exclude_p) or 'B/P' not in df.columns:
        return mask
    bp_series = df['B/P'].fillna(0).astype(int)
    if exclude_b: mask = mask | (bp_series > 0)
    if exclude_p: mask = mask | (bp_series < 0)
    return mask

def command_mask(df, cmd):
    """ダイスコマンドの条件に当てはまる行"""
    mask = pd.Series(True, index=df.index)
    if cmd is None:
        return mask
    if cmd.sel_cmds is not None and 'コマンド' in df.columns:
        mask &= df['コマンド'].isin(cmd.sel_cmds)
    if cmd.sel_diffs is not None and '難易度' in df.columns:
        mask &= df['難易度'].isin(cmd.sel_diffs)
    mask &= ~get_bp_exclusion_mask(df, cmd.exclude_b, cmd.exclude_p)
    if cmd.exclude_multi and '複数ロール' in df.columns:
        mask &= ~df['複数ロール'].astype(bool)
    return mask


# ==========================================
# 3. 各画面の条件設定（結果・初期値・出目の範囲・目標値・コマンド）
# ==========================================
@dataclass
class ConditionConfig:
    """
    各画面の「○○としてカウントする基準」（components/filters_coc.render_complex_condition_ui で作る）。
    ((結果 [logic1] 初期値以下) [logic2] 出目の範囲) [logic3] 目標値 のように前から順に組み合わせ、さらにコマンドの条件を満たすもの
    """
    sel_target_res: list = field(default_factory=list)
    logic1: str = "AND"
    use_init: bool = False
    unk_behav: str = UNK_USE_TARGET
    logic2: str = "AND"
    use_ranges: bool = False
    active_ranges: list = field(default_factory=list)
    logic3: str = "AND"
    target: TargetFilter | None = None   # 目標値の条件（None なら使わない）
    command: CommandFilter | None = None

def _combine(left, logic, right):
    return (left & right) if logic == "AND" else (left | right)

def get_ui_condition_mask(df, cfg):
    """各画面の条件設定から、当てはまる行のマスクを返す"""
    if df.empty:
        return pd.Series(False, index=df.index)

    mask = df['結果'].isin(cfg.sel_target_res)
    if cfg.use_init:
        mask = _combine(mask, cfg.logic1, under_initial_mask(df, cfg.unk_behav))
    if cfg.use_ranges and cfg.active_ranges:
        mask = _combine(mask, cfg.logic2, range_mask(df['出目'], cfg.active_ranges) & rolled_mask(df))
    if cfg.target is not None:
        mask = _combine(mask, cfg.logic3, target_mask(df, cfg.target))
    return mask & command_mask(df, cfg.command)
