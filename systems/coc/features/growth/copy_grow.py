import json
import streamlit as st
from ...components.styles_coc import ACTION_BUTTON_CSS

def render_copy_button(copy_text):
    """クリップボードにコピーする専用のボタンを描画する"""
    # JSONにしてJavaScriptの文字列として埋め込む。「</」は </script> と誤認されないようにエスケープする
    safe_text = json.dumps(copy_text).replace("</", "<\\/")

    html_code = f"""
    {ACTION_BUTTON_CSS}
    <button id="copy-btn" class="action-btn">📋 成長する技能をコピー</button>

    <script>
    document.getElementById('copy-btn').addEventListener('click', async function() {{
        const btn = this;
        const text = {safe_text};

        const showSuccess = () => {{
            btn.innerText = "✅ コピー完了！";
            btn.classList.add('success');
            setTimeout(() => {{
                btn.innerText = "📋 成長する技能をコピー";
                btn.classList.remove('success');
            }}, 2000);
        }};

        if (navigator.clipboard && window.isSecureContext) {{
            try {{
                await navigator.clipboard.writeText(text);
                showSuccess();
                return;
            }} catch (err) {{
                console.warn("Clipboard API failed, falling back...");
            }}
        }}

        // 古いブラウザ用：見えない入力欄に文字を入れてコピーする
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.top = "-9999px";
        document.body.appendChild(textArea);
        textArea.select();

        try {{
            document.execCommand("copy");
            showSuccess();
        }} catch (err) {{
            alert("コピーに失敗しました");
        }} finally {{
            document.body.removeChild(textArea);
        }}
    }});
    </script>
    """
    st.iframe(html_code, height=42)
