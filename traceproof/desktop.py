"""Open the local-only TraceProof workspace without needing a terminal command.

The server binds to 127.0.0.1 on an OS-assigned port (avoids port conflicts).
The process stays open until the console is closed or interrupted.
"""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import threading
import webbrowser

from .server import Handler


def launch(browser_open=webbrowser.open, server_class=ThreadingHTTPServer):
    """Start a localhost server and open the user's default browser.

    No remote service, account or outbound HTTP request is involved here.
    """
    with server_class(("127.0.0.1", 0), Handler) as server:
        server.daemon_threads = True
        url = f"http://127.0.0.1:{server.server_port}/"
        print("TraceProof — local workspace", flush=True)
        print("Open:", url, flush=True)
        print("Close this window to stop the local application.", flush=True)
        threading.Timer(0.4, browser_open, args=(url,)).start()
        try:
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch())