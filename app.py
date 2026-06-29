#!/usr/bin/env python3
"""paste.qixin.ch — 路径对应一个 txt 文件,网页可编辑、内容变动时自动保存。

零依赖,只用 Python 标准库。运行:
    python3 app.py            # 监听 0.0.0.0:8000
    PORT=9000 python3 app.py  # 自定义端口
    NOTES_DIR=/data python3 app.py  # 自定义数据目录
"""

import html
import json
import os
import re
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")
NOTES_DIR = os.path.abspath(os.environ.get("NOTES_DIR", os.path.join(os.path.dirname(__file__), "notes")))

# 合法 paste 名:字母数字、连字符、下划线、点(但不能以点开头,避免隐藏文件 / 路径穿越)
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def safe_path(name):
    """把 paste 名映射到 notes 目录下的 txt 文件路径;非法则返回 None。"""
    if not name or not NAME_RE.match(name) or ".." in name:
        return None
    path = os.path.abspath(os.path.join(NOTES_DIR, name + ".txt"))
    # 双重保险:确保最终路径仍在 NOTES_DIR 内
    if os.path.commonpath([path, NOTES_DIR]) != NOTES_DIR:
        return None
    return path


PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; height: 100%; }}
  textarea {{
    display: block; width: 100%; height: 100%;
    border: 0; outline: 0; resize: none;
    padding: 14px; font-size: 16px; line-height: 1.5;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    background: #ffffff; color: #222; -webkit-text-size-adjust: 100%;
  }}
</style>
</head>
<body>
<textarea id="ed" autofocus spellcheck="false">{content}</textarea>
<script>
const ed = document.getElementById('ed');
const NAME = {name_json};
let timer = null, lastSaved = ed.value, inflight = false, pending = false;

async function save() {{
  if (inflight) {{ pending = true; return; }}
  const value = ed.value;
  if (value === lastSaved) return;
  inflight = true;
  try {{
    const r = await fetch('/' + encodeURIComponent(NAME), {{
      method: 'POST',
      headers: {{ 'Content-Type': 'text/plain; charset=utf-8' }},
      body: value,
    }});
    if (!r.ok) throw new Error(r.status);
    lastSaved = value;
  }} catch (e) {{
    pending = true;
  }} finally {{
    inflight = false;
    if (pending) {{ pending = false; setTimeout(save, 800); }}
  }}
}}

ed.addEventListener('input', () => {{
  clearTimeout(timer);
  timer = setTimeout(save, 600);
}});
// 失焦 / 离开页面时尽量保存
ed.addEventListener('blur', save);
document.addEventListener('visibilitychange', () => {{ if (document.hidden) save(); }});
window.addEventListener('beforeunload', () => {{
  if (ed.value !== lastSaved) {{ navigator.sendBeacon && navigator.sendBeacon('/' + encodeURIComponent(NAME), ed.value); }}
}});
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "paste/1.0"

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _name(self):
        path = urllib.parse.urlparse(self.path).path
        return urllib.parse.unquote(path.strip("/"))

    def do_GET(self):
        name = self._name()
        if name in ("", "index.html"):
            self.send_response(302)
            self.send_header("Location", "/note")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if name == "favicon.ico":
            return self._send(204, b"")

        path = safe_path(name)
        if path is None:
            return self._send(400, "<h1>400 非法路径名</h1>")
        content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        page = PAGE.format(
            title=html.escape(name) + " · paste",
            name=html.escape(name),
            name_json=json.dumps(name),
            content=html.escape(content),
        )
        return self._send(200, page)

    do_HEAD = do_GET

    def do_POST(self):
        name = self._name()
        path = safe_path(name)
        if path is None:
            return self._send(400, "bad name", "text/plain; charset=utf-8")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            text = body.decode("utf-8", errors="replace")
        os.makedirs(NOTES_DIR, exist_ok=True)
        # 原子写:先写临时文件再 rename,避免并发/中断损坏
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
        return self._send(200, "ok", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        pass  # 静默,需要日志时去掉这行


def main():
    os.makedirs(NOTES_DIR, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"paste 运行中  →  http://{HOST}:{PORT}")
    print(f"数据目录: {NOTES_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
