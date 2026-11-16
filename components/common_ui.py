import functools
import re
import traceback
import streamlit as st
from streamlit.errors import StreamlitAPIException
from core import logic_base
from . import styles_base

_LOCAL_ADDRESSES = ("127.0.0.1", "::1", "localhost")
LOCAL_MARK = logic_base.LOCAL_MARK
is_local_machine = logic_base.is_local_machine

def is_local_access():
    """
    このPCのブラウザから開いているか（解析ツール起動.bat で起動して使う、普段の使い方）。
    ネット上に公開したときに、誰でもサーバーを止められたり、エラーの詳細（ファイルの場所など）が見えたりしないように使う。
    公開サーバーでは中継のせいで全員が「このPC」に見えることがあるので、.bat の目印が無ければ常に「他のPC」とする
    """
    if not is_local_machine():
        return False
    try:
        ip = st.context.ip_address
    except Exception:
        return True
    # 接続元が分からないとき（None）やテスト（AppTest）のときは、このPCとして扱う
    return not isinstance(ip, str) or ip in _LOCAL_ADDRESSES

def show_error(message, error):
    """
    エラーの案内を出す。エラーの中身（ファイルの場所などを含むことがある）と詳しい内容（トレースバック）は、
    このPCから開いているときだけ出す（ほかのPC・公開サーバーではエラーの種類だけ）
    """
    if not is_local_access():
        st.error(f"⚠️ {message}（{type(error).__name__}）")
        return
    st.error(f"⚠️ {message}（{type(error).__name__}: {error}）")
    with st.expander("エラーの詳細（不具合の報告用）"):
        st.code("".join(traceback.format_exception(error)), language=None)

def run_page(load_main):
    """
    pages/ の各ページの起動（読み込み中の表示 → 共通CSS → アプリ本体。エラーなら案内を出す）。
    load_main: アプリ本体を import して、起動する関数を返す関数（import に時間がかかる間も「読み込んでいます」を出すため）
    """
    placeholder = st.empty()
    placeholder.info("⏳ システムを読み込んでいます...")
    styles_base.apply_custom_css()
    try:
        main = load_main()
        placeholder.empty()
        main()
    except Exception as e:
        placeholder.empty()
        show_error("アプリケーションの実行中にエラーが発生しました", e)

def error_boundary(message):
    """
    関数の中でエラーが起きたら、その場所にエラーの案内を出して続ける（画面全体は止めない）。
    @st.fragment の部分は、操作したときにその部分だけが実行し直されるので、タブのエラー隔離とは別にこれで囲む。
    （st.rerun() / st.stop() は Exception ではないので、ここでは止まらない）
    """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                show_error(message, e)
        return wrapper
    return decorate

SORT_ASC = "昇順 (A→Z / 低い順)"
SORT_DESC = "降順 (Z→A / 高い順)"
SORT_ORDER_OPTIONS = [SORT_ASC, SORT_DESC]

def init_state(key, default):
    """
    ウィジェットの初期値を設定する（すでに値があればその値のまま）。ウィジェットを作る直前に呼ぶ。
    初期値はこの関数で入れ、ウィジェット側には value= / index= / default= を渡さず key= だけを渡す。
    （両方に渡すと、値が二重に指定されたという警告が出たり、どちらが優先されるか分かりにくくなるため）

    値があっても書き直すのは、ブラウザに値を確実に伝えるため。
    前の回（ウィジェットがまだ無かった回）に入れた値は、ウィジェットができてもブラウザに伝わらず、
    次に何か操作したときにブラウザ側の初期値（ラジオボタンなら先頭の選択肢）で上書きされてしまう。
    """
    st.session_state[key] = st.session_state[key] if key in st.session_state else default

def set_widget_values_later(values):
    """
    入力欄の値を、次の実行の最初（入力欄を作る前）に書き換える。値が None ならそのキーを消す。
    その回にすでに作った入力欄の値は書き換えられない（Streamlit がエラーにする）ので、ボタンを押した後などに使う
    """
    st.session_state.setdefault("_pending_widget_values", {}).update(values)

def apply_pending_widget_values():
    """set_widget_values_later で頼まれた書き換えを行う（入力欄を作る前に呼ぶ）"""
    for k, v in st.session_state.pop("_pending_widget_values", {}).items():
        if v is None:
            st.session_state.pop(k, None)
        else:
            st.session_state[k] = v

# 値を書き戻さない部品の key の頭。ボタンは btn_、表の行選択やタブ（書き戻すと選択が外れたり戻ったりする）・ファイルのアップロード欄は nokeep_ で始める
NO_KEEP_PREFIXES = ("btn_", "nokeep_")

def keep_widget_state(prefixes=(), keys=()):
    """
    表示していない入力欄の値を残す。
    Streamlit は、その回に描画しなかった入力欄（閉じたタブの中、条件付きで出す欄など）の値を自動で破棄するため、
    毎回値を書き戻して「自分で入れた値」として扱わせる。
    ボタンなどは値を書き込めないので、key が NO_KEEP_PREFIXES で始まるものは除く。
    """
    for k in list(st.session_state.keys()):
        if not isinstance(k, str) or k.startswith(NO_KEEP_PREFIXES):
            continue
        if k in keys or (prefixes and k.startswith(prefixes)):
            st.session_state[k] = st.session_state[k]

def keep_all_widget_state():
    """
    サイドバーやタブを描画する前に止めるとき（表示するロールが0件のときなど）に、すべての入力欄の値を残す。
    その回にもう描画した入力欄は書き換えられない（Streamlit がエラーにする）ので、そのままにする（描画したので消えない）
    """
    for k in list(st.session_state.keys()):
        if not isinstance(k, str) or k.startswith(NO_KEEP_PREFIXES + ("_",)):
            continue
        try:
            st.session_state[k] = st.session_state[k]
        except StreamlitAPIException:
            pass

def sort_order_updater(basis_key, order_key, is_ascending_basis):
    """
    並び替えの「基準」を変えたときに「順序」を自動で切り替えるコールバックを作る。
    is_ascending_basis(基準の値) が True なら昇順（名前順など）、False なら降順（数値の大きい順）にする。
    """
    def _update():
        st.session_state[order_key] = SORT_ASC if is_ascending_basis(st.session_state[basis_key]) else SORT_DESC
    return _update

def checkbox_key(prefix, item):
    """チェックボックスの key（{prefix}_{項目}。項目の前後の空白は除く）"""
    return f"{prefix}_{str(item).strip()}"

def escape_md_brackets(text):
    """markdown で [ ] がリンクの書き方と間違われないようにする（ファイル名の表示用）"""
    return text.replace('[', r'\[').replace(']', r'\]')

_MD_SPECIAL = re.compile(r'([\\`*_{}\[\]()#+\-.!|~<>$:])')

def escape_markdown(text):
    """キャラ名などを markdown の書式として読ませない（「# KP」が見出し、「*ミア*」が斜体、「:smile:」が絵文字にならないように）"""
    return _MD_SPECIAL.sub(r'\\\1', str(text))

def render_filter_header(
        title, prefix, item_list,
        default_states=True,
        show_reset=False,
    ):
    """全選択・全解除・(リセット) ボタン付きのヘッダーを描画する関数"""
    col_sizes = [0.55, 0.15, 0.15, 0.15] if show_reset else [0.7, 0.15, 0.15]
    cols = st.columns(col_sizes, vertical_alignment="center")
    c_title = cols[0]
    c_all = cols[1]
    c_none = cols[2]
    c_reset = cols[3] if show_reset else None

    c_title.markdown(f"**{title}**")

    def _set_all(val):
        for item in item_list:
            st.session_state[checkbox_key(prefix, item)] = val

    def _reset_all():
        for item in item_list:
            def_val = default_states.get(item, True) if isinstance(default_states, dict) else default_states
            st.session_state[checkbox_key(prefix, item)] = def_val

    c_all.button("全選択", key=f"btn_all_{prefix}", type="tertiary", on_click=_set_all, args=(True,))
    c_none.button("全解除", key=f"btn_none_{prefix}", type="tertiary", on_click=_set_all, args=(False,))
    if show_reset and c_reset:
        c_reset.button("🔄 リセット", key=f"btn_res_{prefix}", type="tertiary", on_click=_reset_all)


# 選択肢が変わるチェックボックスの並び（render_option_checkboxes で作ったもの）の key の頭。
# 「_」で始まるので「設定をリセット」でも消えない（消えても、次に描画したときに登録し直す）
_OPTION_PREFIXES_KEY = "_option_checkbox_prefixes"

def render_option_checkboxes(item_keys, prefix, defaults=True, item_labels=None, num_columns=4):
    """
    選択肢が再計算ルールや読み込むログで変わるチェックボックスの並び（成功度・ダイスコマンド・難易度など）。
    選択肢から一時的に消えた項目（7版の「ファンブル」を6版にしている間など）の値は Streamlit が捨ててしまうので、
    この関数で作った並びは自動で書き戻しの対象に載る（option_checkbox_prefixes を keep_widget_state に渡す）。
    defaults: 初期値（全部同じなら True/False、項目ごとなら {項目: 値}）
    """
    st.session_state.setdefault(_OPTION_PREFIXES_KEY, set()).add(f"{prefix}_")
    for item in item_keys:
        default = defaults.get(item, True) if isinstance(defaults, dict) else defaults
        init_state(checkbox_key(prefix, item), default)
    render_chunked_checkboxes(item_keys, item_labels=item_labels, prefix=prefix, num_columns=num_columns)

def option_checkbox_prefixes():
    """render_option_checkboxes で作ったことのある並びの key の頭（毎回、入力欄を作る前に書き戻す）"""
    return tuple(sorted(st.session_state.get(_OPTION_PREFIXES_KEY, ())))

def render_chunked_checkboxes(item_keys, item_labels=None, prefix="", num_columns=4, on_change=None, args_func=None):
    """リストをN列ずつの塊に分けて描画し、重複を自動で防ぐ関数（ラベルが空の項目は「（名前なし）」と表示する）"""
    if item_labels is None:
        item_labels = item_keys

    seen_keys = set()

    for i in range(0, len(item_keys), num_columns):
        # 1列なら列の枠を作らずにそのまま並べる（サイドバーでは数百個になるので、余分な枠を作らない）
        cols = st.columns(num_columns) if num_columns > 1 else [st]
        for j in range(num_columns):
            if i + j < len(item_keys):
                k = item_keys[i + j]
                label = str(item_labels[i + j]) or "（名前なし）"
                safe_key = checkbox_key(prefix, k)

                if safe_key in seen_keys:
                    continue
                seen_keys.add(safe_key)
                kwargs = {}
                if on_change:
                    kwargs['on_change'] = on_change
                if args_func:
                    kwargs['args'] = args_func(k)
                cols[j].checkbox(label, key=safe_key, **kwargs)