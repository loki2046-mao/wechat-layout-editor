#!/usr/bin/env python3
"""
公众号排版编辑器 — 一站式服务
端口 8790

使用流程：
1. 浏览器打开 http://localhost:8790
2. 粘贴飞书链接，点排版
3. 自动跳转编辑器
"""

import http.server
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

PORT = 8790
TOOLS_DIR = Path(__file__).parent
SCRIPT = TOOLS_DIR / "feishu_to_copy_page.py"
EDITOR_HTML = TOOLS_DIR / "editor.html"

# 当前serve的目录（generate后切换）
_serve_dir: Path | None = None


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # API: generate
        if path == "/api/generate":
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get("url", [None])[0]
            if not url:
                self._json(400, {"error": "缺少 url 参数"})
                return
            self._generate(url)
            return

        # 首页
        if path == "/" or path == "/index.html":
            self._serve_index()
            return

        # editor.html / copy.html 等 — 从当前输出目录serve
        global _serve_dir
        if _serve_dir:
            file_path = _serve_dir / path.lstrip("/")
            if file_path.is_file():
                self._serve_file(file_path)
                return

        # 从tools目录fallback
        file_path = TOOLS_DIR / path.lstrip("/")
        if file_path.is_file():
            self._serve_file(file_path)
            return

        self.send_error(404)

    def _generate(self, url):
        global _serve_dir
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--url", url, "--wechat"],
                capture_output=True, text=True, timeout=120,
                cwd=str(TOOLS_DIR),
            )
            if result.returncode != 0:
                err = result.stderr[-500:] if result.stderr else "排版脚本失败"
                self._json(500, {"error": err})
                return

            # Parse output
            output = result.stdout.strip()
            json_start = output.rfind("{")
            if json_start < 0:
                self._json(500, {"error": "无法解析输出"})
                return
            data = json.loads(output[json_start:])

            copy_path = Path(data.get("copy", ""))
            if not copy_path.exists():
                self._json(500, {"error": "copy.html 未生成"})
                return

            output_dir = copy_path.parent

            # 复制 editor.html 到输出目录
            shutil.copy2(EDITOR_HTML, output_dir / "editor.html")

            # 切换serve目录
            _serve_dir = output_dir

            self._json(200, {
                "ok": True,
                "title": data.get("title", output_dir.name),
                "block_count": data.get("block_count", 0),
                "editor_url": "/editor.html",
            })
        except subprocess.TimeoutExpired:
            self._json(500, {"error": "排版超时（120秒）"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _serve_index(self):
        html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>公众号排版编辑器</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "PingFang SC", sans-serif;
  background: linear-gradient(135deg, #f5ede2, #faf6f0);
  min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.card { background: #fff; border-radius: 24px; padding: 48px 40px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08); max-width: 520px; width: 100%; text-align: center; }
h1 { font-size: 22px; color: #2d1f15; margin-bottom: 8px; }
.sub { font-size: 14px; color: #9c8e7e; margin-bottom: 32px; }
input { width: 100%; padding: 14px 18px; border: 2px solid #e8e0d6; border-radius: 12px;
  font-size: 15px; outline: none; }
input:focus { border-color: #B8623C; }
button { margin-top: 16px; width: 100%; padding: 14px; background: #B8623C; color: #fff;
  border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; }
button:hover { background: #a0522a; }
button:disabled { background: #d4b89a; cursor: wait; }
#status { margin-top: 16px; font-size: 13px; color: #9c8e7e; min-height: 20px; }
#status.err { color: #c44; }
</style>
</head>
<body>
<div class="card">
  <h1>📝 公众号排版编辑器</h1>
  <p class="sub">粘贴飞书文档链接，一键生成排版</p>
  <input id="url" placeholder="https://xxx.feishu.cn/docx/..." autofocus />
  <button id="go">开始排版</button>
  <div id="status"></div>
</div>
<script>
const inp = document.getElementById("url");
const btn = document.getElementById("go");
const st  = document.getElementById("status");
inp.addEventListener("keydown", e => { if (e.key === "Enter") go(); });
btn.addEventListener("click", go);

async function go() {
  const url = inp.value.trim();
  if (!url) { st.textContent = "请输入飞书链接"; return; }
  btn.disabled = true;
  st.className = ""; st.textContent = "正在排版，请稍候...";
  try {
    const r = await fetch("/api/generate?url=" + encodeURIComponent(url));
    const d = await r.json();
    if (d.error) { st.className = "err"; st.textContent = d.error; btn.disabled = false; return; }
    st.textContent = "排版完成！跳转中...";
    window.location.href = d.editor_url;
  } catch(e) { st.className = "err"; st.textContent = e.message; btn.disabled = false; }
}
</script>
</body>
</html>"""
        self._html(html)

    def _serve_file(self, path: Path):
        ext = path.suffix.lower()
        ct = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
              ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json",
              ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{ct}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, text):
        data = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"🚀 http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
