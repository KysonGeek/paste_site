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
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")
NOTES_DIR = os.path.abspath(os.environ.get("NOTES_DIR", os.path.join(os.path.dirname(__file__), "notes")))
MAX_BODY = int(os.environ.get("MAX_BODY", str(10 * 1024 * 1024)))  # 单次 POST 上限,默认 10MB
MAX_FILES = int(os.environ.get("MAX_FILES", "30"))  # txt 文件数量上限,默认 30

# 新建文件的"计数→落盘"必须原子,否则并发新建会冲破 MAX_FILES
_create_lock = threading.Lock()


def count_notes():
    """统计 NOTES_DIR 下已存在的 txt 文件数量(忽略 .tmp 临时文件)。"""
    try:
        return sum(1 for f in os.scandir(NOTES_DIR) if f.name.endswith(".txt") and f.is_file())
    except FileNotFoundError:
        return 0

# 合法 paste 名:字母数字、连字符、下划线、点(但不能以点开头,避免隐藏文件 / 路径穿越)
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def safe_path(name):
    """把 paste 名映射到 notes 目录下的 txt 文件路径;非法则返回 None。"""
    # 长度上限 200:临时文件名比 name 多 14 字符,须留在文件系统 NAME_MAX(255)内
    if not name or len(name) > 200 or not NAME_RE.match(name) or ".." in name:
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
  #err {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 9;
    padding: 6px 14px; background: #c0392b; color: #fff;
    font: 13px/1.4 -apple-system, "PingFang SC", sans-serif;
  }}
</style>
</head>
<body>
<div id="err" hidden></div>
<textarea id="ed" autofocus spellcheck="false">{content}</textarea>
<script>
const ed = document.getElementById('ed');
const err = document.getElementById('err');
const NAME = {name_json};
let timer = null, lastSaved = ed.value, inflight = false, pending = false;

function showErr(msg) {{
  err.textContent = msg;
  err.hidden = !msg;
}}

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
    if (r.ok) {{
      lastSaved = value;
      showErr('');
    }} else if (r.status >= 400 && r.status < 500) {{
      // 4xx 是确定性失败(超限/名字非法),自动重试无意义,亮出错误等用户处理
      showErr('保存失败 ' + r.status + ':' + await r.text());
    }} else {{
      throw new Error(r.status);
    }}
  }} catch (e) {{
    pending = true;  // 网络错误 / 5xx:稍后自动重试
    showErr('保存失败,正在重试…');
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
window.addEventListener('beforeunload', (e) => {{
  if (ed.value === lastSaved) return;
  navigator.sendBeacon && navigator.sendBeacon('/' + encodeURIComponent(NAME), ed.value);
  // 已知保存一直失败时拦一下,避免内容静默丢失;正常情况不打扰
  if (!err.hidden) {{ e.preventDefault(); e.returnValue = ''; }}
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

    def _send_text(self, code, body):
        return self._send(code, body, "text/plain; charset=utf-8")

    def _drain(self, length):
        # 提前拒绝时先读掉请求体:带未读数据关闭连接会触发 RST,冲掉已发出的响应
        remaining = min(length, 64 * 1024 * 1024)
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)

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
            name_json=json.dumps(name),
            content=html.escape(content),
        )
        return self._send(200, page)

    do_HEAD = do_GET

    def do_POST(self):
        name = self._name()
        path = safe_path(name)
        if path is None:
            return self._send_text(400, "bad name")
        # chunked 编码不解析;若放行,缺 Content-Length 会被当成空 body 清空笔记
        if self.headers.get("Transfer-Encoding"):
            return self._send_text(501, "chunked body not supported")
        if "Content-Length" not in self.headers:
            return self._send_text(411, "length required")
        try:
            length = int(self.headers["Content-Length"])
        except ValueError:
            return self._send_text(400, "bad content-length")
        if length < 0:
            return self._send_text(400, "bad content-length")
        if length > MAX_BODY:
            self._drain(length)
            return self._send_text(413, "body too large")
        os.makedirs(NOTES_DIR, exist_ok=True)
        # 数量上限仅约束新建;这里先无锁预检,满员时不必再收 body,最终裁决在写盘前的锁内
        if not os.path.exists(path) and count_notes() >= MAX_FILES:
            self._drain(length)
            return self._send_text(403, f"file limit reached ({MAX_FILES})")
        body = self.rfile.read(length) if length else b""
        if len(body) != length:
            # 客户端中途断开,拒绝把截断内容写盘覆盖旧数据
            return self._send_text(400, "incomplete body")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            text = body.decode("utf-8", errors="replace")
        # 原子写:每个请求用独立临时文件,避免并发共用 .tmp 互相截断
        fd, tmp = tempfile.mkstemp(dir=NOTES_DIR, prefix="." + name + ".", suffix=".tmp")
        try:
            os.fchmod(fd, 0o644)  # mkstemp 默认 0600,恢复成对外可读
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            with _create_lock:
                if not os.path.exists(path) and count_notes() >= MAX_FILES:
                    os.unlink(tmp)
                    return self._send_text(403, f"file limit reached ({MAX_FILES})")
                os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return self._send_text(200, "ok")

    def log_message(self, fmt, *args):
        pass  # 静默,需要日志时去掉这行


def main():
    os.makedirs(NOTES_DIR, exist_ok=True)
    # 清扫上次异常退出(SIGKILL/断电)留下的孤儿临时文件;本进程是唯一写者,启动时清理安全
    for entry in os.scandir(NOTES_DIR):
        if entry.name.startswith(".") and entry.name.endswith(".tmp") and entry.is_file():
            try:
                os.unlink(entry.path)
            except OSError:
                pass
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"paste 运行中  →  http://{HOST}:{PORT}")
    print(f"数据目录: {NOTES_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
