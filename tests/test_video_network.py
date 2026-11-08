import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from traceproof.video_network import (scan_video_network, render_network_report,
                                      validate_network_report, MAX_VIDEOS)


def fake_fp(path, samples):
    p = Path(path)
    data = p.read_bytes()
    if data == b'broken':
        raise ValueError('Private decoder failure: /secret/path')
    digest = hashlib.sha256(data).hexdigest()
    # a and b differ byte-wise but intentionally have the same two distinct
    # informative fingerprints; c is a negative control.
    hashes = (('1010101010101010', 'efefefefefefefef') if data in (b'a', b'b')
              else ('aaaaaaaaaaaaaaaa', '5555555555555555'))
    return {'schema':'traceproof.video.v2', 'sha256':digest, 'size':p.stat().st_size,
            'name':p.name, 'duration_seconds':2.0,
            'sampled_frames':[{'second':1.0,'dhash':hashes[0],'informative':True},
                              {'second':2.0,'dhash':hashes[1],'informative':True}]}


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, value):
        (self.root / name).write_bytes(value)

    def test_exact_similarity_unresolved_and_components(self):
        for name, data in [('01.mp4',b'a'),('02.mp4',b'a'),
                           ('03.webm',b'b'),('04.mov',b'c')]:
            self.write(name,data)
        report = scan_video_network(self.root,samples=2,fingerprinter=fake_fp)
        s=report['summary']
        self.assertEqual(s['videos'],4)
        self.assertEqual(s['pair_comparisons'],6)
        self.assertEqual(s['byte_identical_edges'],1)
        self.assertEqual(s['similarity_edges'],2)
        self.assertEqual(s['unresolved_pairs'],3)
        self.assertEqual(s['connected_groups'],2)
        self.assertEqual(report['groups'],[['v001','v002','v003'],['v004']])
        self.assertEqual([e['relation'] for e in report['edges']],
            ['byte_identical','video_similarity_candidate','video_similarity_candidate'])
        self.assertNotIn(str(self.root),json.dumps(report))

    def test_bad_video_is_explicit_error_no_path_leak(self):
        self.write('a.mp4',b'broken');self.write('b.mp4',b'a')
        out=scan_video_network(self.root,fingerprinter=fake_fp)
        self.assertEqual(out['summary']['decode_errors'],1)
        self.assertEqual(out['summary']['pair_comparisons'],0)
        self.assertEqual(out['nodes'][0]['error_type'],'video_analysis_failed')
        self.assertNotIn('secret',json.dumps(out))

    def test_reject_symlink_directory(self):
        self.write('a.mp4',b'a')
        alias=self.root.parent/('traceproof-temp-link-'+self.root.name)
        try:
            alias.symlink_to(self.root,target_is_directory=True)
        except (OSError,NotImplementedError):
            self.skipTest('Symlinks unavailable')
        self.addCleanup(alias.unlink)
        with self.assertRaises(ValueError):scan_video_network(alias,fingerprinter=fake_fp)

    def test_skip_symlink_file(self):
        self.write('a.mp4',b'a');self.write('b.mp4',b'b')
        try:(self.root/'c.mp4').symlink_to(self.root/'a.mp4')
        except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable')
        self.assertEqual(scan_video_network(self.root,fingerprinter=fake_fp)['summary']['videos'],2)

    def test_reject_more_than_limit(self):
        for i in range(MAX_VIDEOS+1):self.write(f'{i:03d}.mp4',b'a')
        with self.assertRaisesRegex(ValueError,'maximum permitted'):
            scan_video_network(self.root,fingerprinter=fake_fp)

    def test_reject_invalid_samples_or_limits(self):
        self.write('a.mp4',b'a');self.write('b.mp4',b'b')
        for samples in (1,17,True,'8'):
            with self.subTest(samples=samples),self.assertRaises(ValueError):
                scan_video_network(self.root,samples=samples,fingerprinter=fake_fp)
        for count in (1,13,True):
            with self.subTest(count=count),self.assertRaises(ValueError):
                scan_video_network(self.root,max_videos=count,fingerprinter=fake_fp)

    def test_empty_and_one_video(self):
        with self.assertRaises(ValueError):scan_video_network(self.root,fingerprinter=fake_fp)
        self.write('a.mp4',b'a')
        with self.assertRaisesRegex(ValueError,'at least two'):
            scan_video_network(self.root,fingerprinter=fake_fp)

    def test_report_html_escapes_untrusted_filenames(self):
        self.write('a.mp4',b'a');self.write('b.mp4',b'b')
        report=scan_video_network(self.root,fingerprinter=fake_fp)
        report['nodes'][0]['name']='<script>alert(1)</script>.mp4'
        html=render_network_report(report)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertNotIn(str(self.root),html)
        self.assertNotIn('javascript:',html)

    def test_reject_invalid_report_edges(self):
        self.write('a.mp4',b'a');self.write('b.mp4',b'b')
        r=scan_video_network(self.root,fingerprinter=fake_fp)
        r['edges'].append({'source':'v001','target':'bad','relation':'byte_identical'})
        with self.assertRaises(ValueError):validate_network_report(r)

    def test_local_viewer_routes(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        from traceproof.server import Handler
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            for suffix,typ in (("/network","text/html"),("/network.js","text/javascript"),
                               ("/network.css","text/css")):
                with urlopen(f"http://127.0.0.1:{server.server_port}{suffix}",timeout=5) as response:
                    self.assertEqual(response.status,200)
                    self.assertIn(typ,response.headers.get("Content-Type",""))
                    self.assertGreater(len(response.read()),100)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

    def test_report_without_links_and_no_scripts(self):
        self.write('a.mp4',b'a');self.write('c.mp4',b'c')
        r=scan_video_network(self.root,fingerprinter=fake_fp)
        html=render_network_report(r)
        self.assertIn('No candidate links',html)
        self.assertNotIn('<script',html)

    def test_cli_saves_graph_and_html(self):
        self.write('a.mp4',b'a');self.write('b.mp4',b'b')
        from traceproof.cli import main
        out=self.root/'network.json';html=self.root/'network.html'
        with patch('traceproof.video_network.fingerprint_video',side_effect=fake_fp):
            self.assertEqual(main(['video-network',str(self.root),'--samples','2','--out',str(out),'--html',str(html)]),0)
        self.assertEqual(json.loads(out.read_text())['schema'],'traceproof.video.network.v1')
        self.assertIn('<svg',html.read_text())


if __name__ == '__main__': unittest.main()