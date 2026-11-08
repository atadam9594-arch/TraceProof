"""Small *synthetic* FFmpeg benchmark smoke test, not a real-world accuracy claim."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traceproof.benchmark import MANIFEST_SCHEMA, evaluate_manifest


def run(*args):
    subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', *args],
                   check=True, timeout=80)


def main():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('Install ffmpeg and ffprobe to run the synthetic regression')
    with tempfile.TemporaryDirectory(prefix='traceproof-bench-') as folder:
        root = Path(folder)
        original = root / 'original.mp4'
        run('-f','lavfi','-i','testsrc2=size=320x180:rate=20:duration=7',
            '-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',str(original))
        (root / 'duplicate.mp4').write_bytes(original.read_bytes())
        run('-i',str(original), '-c:v','libx264','-preset','veryfast','-crf','25',str(root/'transcoded.mp4'))
        run('-f','lavfi','-i','color=c=black:s=320x180:r=20:d=7',
            '-c:v','libx264','-preset','veryfast',str(root/'unrelated.mp4'))
        pairs = [
            {'id':'exact','left':'original.mp4','right':'duplicate.mp4','expected_overlap':True},
            {'id':'transcoded','left':'original.mp4','right':'transcoded.mp4','expected_overlap':True},
            {'id':'negative-flat','left':'original.mp4','right':'unrelated.mp4','expected_overlap':False},
        ]
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps({'schema':MANIFEST_SCHEMA,'pairs':pairs}))
        result = evaluate_manifest(manifest, samples=12)
        summary = result['summary']
        outcomes = {pair['id']: pair for pair in result['pairs']}
        # Stable invariants: exact bytes match, unrelated blank footage does not.
        # A lossy re-encode is deliberately *not* guaranteed to match: this suite
        # should surface genuine false negatives instead of hiding them.
        if outcomes['exact']['relation'] != 'byte_identical' or outcomes['negative-flat']['predicted_overlap']:
            raise AssertionError(f'Synthetic fixture invariants failed: {outcomes}')
        if summary['errors'] or summary['evaluated'] != 3:
            raise AssertionError(f'Synthetic benchmark could not evaluate all pairs: {summary}')
        print(json.dumps({'kind':'synthetic smoke test only — not real-world accuracy',
                          'summary':summary,'pairs':result['pairs']},indent=2))


if __name__ == '__main__':
    main()