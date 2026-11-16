import streamlit as st
from core import logic_base
from components import common_ui as common
from ..features.summary         import ui_sum   as summary
from ..features.probability     import ui_prob  as probability
from ..features.growth          import ui_grow  as growth
from ..features.raw_log         import ui_log   as raw_log
from ..features.params          import ui_params as param_changes
from ..features.dice            import ui_dice  as dice

def _counts(df):
    """表のファイル数（キャラ統合の前の元のファイルで数える）・キャラ数・ロール数の文"""
    return f"{logic_base.file_names(df).nunique()}ファイル / {df['_file_char'].nunique()}キャラ / {len(df)}ロール"

def _render_status_caption(full_df, df_filtered, recalc_rule, filter_notes):
    status_texts = [
        f"📁読込済: {_counts(full_df)}",
        f"🔍表示中: {_counts(df_filtered)}",
        f"📜ルール: {recalc_rule}"
    ]
    st.caption(" ｜ ".join(status_texts))
    if filter_notes:
        st.caption("🎛️絞り込み: " + " ｜ ".join(filter_notes))

# 開いていないタブは描画しないので、タブを移動して戻ってきても設定が残るように値を書き戻す、各タブ内の設定のキーの先頭部分
# （書き戻しは app_coc._keep_hidden_settings でまとめて行う）
KEEP_PREFIXES = (
    "sum_", "col_chk_", "hl_",                      # 総合サマリー
    "prob_",                                        # 条件別 確率集計
    "gr_",                                          # 成長チェック
    "log_", "srch_", "sel_col_", "rad_asc_",        # 生ログ一覧
    "max_heading_depth_sel", "final_sort_sel", "final_asc_rad",
    "prm_",                                         # パラメータ増減
    "dice_",                                        # 出目の分布
)
# ボタンと表の行選択は値を書き込めないので、key を btn_ / nokeep_ で始めて対象外にしている（common.NO_KEEP_PREFIXES）

def render_dashboard(full_df, df_filtered, recalc_rule, filter_params, param_inputs, filter_notes=(), summary_sort=None, extra_tabs=()):
    """
    【画面構築】ダッシュボード全体（6つのタブ ＋ 後から足す機能のタブ）を描画する。
    filter_params: サイドバーの絞り込み（パラメータ増減のタブで、表示するファイル・キャラとキャラクターの統合に使う）
    param_inputs: パラメータ増減のタブで使うもの（ui_params.ParamInputs）を返す関数（そのタブを開いたときだけ呼ぶ）
    filter_notes: 初期状態から変えている絞り込み条件（短い文のリスト）
    summary_sort: 総合サマリー・出目の分布の並び順の初期値（None なら名前順）
    extra_tabs: 足すタブ [(タブの見出し, エラーの案内での呼び名, 中身を描画する関数), ...]（addon_coc.CocAddon.extra_tabs）
    """
    st.markdown("### 📊 解析ダッシュボード")
    _render_status_caption(full_df, df_filtered, recalc_rule, filter_notes)
    st.divider()

    # on_change="rerun": 選択中のタブの中身だけを計算・描画する（全タブを毎回計算すると重いため）
    # (タブの見出し, エラーの案内での呼び名, 中身を描画する関数, 閉じているときに呼ぶ関数)
    tab_specs = [
        ("📊 総合サマリー", "総合サマリー", lambda: summary.render_summary(df_filtered, recalc_rule, default_sort=summary_sort), None),
        ("🎲 条件別 確率集計", "確率集計", lambda: probability.render_probability_analysis(df_filtered, recalc_rule), None),
        ("📈 成長チェック", "成長チェック", lambda: growth.render_growth_check(df_filtered, recalc_rule), None),
        ("📋 生ログ一覧", "生ログ一覧", lambda: raw_log.render_raw_log(df_filtered, recalc_rule), raw_log.release_memory),
        ("📉 パラメータ増減", "パラメータ増減", lambda: param_changes.render_param_changes(param_inputs(), filter_params), None),
        ("🎯 出目の分布", "出目の分布", lambda: dice.render_dice_distribution(df_filtered, default_sort=summary_sort), None),
    ]
    tab_specs += [(label, name, render, None) for label, name, render in extra_tabs]
    tabs = st.tabs([spec[0] for spec in tab_specs], key="dashboard_tab", on_change="rerun")

    for tab, (_, name, render, on_closed) in zip(tabs, tab_specs):
        with tab:
            if tab.open:
                _run_tab(name, render)
            elif on_closed is not None:
                on_closed()

def _run_tab(name, render):
    """タブの中身を描画する。1つのタブでエラーが起きても、サイドバーや他のタブは使えるようにする"""
    common.error_boundary(f"「{name}」の表示中にエラーが発生しました。条件を変えるか、他のタブをお使いください")(render)()