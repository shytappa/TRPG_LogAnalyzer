from dataclasses import dataclass, field
from typing import Callable

import streamlit as st

from .core import rules_coc as rules
from .addon_coc import CocAddon, NO_ADDON

# ==========================================
# 起動プロファイル（初期設定と追加機能の切り替え）
# ==========================================
# 画面や集計の処理本体は1つだけにし、初期設定と追加機能（addon）の違いだけをプロファイルで切り替える。
# 通常版は STANDARD。自卓用などの独自設定は、ページ側（例: pages/pages_coc_shy.py）で
# CocProfile を作って app_coc.main() に渡す。ここには通常版以外の設定を置かない。

@dataclass(frozen=True)
class CocProfile:
    name: str
    default_rule: rules.RecalcRule
    # 各ウィジェットの初期値（キー名 → 値）。ここに無いものは各画面の既定値を使う
    widget_defaults: dict = field(default_factory=dict)
    # サマリー表で、最初から「1クリ」「100ファン」とBP内訳の列を隠すか
    summary_hide_detail_columns: bool = True
    # サマリー表で、最初から「期待との差」（目標値から計算した成功率と実際の差）の列を出すか
    summary_show_expected: bool = False
    # サマリー表のハイライトで、最初から「期待との差」の列も強調するか
    summary_highlight_expected: bool = False
    # ハイライトの「同率N人以上で無効化」の N の初期位置（キャラ数 → 選択肢の位置）
    hl_tie_count_index: Callable[[int], int] = lambda char_count: 0
    # ファイルごとのタブの初期表示（None なら全タブ表示）
    default_tab_func: Callable[[str], bool] | None = None
    # 後から足す機能（addon_coc.CocAddon。自卓用の履歴・PLモードなど）。通常版は何も足さない
    addon: CocAddon = NO_ADDON


STANDARD = CocProfile(name="coc", default_rule=rules.R7)


def activate(profile):
    """
    このセッションで使うプロファイルを設定し、初期値を入れる。
    別のプロファイルから切り替わったときは、前後どちらかのプロファイルが変えている設定だけ初期値に戻す。
    """
    previous = st.session_state.get("_coc_profile")
    if previous is None or previous.name != profile.name:
        changed_keys = set(profile.widget_defaults) | {"recalc_rule"}
        if previous is not None:
            changed_keys |= set(previous.widget_defaults)
        for key in changed_keys:
            st.session_state.pop(key, None)
    st.session_state["_coc_profile"] = profile
    st.session_state.setdefault("recalc_rule", profile.default_rule.label)
    for key, value in profile.widget_defaults.items():
        st.session_state.setdefault(key, value)


def current():
    """現在のセッションのプロファイル（未設定なら通常版）"""
    return st.session_state.get("_coc_profile", STANDARD)
