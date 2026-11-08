"""Local-only HTTP UI with bounded, temporary disk-backed video transfers."""
from __future__ import annotations
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from .bundle import make_bundle, verify_bundle
from .lineage import compare_bytes, scan_bytes
from .core import append_event, evaluate, new_case, validate_case, InvalidCase
from .uploads import manager_for, UploadError, MAX_CHUNK

STATIC = Path(__file__).parent / "static"
MAX_BODY = 8_000_000


class Handler(BaseHTTPRequestHandler):
    server_version = "TraceProofLocal/0.11"

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
        if path == "/api/video/capabilities":
            try:
                import PIL
                pillow = True
            except ImportError:
                pillow = False
            ffmpeg = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
            return self._reply(200, {"video_analysis_available": ffmpeg and pillow,
                                     "ffmpeg_available": ffmpeg, "pillow_available": pillow,
                                     "max_file_bytes": 250_000_000,
                                     "chunk_bytes": MAX_CHUNK, "max_samples": 16})
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/video": "video.html", "/video.js": "video.js", "/video.css": "video.css"}
        if path not in files:
            return self._reply(404, {"error": "Not found"})
        blob = (STATIC / files[path]).read_bytes()
        mime = "text/html; charset=utf-8" if path == "/" else "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
        self._headers(200, mime, len(blob))
        self.wfile.write(blob)

    def _upload_chunk(self):
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/octet-stream":
            return self._reply(415, {"error": "Binary chunk required"})
        try:
            count = int(self.headers.get("Content-Length", "0"))
            if not 0 < count <= MAX_CHUNK:
                return self._reply(413, {"error": "Chunk exceeds 1 MiB"})
            token = self.headers.get("X-TraceProof-Session", "")
            side = self.headers.get("X-TraceProof-Side", "")
            offset = int(self.headers.get("X-TraceProof-Offset", "-1"))
            # Validate session and position before consuming the request body.
            mgr = manager_for(self.server)
            data = self.rfile.read(count)
            if len(data) != count:
                raise UploadError("Incomplete chunk")
            return self._reply(200, mgr.chunk(token, side, offset, data))
        except UploadError as exc:
            return self._reply(exc.status, {"error": str(exc)[:500]})
        except (TypeError, ValueError):
            return self._reply(400, {"error": "Invalid chunk headers"})

    def do_POST(self):
        if not self._valid_origin():
            return self._reply(403, {"error": "Cross-origin requests denied"})
        path = urlsplit(self.path).path
        if path == "/api/video/chunk":
            return self._upload_chunk()
        if self.headers.get("Content-Type", "").split(";",1)[0].strip().lower() != "application/json":
            return self._reply(415, {"error": "JSON required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                return self._reply(413, {"error": "Request exceeds 8MB limit"})
            obj = json.loads(self.rfile.read(length))
            if not isinstance(obj, dict):
                raise InvalidCase("JSON object expected")
            if path == "/api/video/session":
                result = manager_for(self.server).create(obj)
            elif path == "/api/video/start":
                result = manager_for(self.server).begin(obj.get("session"))
            elif path == "/api/video/status":
                result = manager_for(self.server).status(obj.get("session"))
            elif path == "/api/video/cancel":
                result = manager_for(self.server).cancel(obj.get("session"))
            elif path == "/api/new":
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
                import tempfile
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
                    if not isinstance(name, str) or not name.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                        raise ValueError("Unsupported video filename")
                    raw = base64.b64decode(item.get("base64", ""), validate=True)
                    if not 0 < len(raw) <= 2_500_000:
                        raise ValueError("Each video must be 2.5 MB or smaller for legacy API")
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
        except UploadError as e:
            return self._reply(e.status, {"error": str(e)[:500]})
        except (ValueError, TypeError, KeyError, InvalidCase, RuntimeError) as e:
            return self._reply(400, {"error": str(e)[:500]})


def serve(port=8765):
    if not 1024 <= port <= 65535:
        raise ValueError("Port must be between 1024 and 65535")
    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"TraceProof offline UI: http://127.0.0.1:{port}/")
        server.serve_forever()