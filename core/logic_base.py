import codecs
import os
from dataclasses import dataclass, field
import pandas as pd

# 起動用の .bat（launch_common.bat）が付ける「自分のPCで起動した」目印。
# .bat から起動したアプリの中だけで有効（PC全体の設定は変えない）。公開サーバーには付かない
LOCAL_MARK = "TRPG_LOCAL"

def is_local_machine():
    """自分のPCで .bat から起動したか（公開サーバーなら False。上限や自分用の表示を切り替えるのに使う）"""
    return os.environ.get(LOCAL_MARK) == "1"

# 「ファイル名」と「キャラ名（またはタブ名）」を1つの文字列にまとめたキーの区切り文字
# （別ファイルの同名キャラを区別するために使う。例: "sample.html<:::>探索者A"）
KEY_SEP = "<:::>"

# 名前が空欄のキャラ（GMのダイス用の駒など）を画面に出すときの名前
BLANK_CHAR_NAME = "（NONAME）"

# キャラ統合の前の、ロールが書かれていたファイルの名前の列（統合すると「ファイル名」は統合後のものになる）
ORIG_FILE_COL = '_orig_file'
MULTI_FILE_MERGE = "🌟複数ファイル統合"   # 別々のファイルのキャラを統合したときの「ファイル名」

def file_names(df):
    """ロールが書かれていた元のファイル名の列（キャラ統合の前の名前。無ければ「ファイル名」）"""
    return df[ORIG_FILE_COL] if ORIG_FILE_COL in df.columns else df['ファイル名']

def make_key(file_name, name):
    return f"{file_name}{KEY_SEP}{name}"

def split_key(key):
    """make_key で作ったキーを (ファイル名, 名前) に戻す"""
    file_name, _, name = str(key).partition(KEY_SEP)
    return file_name, name

def decode_log(data):
    """
    ログファイルの中身（バイト列）を文字列にする（アップロード・履歴フォルダ・ZIP の中で共通）。
    BOM があればその文字コード（UTF-8 / メモ帳の「Unicode」＝UTF-16）、無ければ UTF-8、読めなければ Shift_JIS（cp932）として読む。
    BOM は文字として残すと1行目が読めなくなるので外す
    """
    if data.startswith(codecs.BOM_UTF8):
        return data[len(codecs.BOM_UTF8):].decode("utf-8", errors="replace")
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16", errors="replace").lstrip("﻿")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp932", errors="replace")


# ==========================================
# 0. 絞り込み条件（サイドバーの設定をまとめたもの）
# ==========================================
@dataclass
class SelectorParams:
    """表示するファイル・タブ・キャラ（components/sidebar_selector.py で作る）"""
    sel_files: list = field(default_factory=list)
    sel_file_tabs: list = field(default_factory=list)       # make_key(ファイル名, タブ) のリスト
    sel_chars: list = field(default_factory=list)           # make_key(ファイル名, キャラ名) のリスト
    separate_char_by_file: bool = False

@dataclass
class MergeParams:
    """キャラクターの統合（components/sidebar_merge.py で作る）"""
    char_merges: list = field(default_factory=list)         # [{'id', 'name', 'targets'}, ...]
    allow_overlap: bool = False

@dataclass
class FilterParams:
    """全システム共通の絞り込み条件。システムごとの条件はこれを継承して足す"""
    selector: SelectorParams = field(default_factory=SelectorParams)
    merges: MergeParams = field(default_factory=MergeParams)
    sel_success_levels: list = field(default_factory=list)  # 表示する結果（成功度）
    sel_skills: list = field(default_factory=list)          # 表示する技能（「#1」などを除いた判定名）
    active_ranges: list = field(default_factory=list)       # 出目の範囲 [(最小, 最大), ...]


# ==========================================
# 1. 絞り込みの各処理
# ==========================================
def _filter_exact_matches(df, params):
    """完全一致フィルター（ファイル名、タブ、キャラクター名、成功度、判定名）"""
    sel = params.selector
    df_filtered = df[
        (df['ファイル名'].isin(sel.sel_files)) &
        (df['_file_tab'].isin(sel.sel_file_tabs)) &
        (df['_file_char'].isin(sel.sel_chars)) &
        (df['結果'].isin(params.sel_success_levels)) &
        (df['_base_skill_name'].isin(params.sel_skills))
    ]   # 絞り込んだ表は元の表と別物（pandas 3 では、書き換えても元の表は変わらない）ので複製しない
    # 後のキャラクター統合などで名前が変わる前に、元の名前をバックアップしておく
    # （PLモードでは読み込み時に探索者名が入っているので、それを残す）
    if '統合前のキャラクター名' not in df_filtered.columns:
        df_filtered['統合前のキャラクター名'] = df_filtered['キャラクター名']
    else:
        df_filtered['統合前のキャラクター名'] = df_filtered['統合前のキャラクター名'].fillna(df_filtered['キャラクター名'])
    # 別々のファイルのキャラを統合すると「ファイル名」は「🌟複数ファイル統合」になるので、元のファイル名も残す（生ログ・ファイル数で使う）
    df_filtered[ORIG_FILE_COL] = df_filtered['ファイル名']
    return df_filtered


NO_DICE_COL = '_no_dice'   # ダイスを振っていない行（対抗ロールの自動成功・自動失敗など。出目は0になっている）

def rolled_mask(df):
    """ダイスを振った行（出目に関わる絞り込み・並べ替えでは、これ以外の行を除く）"""
    if NO_DICE_COL not in df.columns:
        return pd.Series(True, index=df.index)
    return ~df[NO_DICE_COL].astype(bool)

def range_mask(rolls, ranges):
    """値（出目・目標値）が、いずれかの範囲 [(最小, 最大), ...] に入っている行。最小・最大が None ならその側は制限しない"""
    mask = pd.Series(False, index=rolls.index)
    for min_v, max_v in ranges:
        inside = pd.Series(True, index=rolls.index) if min_v is None else (rolls >= min_v)
        if max_v is not None:
            inside &= rolls <= max_v
        mask = mask | inside
    return mask

def _filter_range_masks(df, params):
    """出目の数値範囲フィルター"""
    if not params.active_ranges:
        return df
    return df[range_mask(df['出目'], params.active_ranges) & rolled_mask(df)]


def _character_merges(df, params):
    """
    キャラクターの統合処理
    allow_overlap=True のとき、複数の統合に含まれるキャラのロールは、それぞれの統合に1回ずつ（行を複製して）数える。
    False のときは、最初に作った統合だけに含める。
    """
    char_merges = [m for m in params.merges.char_merges if m.get('targets')]
    if not char_merges:
        return df
    allow_overlap = params.merges.allow_overlap

    mapping = []  # (_file_char, 統合後の名前, 統合後のファイル名)
    for merge in char_merges:
        source_files = {split_key(tgt)[0] for tgt in merge['targets']}
        new_file_name = list(source_files)[0] if len(source_files) == 1 else MULTI_FILE_MERGE
        for tgt in merge['targets']:
            mapping.append((tgt, merge['name'], new_file_name))
    map_df = pd.DataFrame(mapping, columns=['_file_char', '_merge_name', '_merge_file'])
    if not allow_overlap:
        map_df = map_df.drop_duplicates('_file_char', keep='first')

    if map_df['_file_char'].duplicated().any():
        # 重複あり: 該当行を統合の数だけ複製する（行の並び順は維持）
        df_filtered = df.merge(map_df, on='_file_char', how='left')
    else:
        df_filtered = df.copy(deep=False)
        indexed = map_df.set_index('_file_char')
        df_filtered['_merge_name'] = df_filtered['_file_char'].map(indexed['_merge_name'])
        df_filtered['_merge_file'] = df_filtered['_file_char'].map(indexed['_merge_file'])

    is_merged_mask = df_filtered['_merge_name'].notna()
    df_filtered.loc[is_merged_mask, 'キャラクター名'] = df_filtered.loc[is_merged_mask, '_merge_name']
    df_filtered.loc[is_merged_mask, 'ファイル名'] = df_filtered.loc[is_merged_mask, '_merge_file']
    df_filtered['_file_char'] = df_filtered['ファイル名'] + KEY_SEP + df_filtered['キャラクター名']
    return df_filtered.drop(columns=['_merge_name', '_merge_file'])


def _separate_char_by_file(df, params):
    """同名キャラのファイル名で区別を処理"""
    if params.selector.separate_char_by_file:
        df_filtered = df.copy(deep=False)
        df_filtered['キャラクター名'] = df_filtered['キャラクター名'] + " (" + df_filtered['ファイル名'] + ")"
        return df_filtered
    return df

# ==========================================
# 2. 🌟 外部から呼ばれる窓口
# ==========================================
def add_search_keys(df):
    """UI検索用の基本結合列（_file_charなど）を作成"""
    df_new = df.copy(deep=False)   # 列を足すだけなので、中身までは複製しない
    # 連続ロール用の #1 などを削る
    df_new['_base_skill_name'] = df_new['判定名'].astype(str).str.replace(r'#\d+$', '', regex=True)

    df_new['_file_tab'] = df_new['ファイル名'] + KEY_SEP + df_new['タブ']
    df_new['_file_char'] = df_new['ファイル名'] + KEY_SEP + df_new['キャラクター名']
    return df_new

def universal_filters(df, params):
    """
    ファイル、タブ、キャラクター、判定名、出目の数値範囲など、
    全システム共通の絞り込みをパイプラインで行う
    """
    df = _filter_exact_matches(df, params)
    df = _filter_range_masks(df, params)
    return rename_characters(df, params)

def rename_characters(df, params):
    """
    サイドバーのキャラクターの統合と「同名キャラをファイル名で区別」を反映する（ロール以外の表でも使える）。
    df には「ファイル名」「キャラクター名」「_file_char」の列が要る
    """
    return _separate_char_by_file(_character_merges(df, params), params)