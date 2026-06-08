import os
import sys
import subprocess
import threading
import time
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

PORT = find_free_port()
STREAMLIT_PROCESS = None

def start_streamlit():
    global STREAMLIT_PROCESS
    if STREAMLIT_PROCESS is None:
        STREAMLIT_PROCESS = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "app_enhanced.py",
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false",
            "--browser.serverAddress", "127.0.0.1",
            "--browser.gatherUsageStats", "false"
        ], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        for _ in range(30):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', PORT))
                    return
            except ConnectionRefusedError:
                time.sleep(1)
        raise RuntimeError("Streamlit failed to start")

start_streamlit()

from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    url = f"http://127.0.0.1:{PORT}/{path}"
    if request.query_string:
        url += f"?{request.query_string.decode('utf-8')}"
    
    headers = {key: value for key, value in request.headers if key != 'Host'}
    
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30
        )
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(key, value) for key, value in resp.raw.headers.items() 
                           if key.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, response_headers)
    except Exception as e:
        return str(e), 500

handler = app
