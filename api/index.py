import json

from flask import Flask, jsonify, render_template_string, request

from app_enhanced import fetch_web_text, word_segment_and_count

app = Flask(__name__)

HTML_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>文章词频分析工具</title>
  <style>
    :root { color-scheme: light; font-family: Arial, Helvetica, sans-serif; }
    body { margin: 0; background: linear-gradient(135deg, #f3fff6 0%, #edf7ef 100%); color: #17311f; }
    .wrap { max-width: 980px; margin: 0 auto; padding: 32px 18px 60px; }
    .card { background: rgba(255,255,255,0.92); border-radius: 18px; padding: 18px; box-shadow: 0 12px 28px rgba(35, 86, 48, 0.12); }
    h1 { margin-top: 0; font-size: 1.8rem; }
    input, select, button { width: 100%; box-sizing: border-box; border-radius: 10px; border: 1px solid #cfe5d4; padding: 10px 12px; font-size: 1rem; }
    button { background: linear-gradient(135deg, #6bcf81, #3e9d5d); color: #fff; border: none; cursor: pointer; font-weight: 600; }
    .row { display: grid; gap: 12px; grid-template-columns: 1fr 140px; margin-top: 12px; }
    .result { margin-top: 18px; white-space: pre-wrap; background: #0f172a; color: #e5eefb; padding: 14px; border-radius: 14px; overflow: auto; }
    .hint { color: #4b6655; font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>📝 文章词频分析工具（Vercel 版）</h1>
      <p class="hint">输入文章链接后，系统会返回词频统计结果。此版本专为 Vercel Serverless 部署。</p>
      <input id="url" type="url" placeholder="例如：https://example.com/article" />
      <div class="row">
        <input id="min_freq" type="number" min="1" max="10" value="2" />
        <button onclick="analyze()">开始分析</button>
      </div>
      <p id="msg" class="hint"></p>
      <div id="result" class="result" style="display:none"></div>
    </div>
  </div>
  <script>
    async function analyze() {
      const url = document.getElementById('url').value.trim();
      const minFreq = Number(document.getElementById('min_freq').value || 2);
      const msg = document.getElementById('msg');
      const result = document.getElementById('result');
      if (!url) { msg.textContent = '请输入有效的文章链接。'; return; }
      msg.textContent = '正在分析，请稍候...';
      result.style.display = 'none';
      try {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url, min_freq: minFreq })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '分析失败');
        result.textContent = JSON.stringify(data, null, 2);
        result.style.display = 'block';
        msg.textContent = '分析完成。';
      } catch (e) {
        msg.textContent = e.message;
      }
    }
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(HTML_PAGE)


@app.post("/api/analyze")
def analyze():
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get("url") or "").strip()
        min_freq = int(payload.get("min_freq", 2) or 2)

        if not url:
            return jsonify({"error": "请输入文章链接"}), 400

        text, error = fetch_web_text(url)
        if error:
            return jsonify({"error": error}), 400

        word_count, top20 = word_segment_and_count(text, min_freq)
        if not word_count:
            return jsonify({"error": "分词结果为空，请降低筛选阈值后重试"}), 400

        return jsonify({
            "url": url,
            "text_len": len(text),
            "word_count": word_count,
            "top20": top20,
            "summary": top20[:10]
        })
    except Exception as exc:
        return jsonify({"error": f"分析失败：{exc}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
