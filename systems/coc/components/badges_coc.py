import re
import html
from .styles_coc import Colors

# ==========================================
# キャラクター名のバッジ生成（全画面共通）
# ==========================================

def _remove_file_suffix(name, file_name):
    """【裏方】名前の末尾に付いているファイル名（_xxxx.html等）を削る"""
    if not name or not file_name: 
        return name, False
    base_file = re.sub(r'\.[a-zA-Z0-9]+$', '', file_name)
    suffixes = [
        f"({file_name})", f"（{file_name}）",
        f"({base_file})", f"（{base_file}）",
        f"_{file_name}", f"_{base_file}",
        file_name, base_file
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            clean_name = name[:-len(suffix)].strip()
            return clean_name, True
    return name, False

def _extract_tags(name):
    """【裏方】名前に含まれるカッコ類をサブ情報として分離する"""
    if not name: return "", ""
    pattern = r'^(.*?)[(（<【\[](.*?)[)）>】\]]$'
    match = re.match(pattern, name.strip())
    if match:
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

    is_merged = False
    if clean_orig and clean_orig != clean_name and (clean_orig not in clean_name):
        is_merged = True
    orig_main, orig_sub = _extract_tags(clean_orig) if is_merged else ("", "")

    main_esc = html.escape(main_name)
    sub_infos = []
    
    if sub_name: 
        sub_infos.append(html.escape(sub_name))
    
    if mode not in ["summary", "growth_header"]:
        orig_parts = []
        if orig_main: orig_parts.append(html.escape(orig_main))
        if orig_sub: orig_parts.append(html.escape(orig_sub))
        if orig_parts:
            sub_infos.append(f"(元: {' '.join(orig_parts)})")
        
    if show_file and file_name and mode != "log":
        sub_infos.append(f"📁{html.escape(file_name)}")

    sub_text = " ".join(sub_infos)

    if mode == "summary":
        if sub_text:
            return f"<span class='badge-name-main'>{main_esc}</span><br><span class='badge-name-sub badge-sub-summary'>{sub_text}</span>"
        return f"<span class='badge-name-main'>{main_esc}</span>"
        
    elif mode == "growth_header":
        if sub_text:
            return f"<span class='badge-name-main'>{main_esc}</span> <span class='badge-name-sub badge-sub-growth'>{sub_text}</span>"
        return f"<span class='badge-name-main'>{main_esc}</span>"
        
    else: # log mode
        if sub_text:
            return f"<span class='badge-name-main'>{main_esc}</span> <span class='badge-name-sub badge-sub-log'>{sub_text}</span>"
        return f"<span class='badge-name-main'>{main_esc}</span>"