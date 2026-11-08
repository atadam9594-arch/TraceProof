"""Offline FFmpeg/Pillow readiness checks and safe install guidance.

No network downloads, installers, shell invocations or absolute file paths are
included in the public diagnostic output. Paths are only used for direct,
argument-list process execution by the video module.
"""
from __future__ import annotations
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

FFMPEG_DIR_ENV = "TRACEPROOF_FFMPEG_DIR"


def find_binary(name: str) -> str | None:
    if name not in ("ffmpeg", "ffprobe"):
        raise ValueError("Unsupported binary name")
    custom = os.environ.get(FFMPEG_DIR_ENV)
    if custom:
        directory = Path(custom)
        candidate = directory / (name + (".exe" if os.name == "nt" else ""))
        # Ignore a nonexistent override and continue with the normal PATH.
        if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
            return str(candidate)
    return shutil.which(name)


def _version(executable: str | None) -> tuple[bool, str | None]:
    if not executable:
        return False, None
    try:
        result = subprocess.run([executable, "-version"], shell=False,
                                capture_output=True, text=True, timeout=4,
                                errors="replace", check=False)
        if result.returncode != 0:
            return False, None
        line = result.stdout.splitlines()[0] if result.stdout else ""
        # Do not echo control characters or arbitrarily long program output.
        clean = "".join(c for c in line[:180] if 32 <= ord(c) <= 126)
        return bool(clean), clean or None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False, None


def diagnose() -> dict:
    tools = {}
    for name in ("ffmpeg", "ffprobe"):
        detected, version = _version(find_binary(name))
        tools[name] = {"ready": detected, "version": version}
    try:
        import PIL
        from PIL import Image  # noqa: F401
        pillow = {"ready": True, "version": str(PIL.__version__)[:50]}
    except (ImportError, AttributeError):
        pillow = {"ready": False, "version": None}
    tools["pillow"] = pillow
    ready = all(x["ready"] for x in tools.values())
    system = platform.system()
    return {
        "schema": "traceproof.diagnostics.v1",
        "platform": system if system in ("Windows", "Darwin", "Linux") else "Other",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "ready": ready,
        "components": tools,
        "external_installation_required": not ready,
        "limitations": [
            "FFmpeg/ffprobe executables are not bundled with TraceProof desktop previews",
            "Readiness does not guarantee decoding support for every codec",
            "TraceProof never downloads or executes installers automatically",
        ],
    }


def guidance(system: str | None = None) -> list[str]:
    system = system or platform.system()
    if system == "Windows":
        return ["Use winget search ffmpeg to see available packages.",
                "Choose a trusted FFmpeg package or visit https://ffmpeg.org/download.html.",
                "Add its bin directory to PATH, or set TRACEPROOF_FFMPEG_DIR to the folder containing ffmpeg.exe and ffprobe.exe.",
                "Restart TraceProof and run: traceproof doctor"]
    if system == "Darwin":
        return ["Install FFmpeg using your trusted package manager (for Homebrew: brew install ffmpeg).",
                "Restart TraceProof, then run: traceproof doctor"]
    if system == "Linux":
        return ["Install FFmpeg using your distribution's trusted package manager (Debian/Ubuntu: sudo apt install ffmpeg).",
                "Restart TraceProof, then run: traceproof doctor"]
    return ["See https://ffmpeg.org/download.html for platform-specific instructions.",
            "Ensure ffmpeg and ffprobe are both on PATH and run: traceproof doctor"]