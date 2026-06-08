import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, render_template_string, jsonify
from analysis_core import fetch_web_text, word_segment_and_count

app = Flask(__name__)

HTML_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>文章词频分析工具</title>
  <style>
    body { margin: 0; background: linear-gradient(135deg, #07111f 0%, #0f172a 45%, #111827 100%); color: #e5eefb; font-family: Arial, sans-serif; }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 24px 16px; }
    .card { background: rgba(15,23,42,0.90); border: 1px solid rgba(148,163,184,0.18); border-radius: 18px; padding: 24px; }
    h1 { margin-top: 0; font-size: 1.9rem; color: #e5eefb; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
    label { display: block; color: #bfdbfe; margin-bottom: 8px; }
    input, button { width: 100%; box-sizing: border-box; border-radius: 10px; border: 1px solid rgba(148,163,184,0.25); padding: 12px; font-size: 1rem; }
    input { background: rgba(15,23,42,0.86); color: #e5eefb; }
    button { background: linear-gradient(135deg, #38bdf8, #8b5cf6); color: white; border: none; cursor: pointer; font-weight: 700; }
    .result { margin-top: 20px; display: none; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(148,163,184,0.15); }
    th { background: rgba(30,41,59,0.95); color: #bae6fd; }
    pre { white-space: pre-wrap; word-break: break-word; max-height: 300px; overflow-y: auto; background: rgba(30,41,59,0.98); padding: 15px; border-radius: 10px; }
    .status { margin-top: 10px; padding: 10px; border-radius: 8px; }
    .error { background: rgba(239,68,68,0.15); color: #fca5a5; }
    .success { background: rgba(34,197,94,0.15); color: #86efac; }
    @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>📝 文章词频分析工具</h1>
      <p style="color: #cbd5e1;">输入文章链接，系统将抓取内容并进行词频统计分析。</p>
      
      <div class="grid">
        <div>
          <label for="url">文章 URL</label>
          <input id="url" type="url" placeholder="例如：https://example.com/article" />
          
          <label for="min_freq" style="margin-top: 12px;">最低词频</label>
          <input id="min_freq" type="number" min="1" max="10" value="2" />
          
          <button onclick="analyze()" style="margin-top: 12px;">开始分析</button>
          <div id="status" class="status"></div>
        </div>
        <div>
          <div style="background: rgba(30,41,59,0.98); border-radius: 12px; padding: 15px;">
            <div style="color: #bae6fd; font-size: 0.95rem; margin-bottom: 8px;">📊 分析结果预览</div>
            <div id="preview" style="color: #e2e8f0; font-size: 0.9rem;">等待输入...</div>
          </div>
        </div>
      </div>

      <div id="result" class="result" style="margin-top: 20px;">
        <h2 style="color: #e5eefb; font-size: 1.2rem;">📌 词频前 20</h2>
        <table>
          <thead><tr><th>词汇</th><th>词频</th></tr></thead>
          <tbody id="top20"></tbody>
        </table>
        
        <h2 style="color: #e5eefb; font-size: 1.2rem; margin-top: 20px;">🧾 抓取文本预览</h2>
        <pre id="text"></pre>
      </div>
    </div>
  </div>
  
  <script>
    async function analyze() {
      const url = document.getElementById('url').value.trim();
      const minFreq = Number(document.getElementById('min_freq').value || 2);
      const status = document.getElementById('status');
      const preview = document.getElementById('preview');
      const result = document.getElementById('result');
      const top20 = document.getElementById('top20');
      const text = document.getElementById('text');
      
      if (!url) {
        status.textContent = '请输入有效的文章链接';
        status.className = 'status error';
        return;
      }
      
      status.textContent = '正在分析，请稍候...';
      status.className = 'status';
      preview.textContent = '正在抓取网页内容...';
      result.style.display = 'none';
      
      try {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ url, min_freq: minFreq })
        });
        
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.error || '分析失败');
        
        const items = data.top20 || [];
        top20.innerHTML = items.map(([word, count]) => `<tr><td>${word}</td><td>${count}</td></tr>`).join('');
        text.textContent = data.text?.substring(0, 2000) + (data.text?.length > 2000 ? '...' : '') || '暂无内容';
        preview.textContent = `已统计 ${Object.keys(data.word_count || {}).length} 个有效词汇`;
        status.textContent = '分析完成！';
        status.className = 'status success';
        result.style.display = 'block';
      } catch (e) {
        status.textContent = '错误：' + e.message;
        status.className = 'status error';
        preview.textContent = '分析失败，请重试';
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
            "text": text,
            "word_count": word_count,
            "top20": top20
        })
    except Exception as exc:
        return jsonify({"error": f"分析失败：{str(exc)}"}), 500


handler = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
