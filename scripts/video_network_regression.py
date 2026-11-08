"""Synthetic full FFmpeg video-network smoke; NOT a real-world accuracy benchmark."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traceproof.video_network import scan_video_network, render_network_report


def ffmpeg(*args):
    subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',*args],
                   timeout=45,check=True)


def main():
    with tempfile.TemporaryDirectory(prefix='traceproof-network-smoke-') as folder:
        root=Path(folder)
        source=root/'001-source.mp4'
        dup=root/'002-duplicate.mp4'
        unrelated=root/'003-black.mp4'
        ffmpeg('-f','lavfi','-i','testsrc2=size=160x90:rate=5:duration=3',
               '-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(source))
        shutil.copyfile(source,dup)
        ffmpeg('-f','lavfi','-i','color=black:s=160x90:r=5:d=3',
               '-c:v','libx264','-preset','ultrafast',str(unrelated))
        report=scan_video_network(root,samples=4)
        summary=report['summary']
        assert summary['videos']==3 and summary['analyzed']==3,report
        assert summary['byte_identical_edges']==1,report
        assert summary['similarity_edges']==0,report
        assert summary['unresolved_pairs']==2,report
        assert summary['connected_groups']==2,report
        html=render_network_report(report)
        assert '<svg' in html and '<script' not in html
        print(json.dumps({'kind':'synthetic video-network regression, not accuracy research',
                          'passed':True,'summary':summary},indent=2))

if __name__=='__main__':main()