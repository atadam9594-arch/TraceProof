import tempfile
import unittest
from pathlib import Path
from traceproof.lineage import compare, scan

class LineageTests(unittest.TestCase):
    def test_exact(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.txt',Path(d)/'b.txt'
            a.write_text('Hello World');b.write_text('Hello World')
            self.assertEqual(compare(a,b)['relation'],'byte_identical')
            self.assertEqual(len(scan(d)['edges']),1)
    def test_normalized(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.txt',Path(d)/'b.txt'
            a.write_text('Hello, WORLD!');b.write_text('hello world')
            self.assertEqual(compare(a,b)['relation'],'text_normalization_match')
    def test_no_false_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.txt',Path(d)/'b.txt'
            a.write_text('Completely different');b.write_text('Nothing alike')
            self.assertEqual(compare(a,b)['direction'],'unknown')
    def test_binary_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.png',Path(d)/'b.png'
            a.write_bytes(b'\x89PNGaaa');b.write_bytes(b'\x89PNGbbb')
            self.assertEqual(compare(a,b)['relation'],'unresolved')
    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.txt',Path(d)/'b.txt'
            a.write_text('a');b.symlink_to(a)
            with self.assertRaises(ValueError):compare(a,b)
    def test_limit(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.txt',Path(d)/'b.txt'
            a.write_bytes(b'x'*20_000_001);b.write_bytes(b'x')
            with self.assertRaises(ValueError):compare(a,b)
if __name__=='__main__':unittest.main()