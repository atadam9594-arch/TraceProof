"""Bounded, private temporary video uploads for the loopback-only video lab.

Browser files travel only to the local HTTP server. No public upload service,
subprocess shell interpolation, arbitrary filesystem access, or persistent media.
"""
from __future__ import annotations

import atexit
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
from .video import compare_videos

MAX_VIDEO_BYTES = 250_000_000
MAX_CHUNK = 1024 * 1024
SESSION_TTL_SECONDS = 30 * 60
ALLOWED_EXTENSIONS = (".mp4", ".mov", ".mkv", ".webm")


def _valid_name(value):
    return (isinstance(value, str) and 1 <= len(value) <= 200
            and value.lower().endswith(ALLOWED_EXTENSIONS)
            and not any(ord(c) < 32 for c in value))


class UploadError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class VideoUploadManager:
    """Maximum one active staging session, bounded by two files x 250 MB.

    Guard all updates under a lock. Worker threads don't retain request handlers.
    Completed media is deleted even when analysis raises; the JSON result remains
    briefly accessible via the random, unguessable session token.
    """
    def __init__(self, *, clock=time.monotonic, compare=compare_videos):
        self.clock = clock
        self.compare = compare
        self.lock = threading.RLock()
        self.session = None
        atexit.register(self.close)

    def _cleanup(self, session):
        folder = session.get("folder")
        if folder is not None:
            session["folder"] = None
            folder.cleanup()

    def _expire(self):
        s = self.session
        if s is not None and self.clock() - s["last_seen"] > SESSION_TTL_SECONDS:
            if s["state"] == "analyzing":
                s["cancelled"] = True
            else:
                self._cleanup(s)
                self.session = None

    def _get(self, token, *, touch=True):
        self._expire()
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{48}", token):
            raise UploadError("Unknown or expired session", 404)
        s = self.session
        if s is None or not secrets.compare_digest(s["token"], token):
            raise UploadError("Unknown or expired session", 404)
        if touch:
            s["last_seen"] = self.clock()
        return s

    def create(self, metadata):
        if not isinstance(metadata, dict):
            raise UploadError("Invalid upload request")
        samples = metadata.get("samples", 12)
        if type(samples) is not int or not 1 <= samples <= 16:
            raise UploadError("Samples must be between 1 and 16")
        specs = {}
        for side in ("left", "right"):
            item = metadata.get(side)
            if not isinstance(item, dict):
                raise UploadError("Provide two video files")
            name, size = item.get("name"), item.get("size")
            if not _valid_name(name) or type(size) is not int or not 0 < size <= MAX_VIDEO_BYTES:
                raise UploadError("Video file must be MP4/MOV/MKV/WebM and at most 250 MB")
            specs[side] = {"name": name, "size": size, "offset": 0}
        with self.lock:
            self._expire()
            if self.session and self.session["state"] in ("uploading", "analyzing"):
                raise UploadError("Finish or cancel the current video comparison", 409)
            if self.session:
                self._cleanup(self.session)
            folder = tempfile.TemporaryDirectory(prefix="traceproof-upload-")
            session = {"token": secrets.token_hex(24), "last_seen": self.clock(),
                       "state": "uploading", "cancelled": False, "folder": folder,
                       "specs": specs, "samples": samples, "result": None, "error": None}
            self.session = session
            return {"session": session["token"], "chunk_bytes": MAX_CHUNK,
                    "max_video_bytes": MAX_VIDEO_BYTES, "status": "uploading"}

    def chunk(self, token, side, offset, data):
        with self.lock:
            s = self._get(token)
            if s["state"] != "uploading":
                raise UploadError("Upload is not active", 409)
            if side not in ("left", "right"):
                raise UploadError("Invalid video side")
            if type(offset) is not int or offset < 0:
                raise UploadError("Invalid chunk offset")
            if not isinstance(data, bytes) or not 0 < len(data) <= MAX_CHUNK:
                raise UploadError("Chunk must contain 1 to 1,048,576 bytes")
            spec = s["specs"][side]
            if offset != spec["offset"]:
                raise UploadError("Chunk offset mismatch", 409)
            if offset + len(data) > spec["size"]:
                raise UploadError("Chunk would exceed declared video size")
            target = Path(s["folder"].name) / (side + ".video")
            with target.open("ab") as out:
                out.write(data)
            spec["offset"] += len(data)
            return {"side": side, "received": spec["offset"], "total": spec["size"]}

    def begin(self, token):
        with self.lock:
            s = self._get(token)
            if s["state"] != "uploading":
                raise UploadError("Comparison already started", 409)
            if any(item["offset"] != item["size"] for item in s["specs"].values()):
                raise UploadError("Both video uploads must be complete", 409)
            s["state"] = "analyzing"
            thread = threading.Thread(target=self._worker, args=(s,), daemon=True)
            thread.start()
            return {"status": "analyzing"}

    def _worker(self, s):
        try:
            path = Path(s["folder"].name)
            result = self.compare(path / "left.video", path / "right.video", samples=s["samples"])
            result["left"]["name"] = s["specs"]["left"]["name"]
            result["right"]["name"] = s["specs"]["right"]["name"]
            with self.lock:
                if not s["cancelled"]:
                    s["result"] = result
                    s["state"] = "done"
        except Exception as exc:
            with self.lock:
                if not s["cancelled"]:
                    s["state"] = "failed"
                    # Never expose temporary local paths or subprocess error output.
                    s["error"] = "Video decoding failed or required tools are unavailable"
        finally:
            with self.lock:
                self._cleanup(s)
                if s["cancelled"]:
                    s["state"] = "cancelled"

    def status(self, token):
        with self.lock:
            s = self._get(token)
            answer = {"status": s["state"], "files": {
                key: {"received": val["offset"], "total": val["size"]}
                for key, val in s["specs"].items()}}
            if s["state"] == "done":
                answer["result"] = s["result"]
            if s["state"] == "failed":
                answer["error"] = s["error"]
            return answer

    def cancel(self, token):
        with self.lock:
            s = self._get(token)
            s["cancelled"] = True
            if s["state"] != "analyzing":
                self._cleanup(s)
                s["state"] = "cancelled"
            return {"status": "cancelled"}

    def close(self):
        with self.lock:
            if self.session:
                self.session["cancelled"] = True
                if self.session["state"] != "analyzing":
                    self._cleanup(self.session)
                    self.session = None


_manager_lock = threading.Lock()

def manager_for(server):
    """One upload manager per local server; never shared across tests/instances."""
    with _manager_lock:
        mgr = getattr(server, "traceproof_video_uploads", None)
        if mgr is None:
            mgr = VideoUploadManager()
            server.traceproof_video_uploads = mgr
        return mgr