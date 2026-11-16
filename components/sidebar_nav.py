import os
import signal
import threading
import time
import streamlit as st
from components import common_ui as common

# ==========================================
# 1. システムの一覧（ランチャーとサイドバーのページ選択で共通）
# ==========================================
# 新しいシステムを作ったら、ここに1行足す（ページは pages/ に置く）
SYSTEMS = [
    # note: ランチャーのボタンに添える補足 / enabled: False ならランチャーのボタンを押せない（サイドバーからは開発中の案内ページへ）
    {"id": "coc", "name": "クトゥルフ神話TRPG", "note": "6版/7版", "page": "pages/pages_coc.py", "icon": "🎲", "enabled": True},
    {"id": "emo", "name": "エモクロアTRPG", "note": "開発中", "page": "pages/pages_emo.py", "icon": "🍃", "enabled": False},
]

# 自卓用ページ（公開時はファイルごと外すので、あるときだけ表示する）
PRIVATE_PAGES = [
    {"id": "coc_shy", "name": "クトゥルフ神話TRPG", "note": "自卓用・履歴/PLモード", "page": "pages/pages_coc_shy.py"},
]

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def available_private_pages():
    """自卓用ページのうち、ファイルがあって、このPCから開いているときだけ出すもの"""
    if not common.is_local_access():
        return []
    return [p for p in PRIVATE_PAGES if os.path.exists(os.path.join(_ROOT, p["page"]))]

def require_local_access(back_to_launcher=False):
    """
    自卓用のページ・ツールの最初に呼ぶ。このPCから開いていなければ、案内だけを出して止める（URL を直接開かれたときのため）。
    back_to_launcher: システム選択（app.py）へ戻るリンクも出す（app.py と同じアプリの中のページだけ。マッピングツールは別のアプリなので出さない）
    """
    if common.is_local_access():
        return
    st.error("🔒 このページは、自分のPCで起動したときだけ使えます。")
    if back_to_launcher:
        st.page_link("app.py", label="🏠 システム選択に戻る")
    st.stop()


# ==========================================
# 2. サイドバー下部：設定リセット・ページ選択・システム終了
# ==========================================
def _switch_system(page):
    """別のシステムの画面へ移る。読み込んだログや設定はシステムごとに別物なので、すべて消してから移動する"""
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.switch_page(page)

def _has_loaded_data(data_keys):
    """ページを移ると消えてしまう、読み込んだログ（アップロード・後から足す機能の履歴フォルダなど）があるか"""
    return any(st.session_state.get(k) for k in data_keys)

def _go_to(page, data_keys):
    """ページ移動のボタン。読み込んだログがあれば、消えることを確認してから移る"""
    if _has_loaded_data(data_keys):
        _confirm("switch", page)
    else:
        _switch_system(page)

def render_sidebar_footer(current_system="launcher", keep_on_reset=(), data_keys=("file_dict",)):
    """
    サイドバー下部の設定リセット・ページ選択・終了ボタン。
    current_system: 今いるページ（SYSTEMS の id、ランチャーなら "launcher"）
    keep_on_reset: 設定リセットで消さないキーの頭の部分（読み込んだログなど）。「_」で始まる内部用のキーも消さない
    data_keys: 読み込んだログが入っているキー（ページを移る前に「消えます」と確認するかの判断に使う）
    """
    is_launcher = (current_system == "launcher")
    if not is_launcher:
        st.sidebar.divider()   # ランチャーではサイドバーの一番上に出すので、区切り線は要らない
        if st.sidebar.button("🔄 設定をリセット", width="stretch", help="読み込んだログはそのままで、絞り込みや表示の設定を最初の状態に戻します"):
            _confirm("reset", tuple(keep_on_reset))
    st.sidebar.title("📖 ページ選択")

    if st.sidebar.button("🏠 システム選択", type="primary" if is_launcher else "secondary", width="stretch"):
        if not is_launcher:
            _go_to("app.py", data_keys)

    for s in SYSTEMS:
        is_current = (current_system == s["id"])
        label = f"{s['icon']} {s['name']}" + ("" if s["enabled"] else f" ({s['note']})")
        if st.sidebar.button(label, type="primary" if is_current else "secondary", width="stretch"):
            if not is_current:
                _go_to(s["page"], data_keys)

    # システム終了は、このPCから開いているときだけ（ネット上に公開したときに、誰でもサーバーを止められないように）
    if common.is_local_access():
        st.sidebar.divider()
        if st.sidebar.button("❌ システム終了", width="stretch"):
            _confirm("shutdown")


def reset_settings(keep_keys):
    """設定（入力欄の値など）を消して最初の状態に戻す。keep_keys で始まるキーと「_」で始まる内部用のキーは残す"""
    for k in list(st.session_state.keys()):
        if not str(k).startswith(("_",) + tuple(keep_keys)):
            del st.session_state[k]

def _request_shutdown():
    st.session_state["_shutdown"] = True


# ==========================================
# 3. 確認画面（設定リセット・ページ移動・システム終了で共通）
# ==========================================
# 種類 → (質問, 説明, 「はい」のボタン, 「はい」で行う処理（引数は _confirm に渡したもの）)
CONFIRMS = {
    "reset": ("🔄 設定をリセットしますか？",
              "絞り込みや表示の設定を、最初の状態に戻します。読み込んだログはそのまま残ります。",
              "はい、リセットします", reset_settings),
    "switch": ("📖 ページを移動しますか？",
               "ページを移ると、読み込んだログ・キャラ統合・画面の設定はすべて消えます。",
               "はい、移動します", _switch_system),
    "shutdown": ("⚠️ システムを終了しますか？",
                 "解析ツールを終了します。読み込んだログや画面の設定は保存されません。",
                 "はい、終了します", _request_shutdown),
}

@st.dialog("確認")
def _confirm(kind, *args):
    question, text, yes_label, action = CONFIRMS[kind]
    st.markdown(f"**{question}**")
    st.write(text)
    c1, c2 = st.columns(2)
    if c1.button(yes_label, type="primary", width="stretch"):
        action(*args)
        st.rerun()
    if c2.button("いいえ、戻ります", width="stretch"):
        st.rerun()


# ==========================================
# 4. システム終了（どのページからでも使う）
# ==========================================

def _stop_server_later(delay_sec=2):
    """終了画面を表示し終わってから、このアプリのサーバー（Python）を止める"""
    def stop():
        time.sleep(delay_sec)
        # Windows では強制終了になる（他の環境では Ctrl+C と同じ止め方）
        os.kill(os.getpid(), signal.SIGINT)
    threading.Thread(target=stop, daemon=True).start()

def stop_if_shutdown():
    """終了が選ばれていたら、終了の案内だけを表示してサーバーを止める。各ページの最初（set_page_config の直後）に呼ぶ"""
    if not st.session_state.get("_shutdown") or not common.is_local_access():
        return
    st.error("### 🛑 システムを終了しました")
    st.info("ご利用ありがとうございました。このタブやウィンドウは閉じて構いません。")
    _stop_server_later()
    st.stop()
