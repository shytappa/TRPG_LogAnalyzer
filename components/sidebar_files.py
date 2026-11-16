import streamlit as st
from core import logic_base, ccfolia_reader
from . import common_ui as common, sidebar_merge

# ==========================================
# ファイル管理（アップロード・削除）
# ==========================================
UPLOAD_TYPES = ["html", "htm", "txt", "md", "json", "zip"]

def bump_sources_revision():
    """
    読み込み元（アップロードしたファイル・履歴フォルダ）が変わったことを記録する。
    解析結果の使い回しはこの番号で判断する（✖ で消して同じ名前の別のファイルを入れ直したときも、解析し直すように）
    """
    st.session_state["_sources_rev"] = st.session_state.get("_sources_rev", 0) + 1

def sources_revision():
    return st.session_state.get("_sources_rev", 0)

MB = 1024 * 1024
# 公開サーバーで、1人（1つの画面）が読み込めるファイルの合計の大きさ。読み込んだファイルはサーバーのメモリに残るので、
# 使いすぎてサーバーが止まらないようにする。ログは長いキャンペーンでも1MB未満なので、普通に使う分には十分。自分のPCでは制限しない
PUBLIC_TOTAL_UPLOAD_LIMIT = 50 * MB

def _data_size(name, data):
    """
    読み込み済みのファイル1つの大きさ（バイト）。文字列は UTF-8 にしたときの大きさで数える。
    ZIP は圧縮したままの大きさではなく、中のログを解凍した後の大きさの合計で数える（解析するときはその大きさになるため）
    """
    if isinstance(data, str):
        return len(data) if data.isascii() else len(data.encode('utf-8'))
    if name.lower().endswith('.zip'):
        return ccfolia_reader.zip_log_bytes(data)
    return len(data)

def store_uploaded_files(uploaded_files):
    """
    アップロードされたファイルを読み込み済みファイル一覧（file_dict）に追加する。
    中身が同じファイルは追加せず、名前だけ同じ別ファイルは「名前(2).html」のように付け直す。
    公開サーバーでは、合計が PUBLIC_TOTAL_UPLOAD_LIMIT を超えるファイルは追加しない。
    """
    limit = None if logic_base.is_local_machine() else PUBLIC_TOTAL_UPLOAD_LIMIT
    # 合計はアップロードしたときだけ数える（毎回の再実行では数えない）
    total = sum(_data_size(n, d) for n, d in st.session_state.file_dict.items()) if limit else 0
    too_big = []
    for f in uploaded_files:
        raw_bytes = f.getvalue()
        new_data = raw_bytes if f.name.lower().endswith('.zip') else logic_base.decode_log(raw_bytes)

        same = next((name for name, ex_data in st.session_state.file_dict.items() if ex_data == new_data), None)
        if same is not None:
            st.toast(f"⚠️ 「{f.name}」は「{same}」と中身が同じなので、読み込みませんでした。")
            continue
        if limit:
            size = _data_size(f.name, new_data)
            if total + size > limit:
                too_big.append(f.name)
                continue
            total += size
        base_name = f.name
        unique_name = base_name
        count = 2
        while unique_name in st.session_state.file_dict:
            parts = base_name.rsplit('.', 1)
            if len(parts) == 2: unique_name = f"{parts[0]}({count}).{parts[1]}"
            else: unique_name = f"{base_name}({count})"
            count += 1
        st.session_state.file_dict[unique_name] = new_data
        bump_sources_revision()
    if too_big:
        names = "」「".join(too_big)
        st.toast(f"⚠️ 読み込めるファイルの合計は {limit // MB}MB までなので、「{names}」は読み込みませんでした。"
                 "いらないファイルを ✖ で消してから、もう一度追加してください。", duration="long")

def _add_uploaded_files():
    up_key = f"nokeep_uploader_{st.session_state.uploader_key}"
    if up_key in st.session_state and st.session_state[up_key]:
        store_uploaded_files(st.session_state[up_key])
        st.session_state.uploader_key += 1

def _forget_settings(source, per_log_prefixes):
    """
    読み込み元（アップロードしたファイル・ZIP・履歴フォルダ）を消したとき、その中のログに関する設定も消す。
    ZIPや履歴フォルダは、中に入っていた個々のログのファイル名で設定が保存されている。
    per_log_prefixes: ほかに消すキーの頭の部分（キーは「頭の部分 + make_key(ログ名, '')」。render_file_manager を参照）
    """
    log_names = st.session_state.get("_source_files", {}).get(source, {source})
    if "char_merges" in st.session_state:
        new_merges = []
        for merge in st.session_state.char_merges:
            new_targets = [tgt for tgt in merge['targets'] if logic_base.split_key(tgt)[0] not in log_names]
            if len(new_targets) > 1:
                new_merges.append({**merge, 'targets': new_targets})
            else:   # 対象が1人以下になった統合は消す。一括操作で OFF にしていたら、残ったキャラを表示に戻す
                sidebar_merge.carry_over_toggle(merge['name'], None, new_targets, [])
        st.session_state.char_merges = new_merges
    prefixes = tuple(p for n in log_names for p in (f"tab_{n}_", f"char_{n}_",
                                                     *(f"{extra}{logic_base.make_key(n, '')}" for extra in per_log_prefixes)))
    enabled_keys = {f"file_en_{n}" for n in log_names}
    keys_to_delete = [
        k for k in st.session_state.keys()
        if isinstance(k, str) and (k.startswith(prefixes) or k in enabled_keys)
    ]
    for k in keys_to_delete: st.session_state.pop(k, None)

def _delete_file(fname, per_log_prefixes):
    if fname in st.session_state.file_dict:
        del st.session_state.file_dict[fname]
        _forget_settings(fname, per_log_prefixes)
        bump_sources_revision()
        st.session_state.uploader_key += 1

def _delete_extra_source(label, remove, per_log_prefixes):
    remove()
    _forget_settings(label, per_log_prefixes)
    bump_sources_revision()

def render_file_manager(extra_sources=None, per_log_prefixes=()):
    """
    サイドバーのファイル管理（アップロードと、読み込み中のファイルの一覧）。
    extra_sources: アップロード以外の読み込み元（表示名 → ✖で消すときに呼ぶ関数）。後から足す機能の履歴フォルダなど
    per_log_prefixes: ログを ✖ で消したときに一緒に消す、後から足す機能のキーの頭の部分（キーは「頭の部分 + make_key(ログ名, '')」）
    """
    extra_sources = extra_sources or {}
    st.sidebar.title("📁 ファイル管理")
    if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0
    st.sidebar.file_uploader(
        "新しいログを追加", type=UPLOAD_TYPES,
        accept_multiple_files=True, key=f"nokeep_uploader_{st.session_state.uploader_key}", on_change=_add_uploaded_files
    )
    if st.session_state.file_dict or extra_sources:
        st.sidebar.subheader("読み込み中のファイル")
        prefixes = tuple(per_log_prefixes)
        rows = [(name, f"📄 {name}", _delete_file, (name, prefixes)) for name in st.session_state.file_dict]
        rows += [(label, label, _delete_extra_source, (label, remove, prefixes)) for label, remove in extra_sources.items()]
        for name, display, on_delete, args in rows:
            col_name, col_del = st.sidebar.columns([0.8, 0.2])
            col_name.caption(common.escape_md_brackets(display))
            col_del.button("✖", key=f"btn_del_{name}", on_click=on_delete, args=args)
    st.sidebar.divider()
