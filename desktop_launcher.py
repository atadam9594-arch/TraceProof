"""PyInstaller entry point for a Windows one-file desktop launcher."""
from traceproof.desktop import launch

if __name__ == "__main__":
    raise SystemExit(launch())