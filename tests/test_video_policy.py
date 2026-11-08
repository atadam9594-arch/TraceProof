import unittest
from traceproof.video import compare_video_fingerprints, match_fingerprints
from traceproof.report import render_video_report


def record(values, *, informative=True, sha='X', name='clip.mp4'):
    return {'schema':'traceproof.video.v2', 'sha256':sha,'size':120,
            'name':name,'duration_seconds':12.0,
            'sampled_frames':[{'second':float(i), 'dhash':f'{n:016x}',
                               'informative':informative} for i,n in enumerate(values)]}


class VideoPolicyTests(unittest.TestCase):
    def test_identical_bytes_even_when_frames_flat(self):
        a=record([0,0],informative=False)
        b=record([0,0],informative=False)
        self.assertEqual(compare_video_fingerprints(a,b)['relation'],'byte_identical')

    def test_black_frames_do_not_produce_similarity_candidate(self):
        a=record([0,0,0],informative=False,sha='A')
        b=record([0,0,0],informative=False,sha='B')
        self.assertEqual(compare_video_fingerprints(a,b)['relation'],'unresolved')
        self.assertEqual(match_fingerprints(a,b),[])

    def test_one_repeated_frame_is_not_sufficient(self):
        a=record([0xf0f0f0f0f0f0f0f0]*3,sha='A')
        b=record([0xf0f0f0f0f0f0f0f0]*3,sha='B')
        self.assertEqual(compare_video_fingerprints(a,b)['relation'],'unresolved')

    def test_two_visually_distinct_informative_matches(self):
        a=record([0xf0f0f0f0f0f0f0f0,0x0f0f0f0f0f0f0f0f],sha='A')
        b=record([0xf0f0f0f0f0f0f0f0,0x0f0f0f0f0f0f0f0f],sha='B')
        self.assertEqual(compare_video_fingerprints(a,b)['relation'],'video_similarity_candidate')

    def test_one_to_one_ordered_matches(self):
        a=record([0xffffffffffffffff,0x0],sha='A')
        b=record([0x0,0xffffffffffffffff],sha='B')
        matches=match_fingerprints(a,b)
        self.assertEqual(len(matches),1)

    def test_reject_bool_threshold(self):
        with self.assertRaises(ValueError):match_fingerprints(record([1]),record([1]),True)

    def test_report_escapes_malicious_filename(self):
        a=record([0,15],sha='A',name='<img src=x onerror=alert(1)>.mp4')
        b=record([0,15],sha='B')
        report=render_video_report(compare_video_fingerprints(a,b))
        self.assertNotIn('<img',report)
        self.assertIn('&lt;img',report)
        self.assertIn('not a cryptographically signed ProofBundle',report)

    def test_report_rejects_wrong_schema(self):
        with self.assertRaises(ValueError):render_video_report({'schema':'evil'})

if __name__=='__main__':unittest.main()