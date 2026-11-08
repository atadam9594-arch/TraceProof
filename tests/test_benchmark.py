import json
import tempfile
import unittest
from pathlib import Path
from traceproof.benchmark import MANIFEST_SCHEMA, load_manifest, evaluate_manifest


class VideoBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['same.mp4','other.mp4','unrelated.mp4']:
            (self.root / name).write_bytes(name.encode())

    def manifest(self, pairs):
        path = self.root / 'dataset.json'
        path.write_text(json.dumps({'schema': MANIFEST_SCHEMA, 'pairs': pairs}))
        return path

    def pair(self, name, a, b, label):
        return {'id':name,'left':a,'right':b,'expected_overlap':label}

    def test_confusion_matrix_and_denominators(self):
        pairs=[self.pair('tp','same.mp4','other.mp4',True),
               self.pair('fn','other.mp4','unrelated.mp4',True),
               self.pair('fp','same.mp4','unrelated.mp4',False),
               self.pair('tn','unrelated.mp4','other.mp4',False)]
        answers={'tp':'video_similarity_candidate','fn':'unresolved','fp':'video_similarity_candidate','tn':'unresolved'}
        call=[0]
        def compare(*args, **kwargs):
            i=call[0];call[0]+=1
            return {'relation': answers[pairs[i]['id']]}
        result=evaluate_manifest(self.manifest(pairs),comparator=compare)
        s=result['summary']
        self.assertEqual((s['true_positive'],s['false_positive'],s['true_negative'],s['false_negative']),(1,1,1,1))
        self.assertEqual(s['precision'],.5)
        self.assertEqual(s['recall'],.5)
        self.assertEqual(s['false_positive_rate'],.5)
        self.assertEqual(s['coverage'],1)
        self.assertEqual([x['status'] for x in result['pairs']],['evaluated']*4)

    def test_unknown_denominator_remains_null(self):
        path=self.manifest([self.pair('neg','same.mp4','other.mp4',False)])
        result=evaluate_manifest(path,comparator=lambda *a,**k:{'relation':'unresolved'})
        self.assertIsNone(result['summary']['precision'])
        self.assertIsNone(result['summary']['recall'])
        self.assertEqual(result['summary']['specificity'],1)

    def test_decoding_errors_count_against_coverage(self):
        p=self.manifest([self.pair('one','same.mp4','other.mp4',True),
                         self.pair('two','other.mp4','unrelated.mp4',False)])
        count=[0]
        def compare(*a,**kw):
            count[0]+=1
            if count[0]==2: raise RuntimeError('/private/secret/path')
            return {'relation':'byte_identical'}
        result=evaluate_manifest(p,comparator=compare)
        self.assertEqual(result['summary']['coverage'],.5)
        self.assertEqual(result['summary']['errors'],1)
        self.assertNotIn('/private',json.dumps(result))

    def test_reject_duplicate_ids(self):
        p=self.pair('x','same.mp4','other.mp4',True)
        with self.assertRaises(ValueError):load_manifest(self.manifest([p,p]))

    def test_reject_nonboolean_ground_truth(self):
        with self.assertRaises(ValueError):load_manifest(self.manifest([self.pair('x','same.mp4','other.mp4',1)]))

    def test_reject_traversal_and_absolute_paths(self):
        for name in ('../secret.mp4','/etc/passwd.mp4','folder/../same.mp4','C:\\secret.mp4'):
            with self.subTest(name=name):
                p=self.manifest([self.pair('x',name,'other.mp4',True)])
                r=evaluate_manifest(p,comparator=lambda *a,**k:{'relation':'byte_identical'})
                self.assertEqual(r['summary']['errors'],1)
                self.assertEqual(r['summary']['coverage'],0)

    def test_unknown_model_relation_not_silent_negative(self):
        p=self.manifest([self.pair('x','same.mp4','other.mp4',False)])
        r=evaluate_manifest(p,comparator=lambda *a,**k:{'relation':'magic_yes'})
        self.assertEqual(r['summary']['errors'],1)
        self.assertEqual(r['summary']['evaluated'],0)

    def test_reject_samples_bool(self):
        p=self.manifest([self.pair('x','same.mp4','other.mp4',True)])
        with self.assertRaises(ValueError):evaluate_manifest(p,samples=True)

    def test_reject_symlink(self):
        link=self.root/'link.mp4'
        try: link.symlink_to(self.root/'same.mp4')
        except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable')
        p=self.manifest([self.pair('x','link.mp4','other.mp4',True)])
        r=evaluate_manifest(p,comparator=lambda *a,**k:{'relation':'byte_identical'})
        self.assertEqual(r['summary']['errors'],1)

    def test_manifest_with_no_pairs(self):
        with self.assertRaises(ValueError):load_manifest(self.manifest([]))

if __name__=='__main__':unittest.main()