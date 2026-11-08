"""Offline FFmpeg/Pillow readiness checks and safe install guidance.

No network downloads, installers, shell invocations or absolute file paths are
included in the public diagnostic output. Paths are only used for direct,
argument-list process execution by the video module.
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

FFMPEG_DIR_ENV = "TRACEPROOF_FFMPEG_DIR"


def _config_path() -> Path:
    """Per-user, local-only CLI preferences; no package downloads occur."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "TraceProof" / "tools.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "traceproof" / "tools.json"


def _saved_binary_dir() -> Path | None:
    target = _config_path()
    try:
        if target.is_symlink() or not target.is_file() or target.stat().st_size > 4096:
            return None
        doc = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or set(doc) != {"schema", "directory"} or doc["schema"] != "traceproof.tools.v1":
            return None
        value = doc["directory"]
        if not isinstance(value, str) or not 0 < len(value) <= 1024:
            return None
        folder = Path(value)
        return folder if folder.is_absolute() and folder.is_dir() else None
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return None


def _binary_pair(directory: Path) -> tuple[Path, Path]:
    names = ("ffmpeg", "ffprobe")
    ext = ".exe" if os.name == "nt" else ""
    return (directory / (names[0]+ext),directory / (names[1]+ext))


def register_ffmpeg_directory(directory: str | Path) -> dict:
    """Register trusted, user-supplied tools. Never downloads or installs binaries.

    This *executes* -version on both files: only point to executables you trust.
    """
    folder = Path(directory).expanduser().resolve(strict=True)
    if not folder.is_dir() or len(str(folder)) > 1024:
        raise ValueError("Expected an existing directory of trusted executables")
    ffmpeg, ffprobe = _binary_pair(folder)
    for executable in (ffmpeg, ffprobe):
        if not executable.is_file() or executable.is_symlink():
            raise ValueError("Directory must include ffmpeg and ffprobe executables")
        if os.name != "nt" and not os.access(executable,os.X_OK):
            raise ValueError("FFmpeg and ffprobe must be executable")
    for executable,name in ((ffmpeg,"ffmpeg"),(ffprobe,"ffprobe")):
        ready,version = _version(str(executable))
        if not ready or not version or not version.lower().startswith(name+" version"):
            raise ValueError(f"{name} did not return a recognized version header")
    target = _config_path()
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_symlink():
        raise ValueError("Refusing to replace symlinked FFmpeg configuration")
    content = json.dumps({"schema":"traceproof.tools.v1","directory":str(folder)},ensure_ascii=False) + "\n"
    # Atomically write a private file (600 on POSIX). Configuration itself is
    # local and does not contain credentials or media, only a user-selected path.
    fd,path = tempfile.mkstemp(prefix=".tools-",dir=str(target.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as output:
            output.write(content)
        if os.name != "nt":
            os.chmod(path,0o600)
        os.replace(path,target)
    finally:
        if os.path.exists(path):
            os.unlink(path)
    return {"registered": True, "ffmpeg_ready": True, "ffprobe_ready": True,
            "warning": "Only register binaries downloaded from a source you independently trust"}


def clear_ffmpeg_directory() -> dict:
    target = _config_path()
    if target.is_symlink():
        raise ValueError("Refusing to follow symlinked tool configuration")
    target.unlink(missing_ok=True)
    return {"registered": False}



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
    saved = _saved_binary_dir()
    if saved:
        candidate = saved / (name + (".exe" if os.name == "nt" else ""))
        if candidate.is_file() and not candidate.is_symlink() and (os.name == "nt" or os.access(candidate, os.X_OK)):
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
                "Register a trusted folder with: TraceProof.exe ffmpeg-register --dir C:\\ffmpeg\\bin (Windows preview) or traceproof ffmpeg-register --dir PATH (Python). Restart TraceProof, then recheck."]
    if system == "Darwin":
        return ["Install FFmpeg using your trusted package manager (for Homebrew: brew install ffmpeg).",
                "Restart TraceProof, then run: traceproof doctor"]
    if system == "Linux":
        return ["Install FFmpeg using your distribution's trusted package manager (Debian/Ubuntu: sudo apt install ffmpeg).",
                "Restart TraceProof, then run: traceproof doctor"]
    return ["See https://ffmpeg.org/download.html for platform-specific instructions.",
            "Ensure ffmpeg and ffprobe are both on PATH and run: traceproof doctor"]