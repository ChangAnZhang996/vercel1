import os
from flask import Flask

app = Flask(__name__)

@app.get("/")
def index():
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>测试页面</title>
  <style>
    body { background: #0f172a; color: white; text-align: center; padding: 100px; font-family: sans-serif; }
    h1 { color: #3b82f6; }
    .success { color: #22c55e; }
  </style>
</head>
<body>
  <h1>✅ 部署成功！</h1>
  <p class="success">文章词频分析工具</p>
  <p>服务已正常运行</p>
</body>
</html>
"""

handler = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
