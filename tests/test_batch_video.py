import unittest
from unittest.mock import patch
from traceproof.lineage import scan_bytes
from traceproof.video import fingerprint_video,compare_videos

class BatchVideoTests(unittest.TestCase):
    def test_scan_identical(self):
        r=scan_bytes([('a.txt',b'Hello!'),('b.txt',b'Hello!')]);self.assertEqual(r['edges'][0]['relation'],'byte_identical')
    def test_scan_normalized(self):
        r=scan_bytes([('a.txt',b'Hello, WORLD'),('b.txt',b'hello world')]);self.assertEqual(r['edges'][0]['relation'],'text_normalization_match')
    def test_scan_no_match(self):
        self.assertEqual(scan_bytes([('a.txt',b'hello'),('b.txt',b'goodbye')])['edges'],[])
    def test_scan_does_not_export_text(self):
        self.assertNotIn('_text',scan_bytes([('a.txt',b'hello')])['files'][0])
    def test_video_bad_file(self):
        with self.assertRaises(ValueError):fingerprint_video('/nonexistent.mp4')
    def test_video_invalid_samples(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp4') as f:
            with self.assertRaises(ValueError):fingerprint_video(f.name,0)