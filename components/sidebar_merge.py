import html
import re
import uuid
from collections import Counter
import streamlit as st
from core.logic_base import MergeParams, split_key
from . import common_ui as common
from .styles_base import ERROR_TEXT

# ==========================================
# キャラクター統合設定
# ==========================================
def _build_merge_options(full_df):
    pairs = full_df[['ファイル名', 'キャラクター名', '_file_char']].drop_duplicates()
    # キャラ名ごとの、出てくるファイルの数（2つ以上ならファイル名も添えて区別する）
    file_counts = pairs['キャラクター名'].map(pairs.groupby('キャラクター名')['ファイル名'].nunique())
    return {
        fc: f"{str(cname).strip()} ［📄{fname}］" if n > 1 else str(cname).strip()
        for fname, cname, fc, n in zip(pairs['ファイル名'], pairs['キャラクター名'], pairs['_file_char'], file_counts)
    }

def _generate_merge_name(input_name, targets, smart_options, current_merges, edit_idx=None):
    if input_name.strip(): base_name = input_name.strip()
    else: base_name = re.split(r'[\(（\s]', smart_options.get(targets[0], targets[0]).split(" ［")[0])[0] + "（統合）"
        
    final_name, count = base_name, 1
    existing_names = [m['name'] for i, m in enumerate(current_merges) if i != edit_idx]
    while final_name in existing_names:
        final_name, count = f"{base_name}({count})", count + 1
    return final_name

def _render_create_mode(smart_options, merged_targets, allow_overlap):
    if "merge_clear_key" not in st.session_state: st.session_state.merge_clear_key = 0
    mk = st.session_state.merge_clear_key
    
    available_fc_ids = list(smart_options.keys()) if allow_overlap \
        else [fc for fc in smart_options.keys() if fc not in merged_targets]
    
    new_name = st.text_input("新しい名前 (未入力可):", placeholder="noname", key=f"merge_name_input_{mk}")
    targets = st.multiselect(
        "まとめる対象:", available_fc_ids, format_func=lambda x: smart_options.get(x, x), 
        placeholder="クリックしてキャラを選択...", key=f"merge_target_input_{mk}"
    )
    
    if st.button("＋ 新規グループを作成", width="stretch", key="btn_add_merge", type="primary"):
        if targets:
            final_name = _generate_merge_name(new_name, targets, smart_options, st.session_state.char_merges)
            st.session_state.char_merges.append({'id': uuid.uuid4().hex, 'name': final_name, 'targets': targets})
            st.session_state[f"gmerge_{final_name}"] = True 
            st.session_state.merge_clear_key += 1
            st.rerun()

def carry_over_toggle(old_name, new_name, old_targets, new_targets):
    """
    統合の名前・対象を変えたとき、「🔗 統合キャラクター 一括操作」の ON/OFF と、対象のキャラの表示を合わせる。
    new_name が None なら統合を削除したとき（OFF にしていたなら、対象のキャラを表示に戻す）
    """
    is_on = st.session_state.get(f"gmerge_{old_name}", True)
    updates = {}
    if new_name != old_name:
        updates[f"gmerge_{old_name}"] = None
        if new_name is not None:
            updates[f"gmerge_{new_name}"] = is_on
    for tgt in old_targets:
        if not is_on and (new_name is None or tgt not in new_targets):
            updates[char_key(tgt)] = True    # 統合から外れたキャラは、隠したままにしない
    for tgt in new_targets:
        if tgt not in old_targets:
            updates[char_key(tgt)] = is_on   # 新しく入れたキャラは、統合の ON/OFF に合わせる
    common.set_widget_values_later(updates)

def char_key(target):
    """サイドバーのファイルごとのキャラの表示（char_{ファイル名}_{キャラ名}）のキー（target: 「ファイル名＋区切り＋キャラ名」）"""
    fname, cname = split_key(target)
    return common.checkbox_key(f"char_{fname}", cname)

def _forget_edit_inputs(merge_id):
    """編集欄の入力内容を捨てる（次に開いたとき、保存済みの内容から表示し直すため）"""
    for k in (f"edit_name_{merge_id}", f"edit_targets_{merge_id}"):
        st.session_state.pop(k, None)

def _render_edit_mode(smart_options, merged_targets, allow_overlap):
    merges = st.session_state.char_merges
    if not merges:
        st.info("作成済みの統合グループがありません。")
        return

    # 入力欄はグループごとのID（何番目か、ではない）で区別する。
    # 番号で区別すると、グループを削除して番号がずれたときに、別のグループの入力内容が残ってしまう
    ids = [m['id'] for m in merges]
    if st.session_state.get("merge_edit_sel") not in ids:
        st.session_state["merge_edit_sel"] = ids[0]
    edit_id = st.selectbox(
        "編集するグループを選択:", ids, key="merge_edit_sel",
        format_func=lambda i: next(m['name'] for m in merges if m['id'] == i)
    )
    edit_idx = ids.index(edit_id)
    target_merge = merges[edit_idx]

    available_fc_ids_edit = list(smart_options.keys()) if allow_overlap else [
            fc for fc in smart_options.keys() if fc not in merged_targets or fc in target_merge['targets']
        ]
    targets_key = f"edit_targets_{edit_id}"
    common.init_state(f"edit_name_{edit_id}", target_merge['name'])
    common.init_state(targets_key, target_merge['targets'])
    # 「1キャラを複数の統合に含める」を切り替えて選択肢から外れたキャラは、選択からも外す
    st.session_state[targets_key] = [t for t in st.session_state[targets_key] if t in available_fc_ids_edit]

    edit_name = st.text_input("統合後の名前を変更:", key=f"edit_name_{edit_id}")
    edit_targets = st.multiselect(
        "まとめる対象を編集:", available_fc_ids_edit,
        format_func=lambda x: smart_options.get(x, x), key=targets_key
    )

    c1, c2 = st.columns(2)
    if c1.button("💾 変更を保存", type="primary", width="stretch"):
        if not edit_targets:
            st.warning("まとめる対象を1人以上選んでください。（グループを消す場合は「削除」）")
            return
        final_name = _generate_merge_name(edit_name, edit_targets, smart_options, merges, edit_idx)
        carry_over_toggle(target_merge['name'], final_name, target_merge['targets'], edit_targets)
        target_merge['name'] = final_name
        target_merge['targets'] = edit_targets
        _forget_edit_inputs(edit_id)
        st.rerun()
    if c2.button("🗑️ 削除", type="secondary", width="stretch"):
        carry_over_toggle(target_merge['name'], None, target_merge['targets'], [])
        merges.pop(edit_idx)
        _forget_edit_inputs(edit_id)
        st.session_state.pop("merge_edit_sel", None)
        st.rerun()

def render_character_merge_ui(full_df):
    with st.sidebar.expander("👥 キャラクターの統合", expanded=False):
        st.caption("同一人物の複数キャラなどをまとめます。")
        if "char_merges" not in st.session_state: st.session_state.char_merges = []
        for merge in st.session_state.char_merges:
            merge.setdefault('id', uuid.uuid4().hex)   # 編集欄の区別用

        allow_overlap = st.toggle("1キャラを複数の統合に含める", key="chk_allow_overlap")
        smart_options = _build_merge_options(full_df)
        merged_targets = {tgt for m in st.session_state.char_merges for tgt in m['targets']}
        
        mode = st.radio("操作を選択:", ["✨ 新規作成", "✏️ 編集・削除"], horizontal=True, label_visibility="collapsed")
        
        if mode == "✨ 新規作成": _render_create_mode(smart_options, merged_targets, allow_overlap)
        else: _render_edit_mode(smart_options, merged_targets, allow_overlap)

        if st.session_state.char_merges:
            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
            overlapped_targets = {tgt for tgt, count in Counter([tgt for m in st.session_state.char_merges for tgt in m['targets']]).items() if count > 1}
            
            for merge in st.session_state.char_merges:
                is_err = (not allow_overlap) and any(tgt in overlapped_targets for tgt in merge['targets'])
                name = html.escape(merge['name'])
                name_display = f"<span style='color: {ERROR_TEXT}; font-weight: bold;'>⚠️ {name}</span>" if is_err else f"<b>{name}</b>"
                targets_display = ", ".join([
                    f"<span style='color: {ERROR_TEXT};'>{html.escape(smart_options.get(t, t))}</span>"
                    if is_err and t in overlapped_targets else html.escape(smart_options.get(t, t)) for t in merge['targets']
                ])
                st.markdown(f"{name_display}<br><small>└ {targets_display}</small>", unsafe_allow_html=True)

    return MergeParams(
        char_merges=st.session_state.get("char_merges", []),
        allow_overlap=st.session_state.get("chk_allow_overlap", False),
    )
