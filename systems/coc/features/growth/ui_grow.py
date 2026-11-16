from dataclasses import dataclass
import streamlit as st
from components import common_ui as common
from ...core import results_coc as results
from ...core import conditions_coc as conditions
from ...core.logic_coc import is_bp_roll
from ...components import export_coc as export
from ...components import filters_coc
from . import logic_grow 
from . import copy_grow
from . import html_grow

# ==========================================
# 1. 設定UIの描画部品
# ==========================================
# 成長マークの判定方法（初期値はプロファイルの widget_defaults で変えられる）
JUDGE_OPTION_DEFAULTS = {
    "gr_bp_overall": True,        # B/Pダイスの内訳は、ロール全体の結果で判定する
    "gr_include_rescue": False,   # 救済で成功したロールも成長対象にする（7版のルールでは、難易度に届かなければ失敗なので対象外）
}

@dataclass
class ViewSettings:
    """成長チェックの表示・並び替えの設定（「⚙️ 成長チェックの表示・絞り込み設定」の欄）"""
    detail_mode: str        # 詳細内訳の表示（表示しない / 成功のみ表示 / すべて表示する）
    show_basis: bool        # ☑️ の根拠になったロールを表示する
    sort_check_top: bool    # ☑️ チェックがついた技能を優先
    sort_basis: str         # 並び替えの基準項目
    ascending: bool         # 昇順か

def _apply_judge_options(df):
    """
    成長マークの判定方法の設定を、データに反映する。
    - B/Pダイスの内訳を抽出していても、1回のロールを1行として「ロール全体の結果」で判定する
      （ペナルティダイスで全体としては失敗したロールに、片方の出目だけ見てチェックが付かないように）
    - 救済で成功したロールを成長対象から外す（7版のルールでは、要求された難易度に届かなければ失敗）
    戻り値: (判定に使うデータ, 救済で成功した行を成長対象から外すか)
    """
    if st.session_state.get("gr_bp_overall", JUDGE_OPTION_DEFAULTS["gr_bp_overall"]) and '_roll_id' in df.columns:
        # 採用された出目の行を残して、1回のロールにつき1行にする
        is_adopted = df['出目'] == df['_bp_adopted_roll']
        one_per_roll = df.assign(_adopted=is_adopted).sort_values('_adopted', ascending=False, kind='stable')
        # キャラ統合で同じキャラを2つの統合に入れると、同じロールが統合ごとに複製されているので、統合後の名前ごとに1行残す
        df = one_per_roll.drop_duplicates(['_roll_id', 'キャラクター名']).sort_index().drop(columns='_adopted')
        df = df.assign(結果=df['結果'].where(~is_bp_roll(df), df['_roll_result']))
    exclude_rescue = not st.session_state.get("gr_include_rescue", JUDGE_OPTION_DEFAULTS["gr_include_rescue"]) and '_is_rescued' in df.columns
    return df, exclude_rescue

def _render_judge_options(df):
    """成長マークの判定方法の設定（該当するロールがあるときだけ表示する）"""
    has_bp = '_roll_id' in df.columns
    has_rescue = '_is_rescued' in df.columns and df['_is_rescued'].any()
    if not has_bp and not has_rescue:
        return
    st.divider()
    st.markdown("**☑️ 成長マークの判定方法**")
    if has_bp:
        st.toggle("B/Pダイスの内訳は、ロール全体の結果で判定する（1回のロールを1回と数える）", key="gr_bp_overall")
    if has_rescue:
        st.toggle("救済で成功したロール（難易度には届かなかったロール）も成長対象にする", key="gr_include_rescue")

def _render_settings_ui(df, raw_df, recalc_rule):
    """
    設定用のアコーディオンパネルを描画し、ユーザーの入力値をすべて返す。
    df: 判定方法を反映したデータ / raw_df: 反映前のデータ（判定方法の設定を出すかどうかの判断に使う）
    戻り値: (logic_grow.GrowthConfig, ViewSettings, 成長マークを付ける行)
    """
    all_possible_res = results.result_options(df, recalc_rule)
    with st.expander("⚙️ 成長チェックの表示・絞り込み設定", expanded=False):
        c1, c2 = st.columns(2)
        common.init_state("gr_hide_non_grow", True)
        common.init_state("gr_hide_sanity", True)
        common.init_state("gr_ign_tgt", True)
        hide_non_grow = c1.toggle("成長しない項目（アイデア、幸運など）を除外", key="gr_hide_non_grow")
        hide_sanity = c1.toggle("正気度ロールを除外", disabled=hide_non_grow, key="gr_hide_sanity")
        ignore_target = c2.toggle("目標値の違いを無視", key="gr_ign_tgt")
        only_growth = c2.toggle("成長チェック(☑️)がついた技能のみ表示", key="gr_only_gr")
        _render_judge_options(raw_df)

        st.divider()
        st.markdown("**📋 詳細内訳の表示**")
        detail_mode = st.radio(
            "詳細内訳",
            ["表示しない", "成功のみ表示", "すべて表示する"],
            horizontal=True,
            label_visibility="collapsed",
            key="gr_detail_mode")
        show_basis = st.toggle("☑️ の根拠になったロールを表示する", key="gr_show_basis")

        st.divider()
        st.markdown("**🔄 行の並び替え**")
        c3, c4, c5 = st.columns(3)
        common.init_state("gr_sort_check_top", True)
        sort_check_top = c3.checkbox("☑️ チェックがついた技能を優先", key="gr_sort_check_top")

        common.init_state("gr_sort_order_rad", common.SORT_ASC)
        sort_basis = c4.selectbox(
            "基準項目:",
            ["技能名順", "総数順", "合計成功数順"],
            key="gr_sort_basis_sel",
            on_change=common.sort_order_updater("gr_sort_basis_sel", "gr_sort_order_rad", lambda basis: "技能名順" in basis)
        )
        sort_order_label = c5.radio(
            "順序:",
            common.SORT_ORDER_OPTIONS,
            horizontal=True,
            key="gr_sort_order_rad"
        )
        view = ViewSettings(detail_mode=detail_mode, show_basis=show_basis, sort_check_top=sort_check_top,
                            sort_basis=sort_basis, ascending="降順" not in sort_order_label)

    # 組み合わせロールの「部分的成功」（片方の目標値だけ成功）は、最初は成長の対象にしない（チェックを付ければ対象になる）
    default_growth_res = [r for r in results.success_results(all_possible_res) if r != results.PARTIAL_SUCCESS]
    filter_config, _ = filters_coc.render_complex_condition_ui(
        "gr", all_possible_res,
        default_growth_res,
        header_title="▼ 成長対象とする結果",
        expander_title="☑️ 成長マークの付与条件: ダイス結果",
        recalc_rule=recalc_rule
    )
    adv_opts = filters_coc.render_adv_filters(
        df, "gr_adv", 
        default_b=True, default_p=False,
        expander_title="☑️ 成長マークの付与条件: ダイスコマンド"
    )
    filter_config.command = adv_opts
    check_growth_mask = conditions.get_ui_condition_mask(df, filter_config)

    config = logic_grow.GrowthConfig(hide_non_grow=hide_non_grow, hide_sanity=hide_sanity,
                                     ignore_target=ignore_target, only_growth=only_growth)
    return config, view, check_growth_mask


# ==========================================
# 2. 🌟 メイン関数（司令塔）
# ==========================================
def render_growth_check(df, recalc_rule):
    if df.empty:
        st.info("集計対象のデータがありません。")
        return
    
    for key, value in JUDGE_OPTION_DEFAULTS.items():
        common.init_state(key, value)
    raw_df = df
    df, exclude_rescue = _apply_judge_options(df)

    # 1. UIから設定を受け取る
    config, view, check_growth_mask = _render_settings_ui(df, raw_df, recalc_rule)
    if exclude_rescue:
        check_growth_mask = check_growth_mask & ~df['_is_rescued'].astype(bool)
    st.divider()

    # 2. ロジック関数でデータを処理・集計する
    df_growth = logic_grow.process_growth_data(df, recalc_rule, check_growth_mask, config)

    if not df_growth.empty:
        chars_present = list(df_growth['キャラクター名'].unique())

        c1, c2, c3 = st.columns([0.5, 0.25, 0.25], vertical_alignment="bottom")
        
        with c1:
            selected_char = st.selectbox("👤 キャラクターを選択:", chars_present, key="gr_char_select")
        
        # 3. 選択されたキャラクターで合算（並び替えで別の表になるので、ここでは複製しない）
        char_df = df_growth[df_growth['キャラクター名'] == selected_char]

        # 4. ロジック関数で並び替え
        use_char_code = st.session_state.get('use_char_code_sort', False)
        char_df = logic_grow.sort_growth_data(char_df, view.sort_check_top, view.sort_basis, view.ascending, recalc_rule, use_char_code)
        
        # 5. エクスポートボタン（コピー＆スクショ）の配置
        copy_text = logic_grow.generate_copy_text(char_df, selected_char)
        with c2: 
            copy_grow.render_copy_button(copy_text)
        with c3: 
            export.render_screenshot_button("capture-growth", "CoC_Growth")
        
        # 6. html_grow に委譲して HTMLを組み立てて表示
        html_str = html_grow.build_cards_html(char_df, selected_char, view.detail_mode, view.show_basis)
        st.html(html_str)
    else:
        st.info("条件に一致するデータがありません。")