import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from analysis_core import fetch_web_text, word_segment_and_count

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>文章词频分析工具</title>
  <style>
    body { background: linear-gradient(135deg, #0f172a, #1e293b); min-height: 100vh; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    .container { max-width: 800px; margin: 0 auto; padding: 24px; }
    .card { background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(148,163,184,0.15); border-radius: 16px; padding: 24px; margin-bottom: 24px; }
    h1 { color: #f1f5f9; text-align: center; margin-bottom: 8px; }
    p { color: #94a3b8; text-align: center; margin-bottom: 24px; }
    input, select, button { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid rgba(148,163,184,0.25); background: rgba(15,23,42,0.8); color: #e2e8f0; font-size: 1rem; margin-bottom: 12px; }
    button { background: linear-gradient(135deg, #3b82f6, #8b5cf6); border: none; cursor: pointer; font-weight: 600; }
    .status { padding: 12px; border-radius: 8px; margin-top: 12px; display: none; }
    .status.success { background: rgba(34,197,94,0.15); color: #86efac; }
    .status.error { background: rgba(239,68,68,0.15); color: #fca5a5; }
    .status.info { background: rgba(59,130,246,0.15); color: #93c5fd; }
    .word-cloud { display: flex; flex-wrap: wrap; gap: 8px; padding: 16px; background: rgba(15,23,42,0.6); border-radius: 12px; }
    .word { padding: 4px 12px; background: rgba(59,130,246,0.3); border-radius: 20px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(148,163,184,0.1); }
    th { background: rgba(15,23,42,0.6); color: #94a3b8; }
    .stats { display: flex; gap: 16px; margin-bottom: 16px; }
    .stat { flex: 1; text-align: center; padding: 12px; background: rgba(59,130,246,0.1); border-radius: 10px; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #3b82f6; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📝 文章词频分析工具</h1>
    <p>输入文章链接，自动抓取内容并进行词频统计</p>
    
    <div class="card">
      <input type="url" id="url" placeholder="请输入文章链接">
      <select id="min_freq">
        <option value="1">最低词频: 1</option>
        <option value="2" selected>最低词频: 2</option>
        <option value="3">最低词频: 3</option>
      </select>
      <button onclick="analyze()">开始分析</button>
      <div id="status" class="status"></div>
    </div>

    <div id="results" style="display: none;">
      <div class="card">
        <h2>📈 统计概览</h2>
        <div class="stats">
          <div class="stat"><div class="stat-value" id="total">-</div><div>总词数</div></div>
          <div class="stat"><div class="stat-value" id="unique">-</div><div>去重词数</div></div>
        </div>
      </div>

      <div class="card">
        <h2>☁️ 词云图</h2>
        <div id="wordcloud" class="word-cloud"></div>
      </div>

      <div class="card">
        <h2>📋 词频排行</h2>
        <table><thead><tr><th>词汇</th><th>词频</th></tr></thead><tbody id="table"></tbody></table>
      </div>
    </div>
  </div>

  <script>
    async function analyze() {
      const url = document.getElementById('url').value.trim();
      const minFreq = document.getElementById('min_freq').value;
      const status = document.getElementById('status');
      const results = document.getElementById('results');

      if (!url) { showStatus('error', '请输入文章链接'); return; }
      showStatus('info', '正在分析...');
      results.style.display = 'none';

      try {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, min_freq: parseInt(minFreq) })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error);
        
        document.getElementById('total').textContent = data.total_words;
        document.getElementById('unique').textContent = Object.keys(data.word_count).length;
        
        const cloud = document.getElementById('wordcloud');
        cloud.innerHTML = '';
        data.top20.forEach(([word, count]) => {
          const span = document.createElement('span');
          span.className = 'word';
          span.textContent = word;
          span.style.fontSize = Math.max(14, Math.min(28, 14 + count)) + 'px';
          cloud.appendChild(span);
        });

        const table = document.getElementById('table');
        table.innerHTML = data.top20.map(([word, count]) => `<tr><td>${word}</td><td>${count}</td></tr>`).join('');

        showStatus('success', '分析完成！');
        results.style.display = 'block';
      } catch (e) {
        showStatus('error', '错误: ' + e.message);
      }
    }

    function showStatus(type, msg) {
      const s = document.getElementById('status');
      s.textContent = msg;
      s.className = 'status ' + type;
      s.style.display = 'block';
    }
  </script>
</body>
</html>
"""

@app.get("/")
def index():
    return HTML

@app.post("/api/analyze")
def analyze():
    try:
        payload = request.get_json(silent=True) or {}
        url = (payload.get("url") or "").strip()
        min_freq = int(payload.get("min_freq", 2))
        
        if not url:
            return jsonify({"error": "请输入文章链接"}), 400
        
        text, error = fetch_web_text(url)
        if error:
            return jsonify({"error": error}), 400
        
        word_count, top20 = word_segment_and_count(text, min_freq)
        if not word_count:
            return jsonify({"error": "分词结果为空"}), 400
        
        return jsonify({
            "word_count": word_count,
            "top20": top20,
            "total_words": sum(word_count.values())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

handler = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
