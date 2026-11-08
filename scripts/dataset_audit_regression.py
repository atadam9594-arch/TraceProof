"""Synthetic audit→benchmark regression; never a real-world accuracy claim."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from traceproof.dataset import SCHEMA, audit_dataset
from traceproof.benchmark import MANIFEST_SCHEMA, evaluate_manifest


def build(path,source):
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                    '-f','lavfi','-i',source,'-c:v','libx264','-preset','veryfast',
                    '-pix_fmt','yuv420p',str(path)],check=True,timeout=30)


def main():
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('This regression requires FFmpeg and ffprobe')
    with tempfile.TemporaryDirectory(prefix='traceproof-dataset-smoke-') as d:
        root=Path(d)
        a=root/'source.mp4'; b=root/'other.mp4'
        build(a,'testsrc2=size=160x90:rate=10:duration=3')
        build(b,'color=c=black:s=160x90:r=10:d=3')
        videos=[]
        for f in (a,b):
            videos.append({'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),
                           'license_spdx':'CC0-1.0','source_url':'https://example.org/synthetic-only',
                           'rights_confirmed':True})
        audit=root/'audit.json'
        audit.write_text(json.dumps({'schema':SCHEMA,'curator':'TraceProof synthetic tests',
             'label_method':'Programmatically generated deterministic FFmpeg fixtures, not real videos',
             'files':videos}),encoding='utf-8')
        manifest=root/'pairs.json';manifest.write_text(json.dumps({'schema':MANIFEST_SCHEMA,
            'pairs':[{'id':'negative','left':a.name,'right':b.name,'expected_overlap':False}]}))
        report=audit_dataset(audit,benchmark_manifest=manifest)
        if not report['ok'] or report['hash_matches'] != 2:
            raise AssertionError('Expected synthetic samples to pass the hash audit')
        result=evaluate_manifest(manifest,samples=4)
        if result['summary']['evaluated'] != 1 or result['summary']['errors']:
            raise AssertionError('Could not evaluate audited videos')
        b.write_bytes(b'changed after hashing')
        after=audit_dataset(audit,benchmark_manifest=manifest)
        if after['ok'] or after['entries'][1].get('reason')!='sha256_mismatch':
            raise AssertionError('File tampering went undetected')
        print(json.dumps({'synthetic':True,'audit_before':report['ok'],
            'tampering_detected':not after['ok'],'pairs_evaluated':1,
            'warning':'Does not benchmark real video accuracy or verify rights claims'}))

if __name__=='__main__':
    main()