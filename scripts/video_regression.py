"""Reproducible smoke scenarios for video matching; not an accuracy benchmark.

Requirements: installed ffmpeg, ffprobe and Pillow; run at repository root:
    python scripts/video_regression.py
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traceproof.video import compare_videos


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', *args],
                   check=True, timeout=45)


def main():
    with tempfile.TemporaryDirectory(prefix='traceproof-smoke-') as folder:
        tmp = Path(folder)
        source = tmp / 'original.mp4'
        reencoded = tmp / 'reencoded.mp4'
        black = tmp / 'black.mp4'
        ffmpeg('-f','lavfi','-i','testsrc2=size=160x90:rate=4:duration=3',
               '-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(source))
        ffmpeg('-i',str(source),'-c:v','libx264','-preset','ultrafast','-crf','30',str(reencoded))
        ffmpeg('-f','lavfi','-i','color=black:s=160x90:r=4:d=3',
               '-c:v','libx264',str(black))
        scenarios = [
            ('identical bytes',source,source,'byte_identical'),
            ('transcoded sample',source,reencoded,'video_similarity_candidate'),
            ('different flat scene',source,black,'unresolved'),
        ]
        results = []
        for label, left, right, expected in scenarios:
            observed = compare_videos(left, right, samples=8)
            results.append({'scenario':label,'expected':expected,
                            'observed':observed['relation'],
                            'matched_samples':len(observed['matched_samples']),
                            'pass':observed['relation']==expected})
        print(json.dumps({'kind':'synthetic smoke tests, not real-world accuracy benchmark',
                          'results':results},indent=2))
        if not all(r['pass'] for r in results):
            raise SystemExit(1)


if __name__ == '__main__':
    main()