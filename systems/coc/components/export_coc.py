import streamlit.components.v1 as components

# ==========================================
# 画像保存機能
# ==========================================
def render_screenshot_button(target_id, file_name):
    html_code = f"""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    
    <style>
        /* コピーボタンと全く同じテーマ */
        .export-btn {{
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
            width: 100%; /* 横幅をカラム幅いっぱいに合わせる */
            white-space: nowrap;
        }}
        .export-btn:hover {{
            background-color: #e0f2fe;
            border-color: #7dd3fc;
        }}
        .export-btn:active {{
            transform: translateY(1px);
        }}
        .export-btn.success {{
            background-color: #10b981;
            color: white;
            border-color: #059669;
        }}
    </style>
    
    <div style="display: flex; justify-content: flex-end; margin-top: 5px;">
        <button id="dl-btn-{target_id}" class="export-btn">
            📸 画像として保存
        </button>
    </div>
    
    <script>
    document.getElementById('dl-btn-{target_id}').addEventListener('click', function() {{
        const btn = this;
        const originalText = "📸 画像として保存";
        btn.innerText = "⏳ 処理中...";
        
        // Streamlit本体（親ウィンドウ）から要素を探す
        const target = window.parent.document.getElementById('{target_id}');
        if (!target) {{
            alert("保存対象が見つかりません。");
            btn.innerText = originalText;
            return;
        }}
        
        html2canvas(target, {{ 
            backgroundColor: '#ffffff', 
            scale: 2,
            useCORS: true 
        }}).then(canvas => {{
            const link = document.createElement('a');
            link.download = '{file_name}.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
            
            // 成功したら緑色にする
            btn.innerText = "✅ 保存完了！";
            btn.classList.add('success');
            setTimeout(() => {{ 
                btn.innerText = originalText; 
                btn.classList.remove('success');
            }}, 2000);
        }}).catch(err => {{
            console.error("画像化エラー:", err);
            btn.innerText = "❌ エラーが発生しました";
            setTimeout(() => {{ btn.innerText = originalText; }}, 3000);
        }});
    }});
    </script>
    """
    
    components.html(html_code, height=50)