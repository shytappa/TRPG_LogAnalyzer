import streamlit as st

def apply_custom_css(is_launcher=False):
    """サイドバーやウィジェットの共通デザイン（CSS）を適用する"""
    st.markdown("""
        <style>
        /* =========================================
           1. 全体設定
        ========================================= */
        /* 左上のページリスト（ナビゲーション）を非表示 */
        [data-testid="stSidebarNav"] { display: none; }

        /* 📊 ダッシュボードのステータスメトリクス */
        .stMetric { background: #f0f2f6; padding: 10px; border-radius: 10px; }

        /* =========================================
           2. メイン画面（画面A）のアップローダー
        ========================================= */
        section[data-testid="stMain"] [data-testid="stFileUploader"] { 
            padding-bottom: 15px !important; }

        /* ドロップゾーン全体（中央揃えレイアウト） */
        section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] {
            min-height: 400px !important; 
            display: flex !important; 
            flex-direction: column !important; 
            justify-content: center !important; 
            align-items: center !important; 
            gap: 15px !important; 
            box-sizing: border-box !important; 
            position: relative !important; }
                
        /* 参照ボタン */
        section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] button { 
            position: absolute !important; 
            left: 40px !important; 
            top: 50% !important; 
            transform: translateY(-50%) !important; 
            margin: 0 !important; 
            padding: 10px 24px !important; }

        /* ドロップゾーン内のテキスト */
        section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] span, 
        section[data-testid="stMain"] [data-testid="stFileUploaderDropzone"] small { 
            font-size: 18px !important; }

        /* =========================================
           3. サイドバーのUI調整
        ========================================= */
        /* 文字が途切れないように折り返しを許可 */ 
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label div,
        [data-testid="stSidebar"] [data-testid="stToggle"] label div,
        [data-testid="stSidebar"] [data-testid="stRadio"] label div { 
            white-space: normal !important; 
            word-break: break-word !important; 
            overflow: visible !important; }
        
        /* ラジオボタンの隙間を広げて押しやすく */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] > label { 
            margin-bottom: 0.5em !important; }
                
        /* 複数行になった時、チェックボックスの四角を上寄せに固定 */
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
        [data-testid="stSidebar"] [data-testid="stToggle"] label { 
            align-items: flex-start !important; }
        
        /* =========================================
           4. 全選択・全解除ボタン（Tertiary Button）
        ========================================= */
        /* ボタンを包む親要素を右寄せにする */
        div[data-testid="stButton"]:has(button[kind="tertiary"]) { 
            display: flex !important; 
            justify-content: flex-end !important; 
            margin-top: 4px !important; 
            overflow: hidden !important; }

        /* ボタン本体をコンパクトに */
        button[kind="tertiary"] { 
            padding: 0px !important; 
            min-height: 20px !important; 
            max-width: 100% !important; }

        /* ボタン内のテキスト（リンク風） */
        button[kind="tertiary"] p { 
            font-size: 12px !important; 
            text-decoration: underline !important; 
            color: #888888 !important; 
            white-space: nowrap !important; 
            overflow: hidden !important; 
            text-overflow: ellipsis !important; 
            width: 100% !important; 
            display: block !important; }
        
        /* =========================================
           5. サイドバーのヘッダー（透明化・スクロール追従）
        ========================================= */
        [data-testid="stSidebarHeader"] {
            position: sticky !important;
            top: 0px !important;
            z-index: 99998 !important;
            background-color: transparent !important;
            pointer-events: none !important; }

        /* =========================================
           6. 開く・閉じるボタン（共通フローティング設定）
        ========================================= */
        button[kind="headerNoPadding"],
        button[data-testid="stBaseButton-headerNoPadding"] {
            pointer-events: auto !important;
            background-color: var(--secondary-background-color, #f0f2f6) !important;
            border-radius: 50% !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
            width: 42px !important;
            height: 42px !important;
            margin-top: 12px !important;
            margin-left: 12px !important;
            transition: 0.2s !important;
            z-index: 99999 !important; }

        button[kind="headerNoPadding"]:hover,
        button[data-testid="stBaseButton-headerNoPadding"]:hover { transform: scale(1.1) !important; }
        
        /* =========================================
           7. 区切り線（Divider）の余白調整
        ========================================= */
        [data-testid="stSidebar"] hr {
            margin-top: 10px !important;
            margin-bottom: 15px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ランチャー画面（app.py）専用のCSS追加
    if is_launcher:
        st.markdown("""
            <style>
            /* メイン画面の大きなボタン用スタイル */
            .stButton > button {
                height: 100px;
                font-size: 18px;
            }
            </style>
        """, unsafe_allow_html=True)