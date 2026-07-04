import streamlit as st
import re
from collections import Counter
from . import common_ui as common

# ==========================================
# 1. フッター
# ==========================================
def render_sidebar_footer(current_system="launcher"):
    """サイドバーの一番下にあるナビゲーションボタンを描画する"""
    st.sidebar.divider()
    st.sidebar.title("📖 ページ選択")
    
    # システム選択ボタン
    is_launcher = (current_system == "launcher")
    if st.sidebar.button(
        "🏠 システム選択", 
        type="primary" if is_launcher else "secondary", 
        use_container_width=True
    ):
        if not is_launcher:
            keys_to_clear = [
                k for k in st.session_state.keys() 
            ] 
            for k in keys_to_clear:
                del st.session_state[k]
            st.switch_page("app.py")
            
    # CoC用ボタン
    is_coc = (current_system == "coc")
    if st.sidebar.button(
        " 🎲 クトゥルフ神話TRPG", 
        type="primary" if is_coc else "secondary", 
        use_container_width=True
    ):
        if not is_coc:
            keys_to_clear = [
                k for k in st.session_state.keys() if not k.startswith("coc_")
            ] 
            for k in keys_to_clear:
                del st.session_state[k]
            st.switch_page("pages/pages_coc.py")
            
    # エモクロア用ボタン
    is_emo = (current_system == "emo")
    if st.sidebar.button(
        "🍃 エモクロアTRPG", 
        type="primary" if is_emo else "secondary", 
        use_container_width=True
    ):
        if not is_emo:
            keys_to_clear = [
                k for k in st.session_state.keys() if not k.startswith("emo_")
            ] 
            for k in keys_to_clear:
                del st.session_state[k]
            st.switch_page("pages/pages_emo.py")
            
    st.sidebar.divider()

    # 終了ボタン
    if st.sidebar.button("❌ システム終了", use_container_width=True):
        st.session_state.show_shutdown_confirm = True
        st.rerun()

# ==========================================
# 2. ファイル管理（アップロード・削除）
# ==========================================
def _add_uploaded_files():
    """ファイルがドロップされた瞬間に自動で走る裏方関数"""
    up_key = f"uploader_{st.session_state.uploader_key}"
    if up_key in st.session_state and st.session_state[up_key]:
        for f in st.session_state[up_key]:
            raw_bytes = f.getvalue()
            
            if f.name.endswith('.zip'):
                new_data = raw_bytes
            else:
                try:
                    new_data = raw_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    new_data = raw_bytes.decode('cp932', errors='replace')
            
            base_name = f.name
            unique_name = base_name
            already_exists = False
            for _, ex_data in st.session_state.file_dict.items():
                if ex_data == new_data:
                    already_exists = True
                    break
            if already_exists:
                continue
            count = 2
            while unique_name in st.session_state.file_dict:
                parts = base_name.rsplit('.', 1)
                if len(parts) == 2:
                    unique_name = f"{parts[0]}({count}).{parts[1]}"
                else:
                    unique_name = f"{base_name}({count})"
                count += 1
            st.session_state.file_dict[unique_name] = new_data
            
        st.session_state.uploader_key += 1

def _delete_file(fname):
    """バツボタン(✖)が押されたときにファイルと関連設定を消す裏方関数"""
    if fname in st.session_state.file_dict:
        del st.session_state.file_dict[fname]
        if "char_merges" in st.session_state:
            new_merges = []
            for merge in st.session_state.char_merges:
                new_targets = [tgt for tgt in merge['targets'] if not tgt.startswith(fname + "<:::>")]
                if len(new_targets) > 1: 
                    new_merges.append({'name': merge['name'], 'targets': new_targets})
            st.session_state.char_merges = new_merges
        keys_to_delete = [
            k for k in st.session_state.keys() 
            if k.startswith(f"tab_{fname}_") or k.startswith(f"char_{fname}_") or k == f"file_en_{fname}"
        ]
        for k in keys_to_delete:
            st.session_state.pop(k, None)
        st.session_state.uploader_key += 1

def render_file_manager():
    """サイドバー上部のファイル管理UIを描画する"""
    st.sidebar.title("📁 ファイル管理")
    if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0
    
    st.sidebar.file_uploader(
        "新しいログを追加", 
        type=["html", "htm", "txt", "md", "zip"], 
        accept_multiple_files=True, 
        key=f"uploader_{st.session_state.uploader_key}", 
        on_change=_add_uploaded_files
    )
    
    if st.session_state.file_dict:
        st.sidebar.subheader("読み込み中のファイル")
        for fname in list(st.session_state.file_dict.keys()):
            col_name, col_del = st.sidebar.columns([0.8, 0.2])
            safe_fname = fname.replace('[', r'\[').replace(']', r'\]')
            col_name.caption(f"📄 {safe_fname}")
            col_del.button("✖", key=f"del_{fname}", on_click=_delete_file, args=(fname,))
    st.sidebar.divider()


# ==========================================
# 3. 表示データの絞り込み（ファイル・タブ・キャラ）
# ==========================================
def _render_single_file_options(fname, file_df, sel_file_tabs, sel_chars):
    """1ファイル分のタブ・キャラの選択UIを描画し、結果をリストに追加する"""
    tabs, chars = file_df['タブ'].unique(), file_df['キャラクター名'].unique()
    
    with st.expander("↳ 表示タブ", expanded=False):
        for t in tabs: st.session_state.setdefault(f"tab_{fname}_{t}", True)
        common.render_filter_header("▼ 表示タブ", f"tab_{fname}", tabs, title_style="font-weight:bold;")
        common.render_chunked_checkboxes(tabs, prefix=f"tab_{fname}", num_columns=1)
        sel_file_tabs.extend([f"{fname}<:::>{t}" for t in tabs if st.session_state.get(f"tab_{fname}_{t}")])
            
    with st.expander("↳ キャラクター", expanded=False):
        for c in chars: st.session_state.setdefault(f"char_{fname}_{c}", True)
        common.render_filter_header("▼ キャラクター", f"char_{fname}", chars, title_style="font-weight:bold;")
        common.render_chunked_checkboxes(chars, prefix=f"char_{fname}", num_columns=1)
        sel_chars.extend([f"{fname}<:::>{c}" for c in chars if st.session_state.get(f"char_{fname}_{c}")])

def render_file_char_selector(full_df):
    """【部品】ファイル・タブ・キャラの選択UIを描画し、設定を返す"""
    st.sidebar.markdown("### 🗂 表示データの絞り込み")
    sel_files, sel_file_tabs, sel_chars = [], [], []
    
    with st.sidebar.expander("📄 表示ファイル・タブ・キャラ", expanded=True):
        for fname in full_df['ファイル名'].unique():
            f_key = f"file_en_{fname}"
            safe_fname = fname.replace('[', r'\[').replace(']', r'\]')
            
            if st.checkbox(f"📁 {safe_fname}", value=st.session_state.get(f_key, True), key=f_key):
                sel_files.append(fname)
                file_df = full_df[full_df['ファイル名'] == fname]
                _render_single_file_options(fname, file_df, sel_file_tabs, sel_chars)
                
        st.divider()
        st.toggle(
            "同名キャラをファイルごとに区別する", 
            value=st.session_state.get("separate_char_by_file", False), 
            key="separate_char_by_file"
        )

    return {
        'sel_files': sel_files,
        'sel_file_tabs': sel_file_tabs,
        'sel_chars': sel_chars,
        'separate_char_by_file': st.session_state.get("separate_char_by_file", False)
    }

# ==========================================
# 4. キャラクター統合設定
# ==========================================
def _build_merge_options(full_df):
    """同名キャラにはファイル名を付けて区別する辞書を作る"""
    char_file_counts = full_df.groupby('キャラクター名')['ファイル名'].nunique()
    return {
        row['file_char']: 
        f"{row['キャラクター名']} ［📄{row['ファイル名']}］" 
            if char_file_counts[row['キャラクター名']] > 1 
            else row['キャラクター名'] 
        for _, row in full_df[['ファイル名', 'キャラクター名', 'file_char']].drop_duplicates().iterrows()
    }

def _generate_merge_name(input_name, targets, smart_options, current_merges, edit_idx=None):
    """入力名が空なら自動生成し、名前被りがあれば(2)などを付けて返す"""
    if input_name.strip():
        base_name = input_name.strip()
    else:
        base_name = re.split(r'[\(（\s]', smart_options.get(targets[0], targets[0]).split(" ［")[0])[0] + "（統合）"
        
    final_name, count = base_name, 1
    existing_names = [m['name'] for i, m in enumerate(current_merges) if i != edit_idx]
    
    while final_name in existing_names:
        final_name, count = f"{base_name}({count})", count + 1
        
    return final_name

def _render_create_mode(smart_options, merged_targets, allow_overlap):
    """新規グループ作成のUIを描画する"""
    if "merge_clear_key" not in st.session_state: 
        st.session_state.merge_clear_key = 0
    mk = st.session_state.merge_clear_key
    
    available_fc_ids = list(smart_options.keys()) if allow_overlap \
        else [fc for fc in smart_options.keys() if fc not in merged_targets]
    
    new_name = st.text_input(
        "新しい名前 (未入力可):", 
        placeholder="noname", 
        key=f"merge_name_input_{mk}"
    )
    targets = st.multiselect(
        "まとめる対象:", 
        available_fc_ids, 
        format_func=lambda x: smart_options.get(x, x), 
        placeholder="クリックしてキャラを選択...", 
        key=f"merge_target_input_{mk}"
    )
    
    if st.button(
        "＋ 新規グループを作成", 
        use_container_width=True, 
        key="btn_add_merge", 
        type="primary"
    ):
        if targets:
            final_name = _generate_merge_name(new_name, targets, smart_options, st.session_state.char_merges)
            st.session_state.char_merges.append({'name': final_name, 'targets': targets})
            st.session_state.merge_clear_key += 1
            st.rerun()

def _render_edit_mode(smart_options, merged_targets, allow_overlap):
    """既存グループの編集・削除UIを描画する"""
    if not st.session_state.char_merges: 
        st.info("作成済みの統合グループがありません。")
        return

    edit_idx = st.selectbox(
        "編集するグループを選択:", 
        range(len(st.session_state.char_merges)), 
        format_func=lambda i: st.session_state.char_merges[i]['name']
    )
    target_merge = st.session_state.char_merges[edit_idx]
    
    available_fc_ids_edit = list(smart_options.keys()) if allow_overlap else [
            fc for fc in smart_options.keys() 
                if fc not in merged_targets or fc in target_merge['targets']
        ]
    valid_defaults = [t for t in target_merge['targets'] if t in available_fc_ids_edit]
    
    edit_name = st.text_input(
        "統合後の名前を変更:", 
        value=target_merge['name'], 
        key=f"edit_name_{edit_idx}"
    )
    edit_targets = st.multiselect(
        "まとめる対象を編集:", 
        available_fc_ids_edit, 
        default=valid_defaults, 
        format_func=lambda x: smart_options.get(x, x), 
        key=f"edit_targets_{edit_idx}"
    )
    
    c1, c2 = st.columns(2)
    if c1.button("💾 変更を保存", type="primary", use_container_width=True):
        final_name = _generate_merge_name(edit_name, edit_targets, smart_options, st.session_state.char_merges, edit_idx)
        st.session_state.char_merges[edit_idx]['name'] = final_name
        st.session_state.char_merges[edit_idx]['targets'] = edit_targets
        st.rerun()
    if c2.button("🗑️ 削除", type="secondary", use_container_width=True):
        st.session_state.char_merges.pop(edit_idx)
        st.rerun()

def render_character_merge_ui(full_df):
    """【部品】キャラクター統合のUIを描画し、設定を返す"""
    with st.sidebar.expander("👥 キャラクターの統合", expanded=False):
        st.caption("同一人物の複数キャラなどをまとめます。")
        if "char_merges" not in st.session_state: st.session_state.char_merges = []
        
        allow_overlap = st.toggle("1キャラを複数の統合に含める", value=False, key="chk_allow_overlap")
        smart_options = _build_merge_options(full_df)
        merged_targets = {tgt for m in st.session_state.char_merges for tgt in m['targets']}
        
        mode = st.radio("操作を選択:", ["✨ 新規作成", "✏️ 編集・削除"], horizontal=True, label_visibility="collapsed")
        
        if mode == "✨ 新規作成":
            _render_create_mode(smart_options, merged_targets, allow_overlap)
        else:
            _render_edit_mode(smart_options, merged_targets, allow_overlap)

        # 作成済みのグループ一覧とエラー表示
        if st.session_state.char_merges:
            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
            overlapped_targets = {tgt for tgt, count in Counter([tgt for m in st.session_state.char_merges for tgt in m['targets']]).items() if count > 1}
            
            for merge in st.session_state.char_merges:
                is_err = (not allow_overlap) and any(tgt in overlapped_targets for tgt in merge['targets'])
                name_display = f"<span style='color: #ef4444; font-weight: bold;'>⚠️ {merge['name']}</span>" \
                                                                        if is_err else f"**{merge['name']}**"
                targets_display = ", ".join([
                    f"<span style='color: #ef4444;'>{smart_options.get(t, t)}</span>" 
                    if is_err and t in overlapped_targets else smart_options.get(t, t) for t in merge['targets']
                ])
                st.markdown(f"{name_display}<br><small>└ {targets_display}</small>", unsafe_allow_html=True)

    return {'char_merges': st.session_state.get("char_merges", [])}