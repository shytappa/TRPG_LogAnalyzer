"""
ココフォリアのログを読む部分（どのシステムでも同じ）。
HTML（2026年10月より前の形式・それ以降の形式）・テキスト・JSON・ZIP を読んで「発言（タブ, 名前, 本文）」の一覧にし、
1発言からロールの行を作る処理だけを、各システムから関数（records_from_message）として受け取る。
例: systems/coc/core/parser_coc.py は、CoC のロールの正規表現で行を作る関数を渡している。
"""
import io
import re
import json
import zipfile
from collections import Counter

import lxml.html
import pandas as pd

from core import logic_base

# テキスト形式のログの1行：「[タブ] 名前 : 本文」
TXT_LINE_PATTERN = re.compile(r'^\[(?P<tab>.*?)\]\s+(?P<name>.*?)\s+:\s+(?P<body>.*)$')

# 英語のタブ名を、日本語のココフォリアと同じ名前にする
TAB_MAP = {
    "main": "メイン", "[main]": "[メイン]",
    "info": "情報",   "[info]": "[情報]",
    "other": "雑談",  "[other]": "[雑談]"
}
UNKNOWN_TAB = "[メイン]"   # タブ名が書かれていない発言のタブ
SYSTEM_NAME = "system"     # システムのメッセージ（ステータスの増減など）の名前（前の形式のログに書かれている名前と同じ）
ALL_TAB_NAMES = ("すべて", "all")   # 全部のタブをまとめて書き出したファイルの、ファイル名・題名の [ ] の中
ZIP_MEMBER_SEP = " 内の "           # ZIP の中のログの表示名「ZIP の名前 内の ファイル名」の区切り（表示のためだけ）
# ZIP の中のログの行に付ける、読み込んだ ZIP の名前の列（ZIP の中のログかどうかは、表示名ではなくこの列で見分ける。
# シナリオ名などに「 内の 」が入っていても間違えないように）
ZIP_SOURCE_COL = "_zip"

HTML_EXTS = ('.html', '.htm')
TEXT_EXTS = ('.txt', '.md')
JSON_EXTS = ('.json',)
LOG_EXTS = HTML_EXTS + TEXT_EXTS + JSON_EXTS   # 読み込めるログの拡張子（ZIP の中も同じ）


# ==========================================
# 1. 形式ごとに「発言（タブ, 名前, 本文）」の一覧にする
# ==========================================
def _element_text(el):
    """要素の中の文字列を、それぞれ前後の空白を取ってつなぐ（BeautifulSoup の get_text(strip=True) と同じ結果）"""
    return "".join(t.strip() for t in el.xpath('.//text()'))

def _has_class(name):
    """XPath の条件：class 属性にその名前を含む（「roll-result success」のように複数書かれていてもよい）"""
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'

def html_messages(html_content, include_system=False):
    """
    HTML のログの発言の一覧（新旧どちらの形式も読む）。
    include_system: システムのメッセージ（「[ A ] SAN : 50 → 44」などの増減）も含める（名前は "system"）。
    前の形式では、もともとふつうの発言と同じ形で入っている
    """
    # 「<?xml ... encoding=...?>」の宣言付きの文字列は lxml が受け付けないので外す
    html_content = re.sub(r'^\s*<\?xml[^>]*\?>', '', html_content)
    if not html_content.strip():
        return []
    doc = lxml.html.document_fromstring(html_content)
    articles = doc.xpath(f'//article[{_has_class("message")}]')
    if not articles:
        return _messages_old_format(doc)
    return _messages_new_format(articles, include_system, default_tab=_title_tab(doc))

_TITLE_TAB_PATTERN = re.compile(r'\[([^\[\]]+)\]\s*$')

def _title_tab(doc):
    """
    タブごとに書き出したログの題名（<title> の「部屋名 [雑談]」）の、最後の [ ] のタブ名（「[雑談]」の形）。
    題名に [ ] が無い・「すべて」なら UNKNOWN_TAB
    """
    titles = doc.xpath('//title')
    found = _TITLE_TAB_PATTERN.search(_element_text(titles[0])) if titles else None
    if not found or found.group(1).strip().lower() in ALL_TAB_NAMES:
        return UNKNOWN_TAB
    tab = f"[{found.group(1).strip()}]"
    return TAB_MAP.get(tab, tab)

def _messages_old_format(doc):
    """2026年10月より前の形式：<p><span>タブ</span><span>名前</span>：<span>本文（ダイスの結果も含む）</span></p>"""
    messages = []
    for p_tag in doc.iter('p'):
        spans = list(p_tag.iter('span'))
        if len(spans) >= 3:
            messages.append(tuple(_element_text(s) for s in spans[:3]))
    return messages

def _messages_new_format(articles, include_system=False, default_tab=UNKNOWN_TAB):
    """
    2026年10月からの形式：<article class="message"> の中に、名前（speaker）・タブ（channel-name）・
    発言（message-text）・ダイスの結果（roll-result）が別々に入っている。
    前の形式と同じ「発言 ダイスの結果」の本文にして返す。
    システムのメッセージ（「SAN : 50 → 44」などの増減）は、include_system でなければ除く（名前が空欄の駒の発言は残す）。
    タブごとに書き出したログは発言にタブ名が無いので、default_tab（題名の [ ] のタブ。_title_tab）にする
    """
    def first_text(article, cls):
        found = article.xpath(f'.//*[{_has_class(cls)}]')
        return _element_text(found[0]) if found else ""
    messages = []
    for article in articles:
        is_system = "system" in (article.get("class") or "").split()
        if is_system and not include_system:
            continue
        body = " ".join(t for t in (first_text(article, "message-text"), first_text(article, "roll-result")) if t)
        speaker = SYSTEM_NAME if is_system else first_text(article, "speaker")
        messages.append((first_text(article, "channel-name") or default_tab, speaker, body))
    return messages

def json_messages(json_content, include_system=False):
    """
    2026年11月からのココフォリアの JSON 出力（{"messages": [{"name", "text", "channelName", "extend": {"roll": {"result"}}}, ...]}）を、
    HTML のログと同じ「(タブ, 名前, 本文)」のリストにする。本文はコマンドとダイスの結果をつないだもの
    （x2 などの改行は空白にして、HTML のログと同じ「x2 CC<=50 #1 (1D100<=50) … #2 (1D100<=50) …」の形にする）。
    include_system: システムのメッセージ（SAN の増減など）も含める（名前は "system"）。
    JSON として読めない・形が違うときは None
    """
    try:
        data = json.loads(json_content)
    except ValueError:
        return None
    messages = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(messages, list):
        return None
    out = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        is_system = m.get("type") == "system"
        if is_system and not include_system:   # システムのメッセージ（SAN の増減など）は除く
            continue
        # extend・roll が辞書でない（形の違う JSON）ときは、ダイスの結果が無いものとして読む
        extend = m.get("extend")
        roll = extend.get("roll") if isinstance(extend, dict) else None
        result = roll.get("result") if isinstance(roll, dict) else None
        body = re.sub(r'\s+', ' ', f"{m.get('text') or ''} {result or ''}").strip()
        tab = f"[{m['channelName']}]" if m.get("channelName") else UNKNOWN_TAB
        out.append((TAB_MAP.get(tab, tab), SYSTEM_NAME if is_system else str(m.get("name") or ""), body))
    return out

def txt_messages(txt_content):
    """テキスト形式のログの発言の一覧（タブは HTML 形式のログと同じ「[メイン]」の形に揃える）"""
    messages = []
    for line in txt_content.splitlines():
        line_match = TXT_LINE_PATTERN.match(line)
        if line_match:
            tab, name, raw_body = line_match.group('tab', 'name', 'body')
            messages.append((f"[{tab.strip()}]", name.strip(), raw_body.strip()))
    return messages


# ==========================================
# 2. 1つのログファイルを読む
# ==========================================
def _to_rows(messages, records_from_message):
    """発言の一覧から、各システムの関数でロールの行を作って表にする"""
    return pd.DataFrame([r for tab, name, body in messages for r in records_from_message(tab, name, body)])

def parse_content(fname, content, records_from_message):
    """
    ログ1つ（ファイル名と中身）をロールの表にする。
    records_from_message(タブ, 名前, 本文): 1発言からロールの行（辞書のリスト）を作る、各システムの関数
    壊れた HTML（「<!DOCTYPE html>」だけ・NUL 文字入りなど）では lxml の例外がそのまま出る。
    呼び出し側で1ファイルごとに受け止めて、「読み込めませんでした」と知らせる（parse_files・_read_zip・履歴フォルダの読み込み）
    """
    content = logic_base.decode_log(content) if isinstance(content, bytes) else content.lstrip('﻿')

    if fname.lower().endswith(JSON_EXTS):
        return _to_rows(json_messages(content) or [], records_from_message)
    is_html_content = bool(re.search(r'<(?:html|body|p|span)\b', content, re.IGNORECASE))
    is_text_file = fname.lower().endswith(TEXT_EXTS)

    if is_html_content or fname.lower().endswith(HTML_EXTS):
        df = _to_rows(html_messages(content), records_from_message)
        # HTML のログを貼った .txt のつもりで読んだが、発言に「<span>」などの文字が入っていただけのテキストのログだった
        if df.empty and is_text_file:
            df = _to_rows(txt_messages(content), records_from_message)
        return df
    elif is_text_file:
        return _to_rows(txt_messages(content), records_from_message)

    return pd.DataFrame()

def log_messages(fname, content, include_system=False):
    """
    ログ1つ（ファイル名と中身）の発言の一覧（タブ, 名前, 本文）。形式の見分け方は parse_content と同じ。
    include_system: システムのメッセージ（ステータスの増減など）も含める
    """
    content = logic_base.decode_log(content) if isinstance(content, bytes) else content.lstrip('﻿')
    lower = fname.lower()
    if lower.endswith(JSON_EXTS):
        return json_messages(content, include_system) or []
    if re.search(r'<(?:html|body|p|span)\b', content, re.IGNORECASE) or lower.endswith(HTML_EXTS):
        messages = html_messages(content, include_system)
        if not messages and lower.endswith(TEXT_EXTS):
            messages = txt_messages(content)
        return messages
    if lower.endswith(TEXT_EXTS):
        return txt_messages(content)
    return []


# ==========================================
# 3. ZIPファイルを読む
# ==========================================
def _zip_member_name(z_info):
    """ZIP内のファイル名。日本語名は、ZIPを作ったソフトによって UTF-8 か Shift_JIS(cp932) で入っている"""
    if z_info.flag_bits & 0x800:
        return z_info.filename   # UTF-8 の印があれば、zipfile が正しく読めている
    # 印が無いと zipfile は cp437 として読むので、元のバイト列に戻してから読み直す
    try:
        raw = z_info.filename.encode('cp437')
    except UnicodeEncodeError:
        # cp437 に戻せない＝すでに正しい日本語名（別の欄に UTF-8 の名前が入っていて、zipfile がそれを読んだ）
        return z_info.filename
    for encoding in ('utf-8', 'cp932'):
        try:
            return raw.decode(encoding)
        except UnicodeError:
            pass
    return z_info.filename

# 自分のPC（.bat で起動）か公開サーバーか。公開サーバーはメモリが少なく、全員で共有するので上限を小さくする
IS_LOCAL = logic_base.is_local_machine()
_MB = 1024 * 1024

# 解凍後の大きさの上限（小さなZIPが解凍すると巨大になるものでメモリを使い切らないように）。
# ココフォリアのログは長いキャンペーンでも1MB未満（hist の最大 0.3MB）なので、公開サーバーでも十分な余裕がある
ZIP_MAX_FILE_BYTES = (200 if IS_LOCAL else 30) * _MB     # 中の1ファイル
ZIP_MAX_TOTAL_BYTES = (1024 if IS_LOCAL else 100) * _MB  # 中のログの合計

def _is_hidden_member(z_info):
    """Mac の ZIP に入る作業用のファイルなど（読まない）"""
    return z_info.filename.startswith(('__MACOSX', '.'))

def zip_log_bytes(zip_content):
    """
    ZIP の中のログの、解凍後の大きさの合計（ZIP の目録を読むだけなので軽い）。
    公開サーバーのアップロードの合計の上限に使う。開けない ZIP は ZIP そのものの大きさ
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            return sum(i.file_size for i in z.infolist()
                       if not _is_hidden_member(i) and i.filename.lower().endswith(LOG_EXTS))
    except Exception:
        return len(zip_content)

_TAB_FILE_PATTERN = re.compile(r'^(?P<room>.*)\[(?P<tab>[^\[\]]+)\]\s*\.[^.]+$')

def zip_members(df):
    """読み込んだ表の、ZIP の中のログ: [(表示名（「ファイル名」）, ZIP の名前), ...]（ZIP の外のログは入れない）"""
    if df.empty or ZIP_SOURCE_COL not in df.columns:
        return []
    pairs = df[['ファイル名', ZIP_SOURCE_COL]].dropna().drop_duplicates()
    return list(zip(pairs['ファイル名'], pairs[ZIP_SOURCE_COL]))

def overlapping_all_tab_files(members):
    """
    同じ ZIP の中に「部屋名[すべて]」（前の形式は [all]）と、同じ部屋のタブごとのファイル（部屋名[メイン] など）が
    両方あるときの、「すべて」のファイルの表示名（読み込んだ表の「ファイル名」）のリスト。
    ココフォリアの ZIP はこの形で、同じロールが両方に入っているので、最初は「すべて」の方を表示しない（ファイル名だけで判断する）。
    members: ZIP の中のログ [(表示名, ZIP の名前), ...]（zip_members）
    """
    groups = {}
    for name, zip_name in members:
        prefix = f"{zip_name}{ZIP_MEMBER_SEP}"
        if not str(name).startswith(prefix):
            continue
        inner = str(name)[len(prefix):]
        folder, _, short = inner.rpartition('/')
        found = _TAB_FILE_PATTERN.match(short)
        if found:
            groups.setdefault((zip_name, folder, found.group('room').strip()), []).append((found.group('tab').strip(), name))
    result = []
    for entries in groups.values():
        all_files = [n for tab, n in entries if tab.lower() in ALL_TAB_NAMES]
        if all_files and len(all_files) < len(entries):
            result += all_files
    return result

def _read_zip(zip_fname, zip_content, parse_one):
    """
    ZIP内のログを読む。parse_one(ファイル名, 中身): ログ1つを表にする関数（各システムの、使い回し付きのもの）。
    戻り値: (解析結果のリスト, 読み込めなかったことの説明のリスト)
    """
    dfs = []
    failed = []      # 読み込めなかったファイル（黙って捨てずに、まとめて知らせる）
    encrypted = []   # パスワード付きのファイル
    too_large = []   # 大きすぎて読まなかったファイル
    no_rolls = []    # 読めたが、ダイスロールが無かったファイル（ZIP から1つも読めなかったときだけ知らせる）
    total_bytes = 0
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            infos = [z_info for z_info in z.infolist() if not _is_hidden_member(z_info)]
            members = [(z_info, _zip_member_name(z_info)) for z_info in infos
                       if z_info.filename.lower().endswith(LOG_EXTS)]
            has_inner_zip = any(z_info.filename.lower().endswith('.zip') for z_info in infos)
            # 表示名はファイル名だけにする。別のフォルダに同じ名前のファイルがあるときだけ、フォルダも付けて区別する
            short_counts = Counter(name.split('/')[-1] for _, name in members)
            for z_info, clean_filename in members:
                short_name = clean_filename.split('/')[-1]
                if short_counts[short_name] > 1:
                    short_name = clean_filename
                if z_info.flag_bits & 0x1:
                    encrypted.append(short_name)
                    continue
                # 合計には読み込むファイルだけを数える（大きすぎて読まなかったファイルの分で、後の普通のファイルまで断らないように）
                if z_info.file_size > ZIP_MAX_FILE_BYTES or total_bytes + z_info.file_size > ZIP_MAX_TOTAL_BYTES:
                    too_large.append(short_name)
                    continue
                total_bytes += z_info.file_size
                try:
                    with z.open(z_info) as f:
                        df = parse_one(clean_filename, f.read(ZIP_MAX_FILE_BYTES + 1))
                    if not df.empty:
                        dfs.append(df.assign(ファイル名=f"{zip_fname}{ZIP_MEMBER_SEP}{short_name}", **{ZIP_SOURCE_COL: zip_fname}))
                    else:
                        no_rolls.append(short_name)
                except Exception as e:
                    failed.append(f"{short_name}（{type(e).__name__}）")
    except Exception as e:
        # エラーの中身は自分のPCのときだけ（公開サーバーでは種類だけを出す決まり。ほかの「読み込めませんでした」と揃える）
        detail = f"{type(e).__name__}: {e}" if IS_LOCAL else type(e).__name__
        return dfs, [f"ZIPファイル「{zip_fname}」を開けませんでした（{detail}）"]

    messages = []
    inner = "ZIP の中の ZIP は読み込まないので、解凍してから中のファイルを読み込ませてください。" if has_inner_zip else ""
    if not members:
        # 画像だけ・ZIP の中の ZIP だけなど、読めるログが1つも入っていない
        messages.append(f"「{zip_fname}」の中に、ココフォリアのログ（.html・.txt・.json）が見つかりませんでした。{inner}")
    elif inner:
        messages.append(f"「{zip_fname}」の中の ZIP ファイルは読み込みませんでした。{inner}")
    # ロールの無いファイル（雑談・情報のタブなど）は、ココフォリアの ZIP に普通に入っているので、
    # 1つも読めなかったときだけ知らせる（毎回出るとうるさいため）
    if no_rolls and not dfs:
        messages.append(f"「{zip_fname}」の中のログからダイスロールが見つかりませんでした: " + "、".join(no_rolls))
    if encrypted:
        messages.append(f"「{zip_fname}」はパスワード付きのため、中の {len(encrypted)} 個のファイルを読み込めませんでした。"
                        "解凍してから、中のファイルを読み込ませてください。")
    if too_large:
        messages.append(f"「{zip_fname}」の中の次のファイルは、解凍すると大きすぎるため読み込みませんでした"
                        f"（1ファイル {ZIP_MAX_FILE_BYTES // _MB}MB・合計 {ZIP_MAX_TOTAL_BYTES // _MB}MB まで）: "
                        + "、".join(too_large))
    if failed:
        messages.append(f"「{zip_fname}」の中の次のファイルを読み込めませんでした: " + "、".join(failed))
    return dfs, messages


# ==========================================
# 4. 読み込んだファイルをまとめて読む
# ==========================================
def parse_files(file_dict, parse_one):
    """
    読み込んだファイル（ファイル名 → 中身）をすべて解析して1つの表にする。
    parse_one(ファイル名, 中身): ログ1つを表にする関数（各システムの、使い回し付きのもの）。
    戻り値: (解析結果, 読み込めなかったファイルについての説明のリスト)。画面への表示はしない（表示は呼び出し側で行う）
    """
    all_dfs = []
    messages = []
    for fname, content in file_dict.items():
        if fname.lower().endswith('.zip'):
            zip_dfs, zip_messages = _read_zip(fname, content, parse_one)
            all_dfs.extend(zip_dfs)
            messages.extend(zip_messages)
        else:
            # 壊れたファイル1つで全体を止めないよう、ZIP の中と同じく1ファイルごとに受け止めて知らせる
            try:
                df = parse_one(fname, content)
            except Exception as e:
                messages.append(f"「{fname}」を読み込めませんでした（{type(e).__name__}）")
                continue
            if not df.empty:
                all_dfs.append(df.assign(ファイル名=fname))
            else:   # 黙って0件にせず知らせる（ロールの無いログ、読めない文字コード、ココフォリアのログでないファイルなど）
                messages.append(f"「{fname}」からダイスロールが見つかりませんでした。"
                                "ココフォリアのログ（.html か、それを貼った .txt）か確かめてください。")

    df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    return df, messages
