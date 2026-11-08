"""PyInstaller entry point: browser workspace or explicit offline CLI command."""
from __future__ import annotations
import sys
from traceproof.desktop import launch
from traceproof.cli import main

if __name__ == "__main__":
    # Launching by double-click retains normal behavior. Explicit CLI commands
    # make a Windows .exe usable without a separate Python installation.
    raise SystemExit(main(sys.argv[1:]) if len(sys.argv) > 1 else launch())