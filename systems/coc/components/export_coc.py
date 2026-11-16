import json
import streamlit as st
from .styles_coc import ACTION_BUTTON_CSS, Colors

# ==========================================
# 画像保存機能
# ==========================================
HTML2CANVAS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"

def render_screenshot_button(target_id, file_prefix):
    """
    画面上の要素（id=target_id）を画像として保存するボタン。
    ファイル名は「{file_prefix}_年月日_時分秒.png」（押した時刻）。
    同じ名前で保存してブラウザに「(1)」「(2)」と付けられないよう、秒まで入れる。
    """
    safe_prefix = json.dumps(file_prefix)
    # 画像にする部品（html2canvas）は、アプリの static/ フォルダから読む（インターネットにつながっていなくても使える）。
    # 読めなかったとき（static を配っていない起動のしかたなど）は、インターネットから読む
    html_code = f"""
    <script src="/app/static/html2canvas.min.js"></script>
    <script>
    if (typeof html2canvas === 'undefined') {{
        document.write('<script src="{HTML2CANVAS_CDN}"><\\/script>');
    }}
    </script>
    {ACTION_BUTTON_CSS}
    <button id="dl-btn" class="action-btn">📸 画像として保存</button>

    <script>
    function timestamp() {{
        const d = new Date();
        const p = (n) => String(n).padStart(2, '0');
        return `${{d.getFullYear()}}${{p(d.getMonth() + 1)}}${{p(d.getDate())}}_${{p(d.getHours())}}${{p(d.getMinutes())}}${{p(d.getSeconds())}}`;
    }}

    document.getElementById('dl-btn').addEventListener('click', function() {{
        const btn = this;
        const originalText = "📸 画像として保存";
        if (typeof html2canvas === 'undefined') {{
            alert("画像保存の部品を読み込めませんでした。static フォルダに html2canvas.min.js があるか、インターネットにつながっているか確認して、ページを開き直してください。");
            return;
        }}
        btn.innerText = "⏳ 処理中...";

        // Streamlit本体（親ウィンドウ）から要素を探す
        const target = window.parent.document.getElementById('{target_id}');
        if (!target) {{
            alert("保存対象が見つかりません。");
            btn.innerText = originalText;
            return;
        }}

        // 横スクロールで隠れている部分（画面に収まらない表の右側など）も写るように、
        // はみ出している幅の分だけ撮影範囲を広げ、複製した要素のスクロールと固定表示（sticky）を解除してから撮影する
        const scrollers = Array.from(target.querySelectorAll('*')).filter(e =>
            e.scrollWidth > e.clientWidth + 1 && window.parent.getComputedStyle(e).overflowX !== 'visible');
        const extra = Math.max(0, ...scrollers.map(e => e.scrollWidth - e.clientWidth));
        const fullWidth = target.clientWidth + extra;
        // ブラウザが作れる画像の大きさには上限がある（Chrome は縦横 32767px まで・面積も上限あり）。
        // 成長チェックの ALL など縦に長いときは、上限に収まるまで倍率（ふだんは2倍）を下げる
        const MAX_SIDE = 32000, MAX_AREA = 250000000;
        const fullHeight = target.scrollHeight;
        const scale = Math.min(2, MAX_SIDE / fullHeight, MAX_SIDE / fullWidth, Math.sqrt(MAX_AREA / (fullWidth * fullHeight)));

        html2canvas(target, {{
            backgroundColor: '{Colors.WHITE}',
            scale: scale,
            useCORS: true,
            width: fullWidth,
            windowWidth: window.parent.document.documentElement.clientWidth + extra,
            onclone: (doc) => {{
                const el = doc.getElementById('{target_id}');
                el.style.width = fullWidth + 'px';
                el.style.maxWidth = 'none';
                el.querySelectorAll('*').forEach(n => {{
                    if (n.scrollWidth > n.clientWidth + 1) n.style.overflow = 'visible';
                    if (doc.defaultView.getComputedStyle(n).position === 'sticky') n.style.position = 'relative';
                }});
            }}
        }}).then(canvas => {{
            const dataUrl = canvas.width && canvas.height ? canvas.toDataURL('image/png') : "data:,";
            if (dataUrl === "data:,") {{   // 大きすぎて画像を作れなかった（空の画像になる）
                throw new Error("画像が大きすぎて作れませんでした");
            }}
            const link = document.createElement('a');
            link.download = {safe_prefix} + "_" + timestamp() + ".png";
            link.href = dataUrl;
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
            btn.innerText = "❌ 保存できませんでした";
            if (String(err).includes("大きすぎ")) alert("画像が大きすぎて作れませんでした。表示するキャラを減らしてから保存してください。");
            setTimeout(() => {{ btn.innerText = originalText; }}, 3000);
        }});
    }});
    </script>
    """
    st.iframe(html_code, height=42)
