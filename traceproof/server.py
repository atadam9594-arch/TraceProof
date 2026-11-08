"""Local-only, stateless HTTP UI. Original media bytes never need to cross HTTP."""
from __future__ import annotations
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from .bundle import make_bundle, verify_bundle
from .lineage import compare_bytes, scan_bytes
from .core import append_event, evaluate, new_case, validate_case, InvalidCase

STATIC = Path(__file__).parent / "static"
MAX_BODY = 8_000_000


class Handler(BaseHTTPRequestHandler):
    server_version = "TraceProofLocal/0.9"

    def _headers(self, status, content_type, size):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()

    def _reply(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def _valid_origin(self):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return host in allowed and (origin is None or origin in {f"http://{x}" for x in allowed})

    def do_GET(self):
        if not self._valid_origin():
            return self._reply(403, {"error": "Localhost access only"})
        path = urlsplit(self.path).path
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/video": "video.html", "/video.js": "video.js"}
        if path not in files:
            return self._reply(404, {"error": "Not found"})
        blob = (STATIC / files[path]).read_bytes()
        mime = "text/html; charset=utf-8" if path == "/" else "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
        self._headers(200, mime, len(blob))
        self.wfile.write(blob)

    def do_POST(self):
        if not self._valid_origin():
            return self._reply(403, {"error": "Cross-origin requests denied"})
        if self.headers.get("Content-Type", "").split(";",1)[0].strip().lower() != "application/json":
            return self._reply(415, {"error": "JSON required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                return self._reply(413, {"error": "Request exceeds 8MB limit"})
            obj = json.loads(self.rfile.read(length))
            if not isinstance(obj, dict):
                raise InvalidCase("JSON object expected")
            path = urlsplit(self.path).path
            if path == "/api/new":
                result = new_case(obj.get("subject"))
            elif path == "/api/event":
                validate_case(obj.get("case"))
                result = append_event(obj["case"], obj.get("action"), obj.get("payload"))
            elif path == "/api/evaluate":
                result = evaluate(obj.get("case"))
            elif path == "/api/pack":
                raw = make_bundle(obj.get("case"))
                self._headers(200, "application/zip", len(raw))
                self.wfile.write(raw)
                return
            elif path == "/api/compare":
                def read_side(side):
                    item = obj.get(side)
                    if not isinstance(item, dict): raise ValueError("Two files required")
                    name = item.get("name", "")
                    if not isinstance(name, str) or not (1 <= len(name) <= 200): raise ValueError("Invalid filename")
                    data = base64.b64decode(item.get("base64", ""), validate=True)
                    if len(data) > 3_000_000: raise ValueError("File exceeds comparison UI limit (3 MB)")
                    return data, name
                a, an = read_side("left")
                b, bn = read_side("right")
                result = compare_bytes(a, an, b, bn)
            elif path == "/api/scan":
                items=obj.get("files")
                if not isinstance(items,list) or len(items)>40:raise ValueError("Select 1–40 files")
                decoded=[]
                for item in items:
                    if not isinstance(item,dict):raise ValueError("Invalid file")
                    name=item.get("name")
                    if not isinstance(name,str) or not 1<=len(name)<=200:raise ValueError("Invalid filename")
                    data=base64.b64decode(item.get("base64",""),validate=True)
                    if len(data)>1_000_000:raise ValueError("Each scan file must be at most 1 MB")
                    decoded.append((name,data))
                result=scan_bytes(decoded)
            elif path == "/api/video/compare":
                from .video import compare_videos
                import shutil
                if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
                    return self._reply(503, {"error": "FFmpeg and ffprobe must be installed locally"})
                samples = obj.get("samples", 8)
                if type(samples) is not int or not 1 <= samples <= 16:
                    raise ValueError("samples must be 1–16")
                def decode_video(key):
                    item = obj.get(key)
                    if not isinstance(item, dict):
                        raise ValueError("Two videos are required")
                    name = item.get("name", "")
                    if not isinstance(name, str) or not name.lower().endswith((".mp4",".mov",".webm",".mkv")):
                        raise ValueError("Unsupported video filename")
                    raw = base64.b64decode(item.get("base64", ""), validate=True)
                    if not 0 < len(raw) <= 2_500_000:
                        raise ValueError("Each video must be 2.5 MB or smaller for this local UI")
                    return raw
                left = decode_video("left")
                right = decode_video("right")
                with tempfile.TemporaryDirectory(prefix="traceproof-video-") as td:
                    a = Path(td) / "left.mp4"
                    b = Path(td) / "right.mp4"
                    a.write_bytes(left)
                    b.write_bytes(right)
                    result = compare_videos(a, b, samples=samples)
                    result["left"]["name"] = obj["left"]["name"]
                    result["right"]["name"] = obj["right"]["name"]
            elif path == "/api/verify":
                raw = base64.b64decode(obj.get("bundle_base64", ""), validate=True)
                result = verify_bundle(raw)
            else:
                return self._reply(404, {"error": "Unknown endpoint"})
            return self._reply(200, result)
        except (ValueError, TypeError, KeyError, InvalidCase, RuntimeError) as e:
            return self._reply(400, {"error": str(e)[:500]})


def serve(port=8765):
    if not 1024 <= port <= 65535:
        raise ValueError("Port must be between 1024 and 65535")
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"TraceProof offline UI: http://127.0.0.1:{port}/")
        server.serve_forever()