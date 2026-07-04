import streamlit as st
import pandas as pd
import zipfile
import io
import re
from bs4 import BeautifulSoup

# ==========================================
# 全角英数・記号を半角にするための辞書
# ==========================================
ZEN = "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ＋－＊／＝＜＞（）［］，．"
HAN = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-*/=<>()[],."
ZEN2HAN = str.maketrans(ZEN, HAN)

# ==========================================
# 正規表現パターン
# ==========================================
COMMAND_PATTERN = re.compile(
    r'(?P<command>'
    r'(?:s?CC[^\s]*'       # CC, CCB, CC<=50, CC<=(10+20) など
    r'|s?1?d100[^\s]*'     # 1d100<=50 など
    r'|s?RES[^\s]*'        # RES, RESB など
    r'|s?CBR[^\s]*'        # CBR, CBRB など
    r'))'
    r'\s*(?P<skill>.*?)\s*'
    r'(?=(?:#\d+\s*)?\((?:1d100)<=)',
    re.IGNORECASE 
)
ROLL_PATTERN = re.compile(
    r'\((?:1d100)<=(?P<actual_target>-?\d+(?:,\d+)?)\).*?>' 
    r'(?:\s+(?:(?P<all_rolls>[\d,\s]+)>\s+)?(?P<roll>\d+)(?:\[.*?\])?\s+>)?'
    r'\s+(?P<result>[^\s]+)',
    re.IGNORECASE
)
BP_PATTERN = re.compile(r'ボーナス・ペナルティダイス\[(?P<bp>[-\d]+)\]')
BASE_PATTERN = re.compile(
    r'(?:CC[a-z]*[+-]?\d*|1d100)<=(?P<base_target>\d+)(?P<diff>[chre])?',
    re.IGNORECASE
)
TXT_LINE_PATTERN = re.compile(r'^\[(?P<tab>.*?)\]\s+(?P<name>.*?)\s+:\s+(?P<body>.*)$')

TAB_MAP = {
    "main": "メイン", "[main]": "[メイン]",
    "info": "情報",   "[info]": "[情報]",
    "other": "雑談",  "[other]": "[雑談]"
}

# ==========================================
# 1. データ行構築（組み立て係）
# ==========================================
def _get_command_id(raw_cmd):
    cmd_upper = raw_cmd.upper()
    is_secret = cmd_upper.startswith('S')
    core = cmd_upper[1:] if is_secret else cmd_upper

    if core.startswith('CBRB'): base = 'CBRB'
    elif core.startswith('CBR'): base = 'CBR'
    elif core.startswith('RESB'): base = 'RESB'
    elif core.startswith('RES'): base = 'RES'
    elif core.startswith('CCB'): base = 'CCB'
    elif core.startswith('CC'): base = 'CC'
    elif core.startswith('1D100') or core.startswith('D100'): base = '1D100'
    else: return raw_cmd 

    return f"s{base}" if is_secret else base

def _extract_roll_params(match, body):
    """正規表現を使って文字列から情報を引っこ抜く"""
    d = match.groupdict()
    cmd_match = COMMAND_PATTERN.search(body)

    base_skill_name = '---'
    
    prefix = body[:match.start()].strip()
    if not prefix or prefix == d.get('result'):
        cmd_id = 'CANCEL' 
    else:
        cmd_id = 'OTHER'
        
    if cmd_match:
        skill_raw = cmd_match.group('skill').strip()
        if skill_raw: base_skill_name = skill_raw
        
        raw_cmd = cmd_match.group('command').strip()
        cmd_id = _get_command_id(raw_cmd)

    bp_match = BP_PATTERN.search(body)
    bp_val = int(bp_match.group('bp')) if bp_match else 0
    
    actual_target_str = d['actual_target']
    if ',' in actual_target_str:
        actual_target_vals = [int(x) for x in actual_target_str.split(',')]
    else:
        actual_target_vals = [int(actual_target_str)]

    if len(actual_target_vals) > 1:
        base_target = None
        diff = None
    else:
        b_match = BASE_PATTERN.search(body)
        base_target = int(b_match.group('base_target')) if (b_match and b_match.group('base_target')) else None
        diff = b_match.group('diff').lower() if (b_match and b_match.group('diff')) else None

    roll_val = int(d['roll']) if d['roll'] else 0

    return {
        'base_skill_name': base_skill_name,
        'cmd_id': cmd_id,
        'bp_val': bp_val,
        'base_target': base_target,
        'actual_targets': actual_target_vals, 
        'diff': diff,
        'result_str': d['result'],
        'all_rolls_str': d.get('all_rolls'),
        'roll_val': roll_val
    }

def _build_roll_records(match, norm_body, raw_body, tab, name, i=0, multiple_rolls=False, base_cmd=""):
    """1回のロールにつき、目標値の数だけ行（辞書）を作ってリストで返す"""
    params = _extract_roll_params(match, norm_body)
    
    start, end = match.span()
    raw_log = raw_body
    
    cmd_match = COMMAND_PATTERN.search(norm_body)
    skill_name = params['base_skill_name']
    if cmd_match and cmd_match.group('skill').strip():
        s_start, s_end = cmd_match.span('skill')
        skill_name = raw_body[s_start:s_end].strip()

    if multiple_rolls:
        roll_text = raw_body[start:end]
        raw_log = f"{base_cmd} #{i+1} {roll_text}"
        skill_name = f"{skill_name}#{i+1}"
        
    dispray_tab = TAB_MAP.get(tab, tab)
    
    records = []
    for target_val in params['actual_targets']:
        records.append({
            'タブ': dispray_tab, 
            'キャラクター名': name, 
            'コマンド': params['cmd_id'],
            '判定名': skill_name,
            '目標値': params['base_target'] if params['base_target'] is not None else target_val, 
            '実目標値': target_val,
            '難易度': params['diff'] if params['diff'] else '通常',
            'B/P': params['bp_val'], 
            '出目': params['roll_val'],
            '全出目文字列': params['all_rolls_str'],
            '結果': params['result_str'],
            '生ログ': raw_log,
            '複数ロール': multiple_rolls
        })
    return records


# ==========================================
# 2. 形式別パーサー（職人：ファイル解読）
# ==========================================
def _extract_base_command(body, first_match):
    base_cmd_raw = body[:first_match.start()].strip()
    return re.sub(r'#\s*1\s*$', '', base_cmd_raw).strip()

def _parse_ccfolia_log_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    data = []
    for p_tag in soup.find_all('p'):
        spans = p_tag.find_all('span')
        if len(spans) >= 3:
            tab, name, raw_body = [s.get_text(strip=True) for s in spans[:3]]
            
            norm_body = raw_body.translate(ZEN2HAN)
            matches = list(ROLL_PATTERN.finditer(norm_body))
            
            if matches:
                multiple = len(matches) > 1
                base_cmd = _extract_base_command(raw_body, matches[0]) if multiple else ""
                for i, match in enumerate(matches):
                    data.extend(_build_roll_records(match, norm_body, raw_body, tab, name, i, multiple, base_cmd))
    return pd.DataFrame(data)

def _parse_ccfolia_log_txt(txt_content):
    data = []
    for line in txt_content.splitlines():
        line_match = TXT_LINE_PATTERN.match(line)
        if line_match:
            tab, name, raw_body = line_match.group('tab', 'name', 'body')
            tab, name = tab.strip(), name.strip()
            
            norm_body = raw_body.strip().translate(ZEN2HAN)
            matches = list(ROLL_PATTERN.finditer(norm_body))
            
            if matches:
                multiple = len(matches) > 1
                base_cmd = _extract_base_command(raw_body, matches[0]) if multiple else ""
                for i, match in enumerate(matches):
                    data.extend(_build_roll_records(match, norm_body, raw_body, tab, name, i, multiple, base_cmd))
    return pd.DataFrame(data)


# ==========================================
# 3. ファイルごとのルーティング（中継地点）
# ==========================================
@st.cache_data(show_spinner=False)
def _process_single_content(fname, content):
    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            content = content.decode('cp932', errors='replace')
            
    is_html_content = bool(re.search(r'<(?:html|body|p|span)\b', content, re.IGNORECASE))
    
    if is_html_content or fname.endswith(('.html', '.htm')):
        return _parse_ccfolia_log_html(content)
    elif fname.endswith(('.txt', '.md')):
        return _parse_ccfolia_log_txt(content)
        
    return pd.DataFrame()


# ==========================================
# 4. ZIP専用の解析機能（分離した関数）
# ==========================================
def _process_zip_content(zip_fname, zip_content):
    dfs = []
    try:
        zip_data = zip_content if isinstance(zip_content, bytes) else zip_content.encode('utf-8', errors='ignore')
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            for z_info in z.infolist():
                if z_info.filename.startswith('__MACOSX') or z_info.filename.startswith('.'):
                    continue
                
                if z_info.filename.endswith(('.html', '.htm', '.txt', '.md')):
                    try:
                        raw_name_bytes = z_info.filename.encode('cp437')
                        try:
                            clean_filename = raw_name_bytes.decode('utf-8')
                        except UnicodeError:
                            try:
                                clean_filename = raw_name_bytes.decode('cp932')
                            except UnicodeError:
                                clean_filename = z_info.filename
                        
                        with z.open(z_info) as f:
                            df = _process_single_content(clean_filename, f.read())
                            if not df.empty:
                                disp_name = f"{zip_fname} 内の {clean_filename.split('/')[-1]}"
                                df = df.assign(ファイル名=disp_name)
                                dfs.append(df)
                    except Exception:
                        continue
    except Exception:
        pass
    return dfs


# ==========================================
# 5. 🌟 外部公開API (メイン窓口)
# ==========================================
def get_all_parsed_data(file_dict):
    all_dfs = []
    
    for fname, content in file_dict.items():
        if fname.endswith('.zip'):
            zip_dfs = _process_zip_content(fname, content)
            all_dfs.extend(zip_dfs)
        else:
            df = _process_single_content(fname, content)
            if not df.empty:
                df = df.assign(ファイル名=fname) 
                all_dfs.append(df)

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()