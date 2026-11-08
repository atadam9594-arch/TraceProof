import unittest
from unittest.mock import patch
from traceproof.desktop import launch


class FakeServer:
    def __init__(self,hostport,handler):
        assert hostport == ('127.0.0.1',0)
        self.server_port=41723
        self.closed=False
    def __enter__(self):return self
    def __exit__(self,*a):self.closed=True
    def serve_forever(self,**kw):pass
    def shutdown(self):pass


class FakeTimer:
    def __init__(self,delay,fn,args):self.fn,self.args=fn,args
    def start(self):self.fn(*self.args)


class DesktopTests(unittest.TestCase):
    def test_desktop_only_binds_loopback_and_opens_browser(self):
        visited=[]
        with patch('traceproof.desktop.threading.Timer',FakeTimer):
            self.assertEqual(launch(browser_open=visited.append,server_class=FakeServer),0)
        self.assertEqual(visited,['http://127.0.0.1:41723/'])

if __name__=='__main__':unittest.main()