import streamlit as st

def render_filter_header(
        title, prefix, item_list, 
        default_states=True, 
        show_reset=False, 
        col_sizes=None, 
        title_style="font-weight:bold; margin-top:6px; color: #000000;"
    ):
    """全選択・全解除・(リセット) ボタン付きのヘッダーを描画する関数"""
    # 1. カラム比率のデフォルト設定（引数で受け取った値があればそちらを優先）
    if col_sizes is None:
        col_sizes = [0.55, 0.15, 0.15, 0.15] if show_reset else [0.7, 0.15, 0.15]
    cols = st.columns(col_sizes)
    c_title = cols[0]
    c_all = cols[1]
    c_none = cols[2]
    c_reset = cols[3] if show_reset else None

    # 2. タイトル描画
    c_title.markdown(f"<div style='{title_style}'>{title}</div>", unsafe_allow_html=True)

    # 3. 各ボタンの処理
    def _set_all(val):
        for item in item_list: 
            st.session_state[f"{prefix}_{item}"] = val
    def _reset_all():
        for item in item_list:
            def_val = default_states.get(item, True) if isinstance(default_states, dict) else default_states
            st.session_state[f"{prefix}_{item}"] = def_val

    # 4. ボタン描画（disabledを削除して常に押せるようにしました）
    c_all.button("全選択", key=f"btn_all_{prefix}", type="tertiary", on_click=_set_all, args=(True,))
    c_none.button("全解除", key=f"btn_none_{prefix}", type="tertiary", on_click=_set_all, args=(False,))
    if show_reset and c_reset:
        c_reset.button("🔄 リセット", key=f"btn_res_{prefix}", type="tertiary", on_click=_reset_all)


def render_chunked_checkboxes(item_keys, item_labels=None, prefix="", num_columns=4):
    """
    リストをN列ずつの塊（行）に分けて綺麗にチェックボックスを描画する関数。
    item_labelsが指定されない場合は、item_keysをそのまま画面に表示します。
    """
    if item_labels is None:
        item_labels = item_keys
        
    for i in range(0, len(item_keys), num_columns):
        cols = st.columns(num_columns)
        for j in range(num_columns):
            if i + j < len(item_keys):
                k = item_keys[i + j]
                label = item_labels[i + j]
                cols[j].checkbox(label, key=f"{prefix}_{k}")