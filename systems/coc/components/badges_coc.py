import re
import html

# ==========================================
# キャラクター名のバッジ生成（全画面共通）
# ==========================================

def _remove_file_suffix(name, file_name):
    """
    【裏方】名前の末尾に付いているファイル名（「名前 (xxxx.html)」「名前_xxxx」など）を削る。
    区切りの無いファイル名は削らない（キャラ「ミア」とファイル「ミア.html」のように、名前が消えてしまうため）
    """
    if not name or not file_name:
        return name, False
    base_file = re.sub(r'\.[a-zA-Z0-9]+$', '', file_name)
    suffixes = [
        f"({file_name})", f"（{file_name}）",
        f"({base_file})", f"（{base_file}）",
        f"_{file_name}", f"_{base_file}",
    ]
    for suffix in suffixes:
        if name.endswith(suffix) and name[:-len(suffix)].strip():
            return name[:-len(suffix)].strip(), True
    return name, False

_TAG_RE = re.compile(r'^(.*)[(（<【\[]([^(（<【\[)）>】\]]*)[)）>】\]]$')

def _extract_tags(name):
    """
    【裏方】名前の末尾のカッコ書き（最後の1組）をサブ情報として分離する（「名前(仮)(2)」→ 名前(仮) と 2）。
    名前全体がカッコ書き（「【KP】」など）なら分けない（名前が空になってしまうため）
    """
    if not name: return "", ""
    match = _TAG_RE.match(name.strip())
    if match and match.group(1).strip():
        return match.group(1).strip(), match.group(2).strip()
    return name.strip(), ""

def format_char_name_html(name, orig_name=None, file_name=None, mode="summary"):
    """
    用途に応じたキャラクター名のHTML文字列（バッジ）を生成する
    mode: "summary" (2段組), "growth_header" (1段組横並び), "log" (シンプル)
    """
    clean_name, show_file_1 = _remove_file_suffix(name, file_name)
    clean_orig, show_file_2 = _remove_file_suffix(orig_name, file_name) if orig_name else ("", False)
    show_file = show_file_1 or show_file_2

    main_name, sub_name = _extract_tags(clean_name)

    # 統合前の名前が今の名前に含まれていなければ、統合したキャラとして元の名前も添える
    is_merged = bool(clean_orig) and clean_orig not in clean_name
    orig_main, orig_sub = _extract_tags(clean_orig) if is_merged else ("", "")

    main_esc = html.escape(main_name)
    sub_infos = []

    if sub_name:
        sub_infos.append(html.escape(sub_name))

    if mode == "log":
        orig_parts = []
        if orig_main: orig_parts.append(html.escape(orig_main))
        if orig_sub: orig_parts.append(html.escape(orig_sub))
        if orig_parts:
            sub_infos.append(f"(元: {' '.join(orig_parts)})")
        
    if show_file and file_name and mode != "log":
        sub_infos.append(f"📁{html.escape(file_name)}")

    sub_text = " ".join(sub_infos)
    if not sub_text:
        return main_esc
    separator, css_class = _SUB_STYLES[mode]
    return f"{main_esc}{separator}<span class='badge-name-sub {css_class}'>{sub_text}</span>"

# mode → (名前とサブ情報の間, サブ情報の CSS クラス)
_SUB_STYLES = {
    "summary": ("<br>", "badge-sub-summary"),
    "growth_header": (" ", "badge-sub-growth"),
    "log": (" ", "badge-sub-log"),
}