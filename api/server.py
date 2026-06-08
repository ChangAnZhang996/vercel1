import os
import sys
import json
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, render_template_string, jsonify
from analysis_core import fetch_web_text, word_segment_and_count

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>文章词频分析工具</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%); 
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      color: #e2e8f0;
    }
    .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
    .header { text-align: center; margin-bottom: 32px; }
    .header h1 { font-size: 2rem; color: #f1f5f9; margin-bottom: 8px; }
    .header p { color: #94a3b8; }
    .card { 
      background: rgba(30, 41, 59, 0.8); 
      border: 1px solid rgba(148, 163, 184, 0.15); 
      border-radius: 16px; 
      padding: 24px; 
      margin-bottom: 24px;
    }
    .form-group { margin-bottom: 16px; }
    .form-group label { 
      display: block; 
      color: #cbd5e1; 
      margin-bottom: 8px; 
      font-weight: 500;
    }
    .form-group input, .form-group select {
      width: 100%;
      padding: 12px 16px;
      border: 1px solid rgba(148, 163, 184, 0.25);
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.8);
      color: #e2e8f0;
      font-size: 1rem;
    }
    .btn {
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 10px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
    }
    .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .status {
      margin-top: 12px;
      padding: 12px;
      border-radius: 8px;
      display: none;
    }
    .status.error { background: rgba(239, 68, 68, 0.15); color: #fca5a5; }
    .status.success { background: rgba(34, 197, 94, 0.15); color: #86efac; }
    .status.info { background: rgba(59, 130, 246, 0.15); color: #93c5fd; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    .result-section { margin-top: 32px; }
    .result-section h2 { color: #f1f5f9; margin-bottom: 16px; font-size: 1.3rem; }
    table { width: 100%; border-collapse: collapse; }
    th, td { 
      padding: 12px; 
      text-align: left; 
      border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    }
    th { background: rgba(15, 23, 42, 0.6); color: #94a3b8; }
    td { color: #e2e8f0; }
    .word-cloud {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 16px;
      background: rgba(15, 23, 42, 0.6);
      border-radius: 12px;
      min-height: 150px;
    }
    .word-item {
      padding: 4px 12px;
      border-radius: 20px;
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.3));
      font-size: 14px;
      transition: all 0.3s ease;
    }
    .word-item:hover { transform: scale(1.1); }
    .text-preview {
      background: rgba(15, 23, 42, 0.6);
      padding: 16px;
      border-radius: 12px;
      max-height: 200px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
      color: #cbd5e1;
      font-size: 0.9rem;
    }
    .stats {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }
    .stat-item {
      background: rgba(59, 130, 246, 0.1);
      padding: 12px 20px;
      border-radius: 10px;
      text-align: center;
      flex: 1;
    }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #3b82f6; }
    .stat-label { font-size: 0.85rem; color: #94a3b8; }
    .export-btn {
      background: linear-gradient(135deg, #10b981, #059669);
      margin-left: 12px;
    }
    @media (max-width: 768px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📝 文章词频分析工具</h1>
      <p>输入文章链接，自动抓取内容并进行中文分词与词频统计分析</p>
    </div>

    <div class="card">
      <div class="grid">
        <div>
          <div class="form-group">
            <label for="url">文章链接</label>
            <input type="url" id="url" placeholder="例如：https://example.com/article">
          </div>
          <div class="form-group">
            <label for="min_freq">最低词频</label>
            <select id="min_freq">
              <option value="1">1 (包含所有词)</option>
              <option value="2" selected>2 (过滤低频词)</option>
              <option value="3">3</option>
              <option value="5">5</option>
            </select>
          </div>
          <button class="btn" onclick="analyze()">开始分析</button>
          <div id="status" class="status"></div>
        </div>
        <div>
          <div style="background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 12px;">
            <h3 style="color: #94a3b8; margin-bottom: 12px;">📊 功能特性</h3>
            <ul style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.8;">
              <li>🌐 自动抓取网页正文</li>
              <li>📝 中文分词处理</li>
              <li>📈 词频统计分析</li>
              <li>☁️ 词云图展示</li>
              <li>📥 导出 Excel</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <div id="results" style="display: none;">
      <div class="card">
        <h2>📈 统计概览</h2>
        <div class="stats">
          <div class="stat-item">
            <div class="stat-value" id="total-words">-</div>
            <div class="stat-label">总词数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value" id="unique-words">-</div>
            <div class="stat-label">去重词数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value" id="text-length">-</div>
            <div class="stat-label">原文长度</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h2>☁️ 词云图</h2>
        </div>
        <div id="word-cloud" class="word-cloud"></div>
      </div>

      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h2>📋 词频排行 Top 20</h2>
          <button class="btn export-btn" onclick="exportExcel()">导出 Excel</button>
        </div>
        <table>
          <thead>
            <tr><th>词汇</th><th>词频</th><th>占比</th></tr>
          </thead>
          <tbody id="word-table"></tbody>
        </table>
      </div>

      <div class="card">
        <h2>📝 抓取文本预览</h2>
        <div id="text-preview" class="text-preview"></div>
      </div>
    </div>
  </div>

  <script>
    let currentData = null;

    async function analyze() {
      const url = document.getElementById('url').value.trim();
      const minFreq = document.getElementById('min_freq').value;
      const status = document.getElementById('status');
      const results = document.getElementById('results');

      if (!url) {
        showStatus('error', '请输入文章链接');
        return;
      }

      showStatus('info', '正在抓取网页并分析...');
      results.style.display = 'none';

      try {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url, min_freq: parseInt(minFreq) })
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.error || '分析失败');

        currentData = data;
        displayResults(data);
        showStatus('success', '分析完成！');
        results.style.display = 'block';
      } catch (e) {
        showStatus('error', '错误: ' + e.message);
      }
    }

    function showStatus(type, message) {
      const status = document.getElementById('status');
      status.textContent = message;
      status.className = 'status ' + type;
      status.style.display = 'block';
    }

    function displayResults(data) {
      document.getElementById('total-words').textContent = data.total_words || 0;
      document.getElementById('unique-words').textContent = Object.keys(data.word_count || {}).length;
      document.getElementById('text-length').textContent = (data.text?.length || 0).toLocaleString();

      const wordCloud = document.getElementById('word-cloud');
      wordCloud.innerHTML = '';
      const top20 = data.top20 || [];
      top20.forEach(([word, count]) => {
        const item = document.createElement('span');
        item.className = 'word-item';
        item.textContent = word;
        item.style.fontSize = Math.max(14, Math.min(32, 14 + count * 1.5)) + 'px';
        item.title = `${word}: ${count}次`;
        wordCloud.appendChild(item);
      });

      const table = document.getElementById('word-table');
      table.innerHTML = '';
      const total = data.total_words || 1;
      top20.forEach(([word, count]) => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${word}</td><td>${count}</td><td>${((count / total) * 100).toFixed(2)}%</td>`;
        table.appendChild(row);
      });

      const preview = document.getElementById('text-preview');
      preview.textContent = data.text?.substring(0, 2000) + (data.text?.length > 2000 ? '...' : '') || '暂无内容';
    }

    function exportExcel() {
      if (!currentData) return;

      let csv = '词汇,词频\n';
      Object.entries(currentData.word_count || {}).forEach(([word, count]) => {
        csv += `"${word}",${count}\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = '词频统计.csv';
      link.click();
    }
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(HTML_TEMPLATE)


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

        total_words = sum(word_count.values())

        return jsonify({
            "url": url,
            "text": text,
            "word_count": word_count,
            "top20": top20,
            "total_words": total_words
        })
    except Exception as exc:
        return jsonify({"error": f"分析失败：{str(exc)}"}), 500


handler = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
