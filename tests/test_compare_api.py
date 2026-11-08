import base64
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from traceproof.server import Handler
from traceproof.lineage import compare_bytes

class CompareTests(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(compare_bytes(b"same", "a.txt", b"same", "b.txt")["relation"], "byte_identical")
    def test_normalized(self):
        self.assertEqual(compare_bytes(b"Hello, World!", "a.txt", b"hello world", "b.txt")["relation"], "text_normalization_match")
    def test_different(self):
        self.assertEqual(compare_bytes(b"hello", "a.txt", b"goodbye", "b.txt")["relation"], "unresolved")
    def test_http(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            port=server.server_port
            data={k:{"name":k+".txt","base64":base64.b64encode(b"hello").decode()} for k in ("left","right")}
            req=Request(f"http://127.0.0.1:{port}/api/compare",data=json.dumps(data).encode(),headers={"Content-Type":"application/json"},method="POST")
            with urlopen(req,timeout=3) as resp:result=json.load(resp)
            self.assertEqual(result["relation"],"byte_identical")
        finally:server.shutdown();server.server_close();thread.join(timeout=3)