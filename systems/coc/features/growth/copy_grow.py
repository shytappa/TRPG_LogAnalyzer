import json
import streamlit.components.v1 as components

def render_copy_button(copy_text):
    """クリップボードにコピーする専用のボタンを描画する"""
    safe_text = json.dumps(copy_text)
    
    html_code = f"""
    <style>
        .copy-btn {{
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
            color: #0369a1;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            font-weight: 600;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            font-family: sans-serif;
            width: 100%;
            white-space: nowrap;
        }}
        .copy-btn:hover {{
            background-color: #e0f2fe;
            border-color: #7dd3fc;
        }}
        .copy-btn.success {{
            background-color: #10b981;
            color: white;
            border-color: #059669;
        }}
    </style>
    
    <div style="display: flex; justify-content: flex-end; margin-top: 5px;">
        <button id="custom-copy-btn" class="copy-btn">
            📋 成長する技能をコピー
        </button>
    </div>
    
    <script>
    document.getElementById('custom-copy-btn').addEventListener('click', async function() {{
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
    
    components.html(html_code, height=50)