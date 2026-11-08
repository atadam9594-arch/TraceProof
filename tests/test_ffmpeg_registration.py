from pathlib import Path
import os
import stat
import tempfile
import unittest
from unittest.mock import patch
from traceproof import diagnostics


class FFmpegRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.dir=self.home/'bin'
        self.dir.mkdir()
        self.files=[]
        for name in ('ffmpeg','ffprobe'):
            file=self.dir/(name+('.exe' if os.name=='nt' else ''))
            file.write_bytes(b'placeholder for a trusted executable')
            if os.name!='nt':file.chmod(file.stat().st_mode|stat.S_IXUSR)
            self.files.append(file)
        self.env=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.home),
                                       'LOCALAPPDATA':str(self.home)},clear=False)
        self.env.start();self.addCleanup(self.env.stop)

    def fake_version(self,path):
        name=Path(path).stem if os.name=='nt' else Path(path).name
        return True,name+' version 7.0'

    def test_register_and_reuse_from_local_config(self):
        with patch.object(diagnostics,'_version',side_effect=self.fake_version):
            result=diagnostics.register_ffmpeg_directory(self.dir)
        self.assertTrue(result['registered'])
        self.assertTrue(Path(diagnostics.find_binary('ffmpeg')).samefile(self.files[0]))
        self.assertTrue(Path(diagnostics.find_binary('ffprobe')).samefile(self.files[1]))
        doc=diagnostics._config_path().read_text()
        self.assertIn('traceproof.tools.v1',doc)
        if os.name!='nt':self.assertEqual(diagnostics._config_path().stat().st_mode & 0o777,0o600)
        diagnostics.clear_ffmpeg_directory()
        self.assertFalse(diagnostics._config_path().exists())

    def test_reject_unverified_version(self):
        with patch.object(diagnostics,'_version',return_value=(True,'something else')):
            with self.assertRaisesRegex(ValueError,'recognized version'):
                diagnostics.register_ffmpeg_directory(self.dir)
        self.assertFalse(diagnostics._config_path().exists())

    def test_reject_missing_ffprobe(self):
        self.files[1].unlink()
        with self.assertRaisesRegex(ValueError,'both|ffprobe'):
            diagnostics.register_ffmpeg_directory(self.dir)

    def test_invalid_config_is_ignored(self):
        target=diagnostics._config_path();target.parent.mkdir(exist_ok=True)
        target.write_text('{"schema":"wrong","directory":"/secret"}')
        self.assertIsNone(diagnostics._saved_binary_dir())
        target.write_text('not json')
        self.assertIsNone(diagnostics._saved_binary_dir())

    def test_unsupported_command_does_not_execute(self):
        with self.assertRaises(ValueError):diagnostics.find_binary('sh')

    def test_cli_register_and_forget(self):
        from traceproof.cli import main
        with patch.object(diagnostics,'_version',side_effect=self.fake_version):
            self.assertEqual(main(['ffmpeg-register','--dir',str(self.dir)]),0)
        self.assertTrue(diagnostics._config_path().exists())
        self.assertEqual(main(['ffmpeg-forget']),0)

    def test_symlinked_config_not_overwritten(self):
        dest=diagnostics._config_path();dest.parent.mkdir(exist_ok=True)
        other=self.home/'out.json';other.write_text('secret')
        try:dest.symlink_to(other)
        except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable')
        with patch.object(diagnostics,'_version',side_effect=self.fake_version):
            with self.assertRaisesRegex(ValueError,'symlinked'):
                diagnostics.register_ffmpeg_directory(self.dir)
        self.assertEqual(other.read_text(),'secret')

if __name__=='__main__':unittest.main()