"""Full HTTP regression of >2.5 MB local video uploads; synthetic only.

Requires FFmpeg/ffprobe and Pillow. No external network, datasets or uploads.
"""
from __future__ import annotations
import http.client
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traceproof.server import Handler


def main():
    with tempfile.TemporaryDirectory(prefix='traceproof-regression-') as directory:
        video = Path(directory) / 'test.mp4'
        subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                        '-f','lavfi','-i','testsrc2=size=640x360:rate=20:duration=12',
                        '-c:v','libx264','-preset','ultrafast','-crf','5','-pix_fmt','yuv420p',str(video)],
                       check=True,timeout=90)
        size=video.stat().st_size
        if size <= 2_500_000:
            raise AssertionError(f'Fixture too small to exercise large-video path: {size}')
        with ThreadingHTTPServer(('127.0.0.1',0),Handler) as server:
            server.daemon_threads=True
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            port=server.server_port
            def post(path,data,headers):
                conn=http.client.HTTPConnection('127.0.0.1',port,timeout=35)
                try:
                    conn.request('POST',path,data,headers)
                    response=conn.getresponse()
                    obj=json.loads(response.read())
                    if response.status!=200:
                        raise AssertionError(f'{path}: {response.status}, {obj}')
                    return obj
                finally:
                    conn.close()
            def js(path,value):
                return post(path,json.dumps(value).encode(),{'Content-Type':'application/json'})
            try:
                response=js('/api/video/session',{'left':{'name':'reference.mp4','size':size},
                                                  'right':{'name':'comparison.mp4','size':size},'samples':4})
                token=response['session']
                for side in ('left','right'):
                    with video.open('rb') as inp:
                        offset=0
                        while chunk:=inp.read(response['chunk_bytes']):
                            post('/api/video/chunk',chunk,{'Content-Type':'application/octet-stream',
                                'X-TraceProof-Session':token,'X-TraceProof-Side':side,
                                'X-TraceProof-Offset':str(offset)})
                            offset+=len(chunk)
                    if offset!=size:
                        raise AssertionError(f'Incomplete upload: {offset}/{size}')
                js('/api/video/start',{'session':token})
                deadline=time.monotonic()+120
                while True:
                    status=js('/api/video/status',{'session':token})
                    if status['status']=='done':break
                    if status['status']=='failed' or time.monotonic()>deadline:
                        raise AssertionError(f'Video job failed or timed out: {status}')
                    time.sleep(.4)
                result=status['result']
                if result['relation']!='byte_identical':
                    raise AssertionError('Matching test videos did not produce a byte-identical result')
                print(json.dumps({'synthetic_large_video_bytes':size,'http_chunk_bytes':response['chunk_bytes'],
                                  'relation':result['relation'],'pass':True},indent=2))
            finally:
                server.traceproof_video_uploads.close()
                server.shutdown()
                thread.join(timeout=5)

if __name__=='__main__':main()