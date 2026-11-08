import hashlib
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from traceproof.benchmark import MANIFEST_SCHEMA, _wilson, evaluate_manifest, load_manifest
from traceproof.benchmark_report import render_benchmark_report
from traceproof.server import Handler


class BenchmarkV12Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('a.mp4','b.mp4','c.mp4'):
            (self.root/name).write_bytes(name.encode())

    def manifest(self, pairs):
        path = self.root/'manifest.json'
        path.write_text(json.dumps({'schema':MANIFEST_SCHEMA,'pairs':pairs}),encoding='utf-8')
        return path

    def pair(self, ident, a, b, overlap, group='transcode'):
        return {'id':ident,'left':a,'right':b,'expected_overlap':overlap,'group':group}

    def fake_decode(self, log):
        def decode(path,samples):
            name=Path(path).name
            log.append(name)
            return {'sha256':hashlib.sha256(name.encode()).hexdigest(),'size':len(name),
                    'sampled_frames':[{'second':0,'dhash':'0000000000000000','informative':False}]}
        return decode

    def test_duplicate_files_decoded_once_with_default_cache(self):
        pairs=[self.pair('p1','a.mp4','b.mp4',False),
               self.pair('p2','a.mp4','c.mp4',False),
               self.pair('p3','a.mp4','b.mp4',False)]
        calls=[]
        report=evaluate_manifest(self.manifest(pairs),fingerprinter=self.fake_decode(calls))
        self.assertEqual(len(calls),3)
        self.assertEqual(report['summary']['unique_decodes'],3)
        self.assertEqual(report['summary']['fingerprint_cache_hits'],3)
        self.assertEqual(report['groups']['transcode']['true_negative'],3)
        self.assertEqual(report['groups']['transcode']['coverage'],1)

    def test_disable_cache_decodes_every_pair(self):
        pairs=[self.pair('p1','a.mp4','b.mp4',False),self.pair('p2','a.mp4','b.mp4',False)]
        calls=[]
        result=evaluate_manifest(self.manifest(pairs),fingerprinter=self.fake_decode(calls),cache=False)
        self.assertEqual(len(calls),4)
        self.assertEqual(result['summary']['unique_decodes'],4)
        self.assertEqual(result['summary']['fingerprint_cache_hits'],0)

    def test_decode_failures_are_cached_without_leaking_paths(self):
        pairs=[self.pair('p1','a.mp4','b.mp4',True),self.pair('p2','a.mp4','c.mp4',False)]
        calls=[]
        def fail(path,samples):
            calls.append(path)
            raise RuntimeError('secret path /home/a/video.mp4')
        result=evaluate_manifest(self.manifest(pairs),fingerprinter=fail)
        self.assertEqual(len(calls),1)
        self.assertEqual(result['summary']['errors'],2)
        self.assertNotIn('/home/a/',json.dumps(result))

    def test_group_metrics_and_intervals(self):
        manifest=self.manifest([self.pair('p1','a.mp4','b.mp4',True,'positive'),
                                self.pair('p2','b.mp4','c.mp4',False,'negative')])
        result=evaluate_manifest(manifest, comparator=lambda a,b,samples:{'relation':'unresolved'})
        self.assertEqual(result['groups']['positive']['false_negative'],1)
        self.assertEqual(result['groups']['negative']['true_negative'],1)
        self.assertIsNone(result['groups']['negative']['recall'])
        self.assertIsNone(result['groups']['positive']['false_positive_rate'])
        self.assertIsNone(result['groups']['negative']['confidence_intervals_95']['recall'])
        self.assertEqual(result['summary']['confidence_intervals_95']['coverage'][1],1.0)
        self.assertEqual(result['summary']['accuracy'],0.5)

    def test_tiny_samples_never_show_false_confidence(self):
        self.assertIsNone(_wilson(0,0))
        self.assertLess(_wilson(1,1)[0],0.25)
        self.assertGreater(_wilson(0,1)[1],0.75)

    def test_group_validation(self):
        for name in ('a/b','<script>','', ' '):
            with self.subTest(name=name):
                with self.assertRaises(ValueError): load_manifest(self.manifest([self.pair('p','a.mp4','b.mp4',True,name)]))

    def test_invalid_cache_boolean(self):
        with self.assertRaises(ValueError): evaluate_manifest(self.manifest([self.pair('p','a.mp4','b.mp4',True)]),cache=1)

    def test_html_escapes_malicious_strings_and_omits_original_paths(self):
        path=self.manifest([self.pair('p1','a.mp4','b.mp4',True)])
        result=evaluate_manifest(path,comparator=lambda *a,**kw:{'relation':'unresolved'})
        result['pairs'][0]['id']='<img src=x onerror=alert(1)>'
        result['groups']={'<script>alert(1)</script>':result['groups']['transcode']}
        html=render_benchmark_report(result)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertNotIn('<img src=x',html)
        self.assertNotIn(str(self.root),html)
        self.assertIn('Confidence',html)
        self.assertIn('95% Wilson',html)

    def test_report_rejects_wrong_schema(self):
        with self.assertRaises(ValueError):render_benchmark_report({'schema':'bogus'})

    def test_new_browser_lab_is_served_with_correct_mime(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            for route,ctype,marker in [('/benchmark','text/html','Benchmark Lab'),
                                       ('/benchmark.js','text/javascript','confidence_intervals_95'),
                                       ('/benchmark.css','text/css','bench-kpi')]:
                with urlopen(f'http://127.0.0.1:{server.server_port}{route}',timeout=3) as resp:
                    self.assertIn(ctype,resp.headers['Content-Type'])
                    self.assertIn(marker,resp.read().decode())
        finally:
            server.shutdown();server.server_close();worker.join(timeout=3)

if __name__=='__main__':unittest.main()