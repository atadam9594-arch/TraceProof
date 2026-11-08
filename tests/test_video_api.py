import base64
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from traceproof.server import Handler

class VideoApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def post(self, data):
        req = Request(f"http://127.0.0.1:{self.server.server_port}/api/video/compare",
                      data=json.dumps(data).encode(), headers={"Content-Type":"application/json"}, method="POST")
        try:
            with urlopen(req, timeout=5) as r:
                return r.status, json.load(r)
        except HTTPError as e:
            return e.code, json.load(e)

    def payload(self):
        item={"name":"sample.mp4","base64":base64.b64encode(b"fake-video").decode()}
        return {"left":item,"right":item,"samples":4}

    def test_video_page_is_served(self):
        with urlopen(f"http://127.0.0.1:{self.server.server_port}/video",timeout=5) as r:
            self.assertIn(b"Compare video evidence",r.read())

    def test_invalid_samples_rejected(self):
        with patch("shutil.which",return_value="/usr/bin/ffmpeg"):
            d=self.payload();d["samples"]=True
            status,_=self.post(d)
        self.assertEqual(status,400)

    def test_oversize_video_rejected(self):
        with patch("shutil.which",return_value="/usr/bin/ffmpeg"):
            d=self.payload()
            d["left"]["base64"]=base64.b64encode(b"x"*2_500_001).decode()
            status,_=self.post(d)
        self.assertEqual(status,400)

    def test_ffmpeg_missing(self):
        with patch("shutil.which",return_value=None):
            status,_=self.post(self.payload())
        self.assertEqual(status,503)

    def test_comparison_uses_temporary_files(self):
        def mock_compare(a,b,samples):
            self.assertEqual(a.read_bytes(),b"fake-video")
            self.assertEqual(b.read_bytes(),b"fake-video")
            self.assertEqual(samples,4)
            return {"left":{"name":"left.mp4"},"right":{"name":"right.mp4"},
                    "relation":"unresolved","matched_samples":[],"warning":"Not proof"}
        with patch("shutil.which",return_value="/usr/bin/ffmpeg"), patch("traceproof.video.compare_videos",side_effect=mock_compare):
            status,result=self.post(self.payload())
        self.assertEqual(status,200)
        self.assertEqual(result["left"]["name"],"sample.mp4")
        self.assertEqual(result["relation"],"unresolved")

if __name__=="__main__":
    unittest.main()
