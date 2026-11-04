"""Loopback-only visual preview for the Django template snapshot. No business backend."""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings

FRONTEND = Path(__file__).resolve().parents[1]
if not settings.configured:
    settings.configure(
        DEBUG=False, SECRET_KEY="local-template-preview-only",
        ROOT_URLCONF=__name__, USE_I18N=False, USE_TZ=True,
        STATIC_URL="/static/", INSTALLED_APPS=[],
    )

import django
django.setup()
from django.template import Context, Engine
from django.urls import path

ROUTES = json.loads((FRONTEND / "docs/routes-reference.json").read_text(encoding="utf-8"))
urlpatterns = [path(item["path"].lstrip("/"), lambda request: None, name=item["name"])
               for item in ROUTES if item.get("name")]
ENGINE = Engine(dirs=[str(FRONTEND / "templates")], debug=True,
                loaders=["django.template.loaders.filesystem.Loader"],
                libraries={"static": "django.templatetags.static"})
PAGES = {
    "/": "login.html", "/register/": "register.html", "/index/": "index.html",
    "/atest/": "analyse.html", "/adatabase/": "database.html", "/adatabase2/example/": "database2.html",
    "/use/": "use.html", "/user_single/": "dex.html", "/user_show/": "user_show.html",
    "/user_add/": "user_add.html", "/user_show/1/edit/": "user_edit.html",
    "/sort/": "sort.html", "/upload/": "upload.html", "/entity/": "entity.html", "/try/": "try.html",
}
CONTEXT = {
    "user_info": {"role": "1"}, "username": "Researcher", "error_msg": "",
    "csrf_token": "local-visual-preview-no-backend", "model_name": "", "sum": "",
    "data_list": [], "queryset": [], "page_string": "", "image_names": [],
}
PREVIEW_NAV = '''<details id="local-preview-tools" style="position:fixed;right:14px;bottom:12px;z-index:20000;background:#fff;color:#3c5b47;border:1px solid #d1dccb;border-radius:8px;padding:9px 12px;font:11px/1.6 'Segoe UI','Microsoft YaHei',sans-serif;box-shadow:0 3px 16px #102d1910;max-width:calc(100vw - 28px)">
<summary style="cursor:pointer">本地界面预览 · 未连接业务后台</summary>
<nav style="display:flex;flex-wrap:wrap;gap:13px;padding-top:9px"><a href="/">登录</a><a href="/register/">注册</a><a href="/index/">单图分析</a><a href="/atest/">批量分析</a><a href="/adatabase/">资源库</a><a href="/use/">使用说明</a></nav>
</details>'''


def render_page(template):
    return ENGINE.get_template(template).render(Context(CONTEXT)).replace("</body>", PREVIEW_NAV + "</body>")


class Handler(BaseHTTPRequestHandler):
    def send(self, code, content, content_type):
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def unavailable(self):
        self.send(503, json.dumps({"error": "本地仅预览界面，未连接业务后台。", "done": False}, ensure_ascii=False), "application/json; charset=utf-8")

    def do_POST(self):
        self.unavailable()

    def do_GET(self):
        route = unquote(urlsplit(self.path).path)
        if route.startswith("/static/"):
            base = (FRONTEND / "static").resolve()
            file = (base / route[len("/static/"):]).resolve()
            if base not in file.parents or not file.is_file():
                self.send(404, "Not found", "text/plain")
                return
            self.send(200, file.read_bytes(), mimetypes.guess_type(str(file))[0] or "application/octet-stream")
            return
        route = route if route == "/" else route.rstrip("/") + "/"
        if route in PAGES:
            try:
                self.send(200, render_page(PAGES[route]), "text/html; charset=utf-8")
            except Exception as error:
                self.send(500, str(error), "text/plain; charset=utf-8")
            return
        if route == "/favicon.ico/":
            self.send(204, b"", "image/x-icon")
            return
        self.unavailable()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    print(f"Local preview: http://127.0.0.1:{args.port}/", flush=True)
    print("Visual preview only. Login, model inference and exports require the real test backend.", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
