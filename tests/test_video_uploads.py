"""Security and end-to-end tests for large-file localhost video workflow."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from traceproof.uploads import (VideoUploadManager, UploadError, MAX_CHUNK,
                                MAX_VIDEO_BYTES, SESSION_TTL_SECONDS)
from traceproof.server import Handler


def fake_compare(a,b,*,samples):
    if a.read_bytes() != b'video-a' or b.read_bytes() != b'video-b':
        raise AssertionError('Unexpected file bytes')
    return {'left':{'name':'left.video'}, 'right':{'name':'right.video'},
            'relation':'unresolved','matched_samples':[], 'warning':'Not proof',
            'samples':samples}


def body(left=7,right=7,samples=12):
    return {'left':{'name':'first.mp4','size':left},
            'right':{'name':'second.webm','size':right},'samples':samples}


class UploadManagerTests(unittest.TestCase):
    def setUp(self):
        self.now=0
        self.mgr=VideoUploadManager(clock=lambda:self.now, compare=fake_compare)

    def tearDown(self):
        self.mgr.close()

    def token(self):
        return self.mgr.create(body())['session']

    def test_session_token_random_and_hex(self):
        self.assertRegex(self.token(),r'^[a-f0-9]{48}$')

    def test_bytes_and_name_limits(self):
        for bad in (-1,0,MAX_VIDEO_BYTES+1,True,1.2):
            with self.subTest(value=bad),self.assertRaises(UploadError):
                self.mgr.create(body(left=bad))
        for bad in ('../escape.mp4','<a>\n.mp4','', 'file.exe'):
            if bad == '../escape.mp4':
                # User-supplied name is display-only; no filesystem path is used.
                self.assertEqual(self.mgr.create({**body(),'left':{'name':bad,'size':7}})['status'],'uploading')
                self.mgr.cancel(self.mgr.session['token'])
                continue
            with self.subTest(name=bad),self.assertRaises(UploadError):
                self.mgr.create({**body(),'left':{'name':bad,'size':7}})

    def test_sample_limits(self):
        for bad in (True,0,17,'4'):
            with self.subTest(value=bad),self.assertRaises(UploadError):
                self.mgr.create(body(samples=bad))

    def test_one_active_session(self):
        self.token()
        with self.assertRaises(UploadError) as e: self.mgr.create(body())
        self.assertEqual(e.exception.status,409)

    def test_unknown_session_rejected(self):
        self.token()
        for t in ('e'*48,'..',''):
            with self.subTest(token=t),self.assertRaises(UploadError):self.mgr.status(t)

    def test_chunk_size_limit(self):
        t=self.token()
        for data in (b'',b'x'*(MAX_CHUNK+1)):
            with self.assertRaises(UploadError):self.mgr.chunk(t,'left',0,data)

    def test_offset_and_declared_size(self):
        t=self.token()
        with self.assertRaises(UploadError):self.mgr.chunk(t,'left',1,b'xx')
        self.assertEqual(self.mgr.chunk(t,'left',0,b'v')['received'],1)
        with self.assertRaises(UploadError):self.mgr.chunk(t,'left',0,b'v')
        with self.assertRaises(UploadError):self.mgr.chunk(t,'left',1,b'y'*7)

    def test_start_before_complete(self):
        t=self.token()
        with self.assertRaises(UploadError) as e:self.mgr.begin(t)
        self.assertEqual(e.exception.status,409)

    def test_success_and_cleanup(self):
        t=self.token()
        folder=Path(self.mgr.session['folder'].name)
        self.mgr.chunk(t,'left',0,b'video-a')
        self.mgr.chunk(t,'right',0,b'video-b')
        self.assertEqual(self.mgr.begin(t)['status'],'analyzing')
        deadline=time.monotonic()+3
        while self.mgr.status(t)['status']=='analyzing' and time.monotonic()<deadline:
            time.sleep(.01)
        result=self.mgr.status(t)
        self.assertEqual(result['status'],'done')
        self.assertEqual(result['result']['samples'],12)
        self.assertEqual(result['result']['left']['name'],'first.mp4')
        self.assertFalse(folder.exists())
        self.assertEqual(self.mgr.create(body())['status'],'uploading')

    def test_expire_staging_session(self):
        t=self.token()
        folder=Path(self.mgr.session['folder'].name)
        self.now=SESSION_TTL_SECONDS+1
        with self.assertRaises(UploadError):self.mgr.status(t)
        self.assertFalse(folder.exists())

    def test_cancel_removes_staging_media(self):
        t=self.token()
        folder=Path(self.mgr.session['folder'].name)
        self.mgr.chunk(t,'left',0,b'vid')
        self.assertEqual(self.mgr.cancel(t)['status'],'cancelled')
        self.assertFalse(folder.exists())
        with self.assertRaises(UploadError):self.mgr.chunk(t,'left',3,b'xx')

    def test_worker_error_omits_local_path(self):
        t=self.token()
        self.mgr.compare=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('secret /home/private/file'))
        self.mgr.chunk(t,'left',0,b'video-a')
        self.mgr.chunk(t,'right',0,b'video-b')
        self.mgr.begin(t)
        end=time.monotonic()+3
        while self.mgr.status(t)['status']=='analyzing' and time.monotonic()<end: time.sleep(.01)
        answer=self.mgr.status(t)
        self.assertEqual(answer['status'],'failed')
        self.assertNotIn('/home',answer['error'])


class UploadHttpTests(unittest.TestCase):
    def setUp(self):
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.traceproof_video_uploads=VideoUploadManager(compare=fake_compare)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.traceproof_video_uploads.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, endpoint, data, *, headers=None, origin=None):
        h={'Content-Type':'application/json'}
        if headers:h.update(headers)
        if origin:h['Origin']=origin
        request=Request(self.base+endpoint,data=json.dumps(data).encode() if not isinstance(data,bytes) else data,headers=h,method='POST')
        try:
            with urlopen(request,timeout=5) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)

    def test_workflow(self):
        status,obj=self.request('/api/video/session',body())
        self.assertEqual(status,200)
        token=obj['session']
        self.assertEqual(obj['chunk_bytes'],MAX_CHUNK)
        for side,content in [('left',b'video-a'),('right',b'video-b')]:
            status,r=self.request('/api/video/chunk',content,headers={'Content-Type':'application/octet-stream','X-TraceProof-Session':token,'X-TraceProof-Side':side,'X-TraceProof-Offset':'0'})
            self.assertEqual(status,200)
            self.assertEqual(r['received'],7)
        status,result=self.request('/api/video/start',{'session':token})
        self.assertEqual(status,200)
        end=time.monotonic()+3
        while True:
            status,result=self.request('/api/video/status',{'session':token})
            if result['status']!='analyzing' or time.monotonic()>end: break
            time.sleep(.01)
        self.assertEqual(status,200)
        self.assertEqual(result['status'],'done')
        self.assertEqual(result['result']['right']['name'],'second.webm')

    def test_origin_rejected(self):
        status,_=self.request('/api/video/session',body(),origin='https://not-local.example')
        self.assertEqual(status,403)

    def test_wrong_type_and_bad_chunk(self):
        status,_=self.request('/api/video/chunk',b'hello')
        self.assertEqual(status,415)
        # Send an oversized Content-Length without a body. Server must reject at headers.
        import http.client
        connection = http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        try:
            connection.putrequest('POST','/api/video/chunk')
            connection.putheader('Content-Type','application/octet-stream')
            connection.putheader('Content-Length',str(MAX_CHUNK+1))
            connection.endheaders()
            response=connection.getresponse()
            self.assertEqual(response.status,413)
            response.read()
        finally:
            connection.close()

    def test_local_capability_report(self):
        with urlopen(self.base+'/api/video/capabilities',timeout=5) as response:
            body=json.load(response)
            self.assertEqual(response.status,200)
        self.assertIs(type(body['video_analysis_available']),bool)
        self.assertEqual(body['max_file_bytes'],250000000)
        self.assertEqual(body['chunk_bytes'],MAX_CHUNK)

    def test_video_page_and_script_available(self):
        for resource,expected in [('/video',b'250 MB'),('/video.js',b'/api/video/chunk'),('/video.css',b'#progress')]:
            with self.subTest(path=resource),urlopen(self.base+resource,timeout=5) as r:
                self.assertEqual(r.status,200)
                if resource == '/video':
                    self.assertIn('text/html',r.headers.get('Content-Type',''))
                self.assertIn(expected,r.read())


if __name__=='__main__':unittest.main()

class LargeTransferTests(unittest.TestCase):
    """Demonstrate the new protocol can handle files beyond the old 2.5 MB cap."""
    def test_streaming_four_megabyte_video_without_base64(self):
        from traceproof.uploads import MAX_CHUNK
        size = 4_200_000
        mgr = VideoUploadManager(compare=lambda a,b,*,samples: {
            'left':{'name':a.name,'size':a.stat().st_size},
            'right':{'name':b.name,'size':b.stat().st_size},
            'relation':'unresolved','matched_samples':[], 'warning':'Not proof'
        })
        try:
            meta = body(left=size,right=size)
            token = mgr.create(meta)['session']
            block = b'Z' * MAX_CHUNK
            for side in ('left','right'):
                offset = 0
                while offset < size:
                    data = block[:min(MAX_CHUNK,size-offset)]
                    mgr.chunk(token,side,offset,data)
                    offset += len(data)
            mgr.begin(token)
            deadline = time.monotonic()+5
            while mgr.status(token)['status']=='analyzing' and time.monotonic()<deadline:
                time.sleep(.01)
            answer=mgr.status(token)
            self.assertEqual(answer['status'],'done')
            self.assertEqual(answer['result']['left']['size'],size)
        finally:
            mgr.close()