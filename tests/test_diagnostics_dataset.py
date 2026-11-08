"""Zero-network doctor, dataset integrity and limited local UI endpoint tests."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import urlopen

from traceproof.dataset import SCHEMA, audit_dataset
from traceproof.diagnostics import diagnose, find_binary, guidance
from traceproof.cli import main
from traceproof.server import Handler


class DiagnosticsTests(unittest.TestCase):
    def test_missing_tools_do_not_claim_readiness(self):
        with patch("traceproof.diagnostics.shutil.which", return_value=None):
            result = diagnose()
        self.assertFalse(result["ready"])
        self.assertFalse(result["components"]["ffmpeg"]["ready"])
        self.assertNotIn("/home/", json.dumps(result))

    def test_valid_path_invocation_uses_no_shell(self):
        class Completed:
            returncode = 0
            stdout = "ffmpeg version 7.1\nmore info"
        with patch("traceproof.diagnostics.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("traceproof.diagnostics.subprocess.run", return_value=Completed()) as run:
            result = diagnose()
        self.assertTrue(result["ready"])
        self.assertEqual(result["components"]["ffprobe"]["version"], "ffmpeg version 7.1")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["timeout"], 4)

    def test_timeout_means_unavailable(self):
        import subprocess
        with patch("traceproof.diagnostics.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("traceproof.diagnostics.subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 4)):
            self.assertFalse(diagnose()["ready"])

    def test_path_override_used_when_exists(self):
        with tempfile.TemporaryDirectory() as d:
            filename = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            target = Path(d) / filename
            target.write_bytes(b"dummy")
            try:
                target.chmod(0o700)
            except OSError:
                pass
            with patch.dict(os.environ, {"TRACEPROOF_FFMPEG_DIR": d}), \
                 patch("traceproof.diagnostics.shutil.which", return_value=None):
                self.assertEqual(find_binary("ffmpeg"), str(target))

    def test_no_unknown_tools_allowed(self):
        with self.assertRaises(ValueError):
            find_binary("curl")

    def test_guides_no_automatic_execution(self):
        for name in ("Windows", "Linux", "Darwin"):
            text = " ".join(guidance(name)).lower()
            self.assertIn("ffmpeg", text)

    def test_doctor_check_returns_nonzero_when_missing(self):
        with patch("traceproof.diagnostics.shutil.which", return_value=None), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["doctor", "--check"]), 2)

    def test_doctor_json_outputs_report(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main(["doctor", "--json"]), 0)
        self.assertIn("components", json.loads(buf.getvalue()))

    def test_setup_routes_and_api(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            base = f"http://127.0.0.1:{srv.server_port}"
            for path, mime in (("/setup", "text/html"), ("/setup.js", "text/javascript"), ("/setup.css", "text/css")):
                with urlopen(base+path, timeout=5) as resp:
                    self.assertIn(mime, resp.headers["Content-Type"])
                    self.assertTrue(resp.read())
            with urlopen(base+"/api/system", timeout=10) as resp:
                self.assertEqual(json.load(resp)["schema"], "traceproof.diagnostics.v1")
        finally:
            srv.shutdown(); srv.server_close(); t.join(timeout=3)


class DatasetAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.a = self.base / "first.mp4"
        self.b = self.base / "second.mp4"
        self.a.write_bytes(b"first fixed bytes")
        self.b.write_bytes(b"second fixed bytes")
        self.dataset_path = self.base / "audit.json"
        self.pairs_path = self.base / "pairs.json"
        self.manifest = {
            "schema": SCHEMA, "curator": "Testing curator",
            "label_method": "Synthetic labels are not independent truth",
            "files": [self.entry(self.a), self.entry(self.b)]
        }
        self.write()
        self.pairs_path.write_text(json.dumps({"schema": "traceproof.benchmark.manifest.v1",
            "pairs": [{"id":"one", "left":"first.mp4", "right":"second.mp4", "expected_overlap":False}]}))

    @staticmethod
    def entry(path):
        return {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "license_spdx": "CC0-1.0", "source_url": "https://example.org/curated-video",
                "rights_confirmed": True}

    def write(self):
        self.dataset_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def audit(self):
        return audit_dataset(self.dataset_path, root=self.base, benchmark_manifest=self.pairs_path)

    def test_verified_bytes_and_benchmark_coverage(self):
        result = self.audit()
        self.assertTrue(result["ok"])
        self.assertEqual(result["hash_matches"], 2)
        self.assertEqual(result["benchmark_coverage"]["referenced"], 2)
        self.assertNotIn(str(self.base), json.dumps(result))

    def test_tamper_reported_but_not_trusted(self):
        self.a.write_bytes(b"mutated evidence")
        result = self.audit()
        self.assertFalse(result["ok"])
        self.assertEqual(result["entries"][0]["reason"], "sha256_mismatch")

    def test_rights_attestation_not_fabricated(self):
        self.manifest["files"][0]["rights_confirmed"] = False
        self.write()
        result = self.audit()
        self.assertFalse(result["ok"])
        self.assertFalse(result["entries"][0]["rights_asserted"])

    def test_unlisted_benchmark_video_rejected(self):
        self.manifest["files"] = self.manifest["files"][:1]
        self.write()
        result = self.audit()
        self.assertFalse(result["ok"])
        self.assertEqual(result["benchmark_coverage"]["unlisted"], ["second.mp4"])

    def test_missing_video_fails_closed(self):
        self.b.unlink()
        self.assertFalse(self.audit()["ok"])

    def test_duplicate_path_rejected(self):
        self.manifest["files"].append(self.manifest["files"][0])
        self.write()
        with self.assertRaises(ValueError):
            self.audit()

    def test_path_traversal_rejected(self):
        self.manifest["files"][0]["path"] = "../outside.mp4"
        self.write()
        self.assertFalse(self.audit()["ok"])

    def test_malformed_sha_rejected(self):
        self.manifest["files"][0]["sha256"] = "not-a-sha"
        self.write()
        with self.assertRaises(ValueError):
            self.audit()

    def test_http_source_required(self):
        self.manifest["files"][0]["source_url"] = "http://not-encrypted.test"
        self.write()
        with self.assertRaises(ValueError):
            self.audit()

    def test_bool_rights_required(self):
        self.manifest["files"][0]["rights_confirmed"] = 1
        self.write()
        with self.assertRaises(ValueError):
            self.audit()

    def test_bad_license_identifier_rejected(self):
        self.manifest["files"][0]["license_spdx"] = "Unclear proprietary license"
        self.write()
        with self.assertRaises(ValueError):
            self.audit()

    def test_symlink_video_does_not_pass(self):
        link = self.base / "linked.mp4"
        try:
            link.symlink_to(self.a)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        self.manifest["files"][0] = self.entry(self.a)
        self.manifest["files"][0]["path"] = "linked.mp4"
        self.write()
        self.assertFalse(self.audit()["ok"])

    def test_dataset_audit_cli(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = main(["dataset-audit", str(self.dataset_path),
                       "--root", str(self.base), "--benchmark-manifest", str(self.pairs_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(json.loads(buf.getvalue())["ok"])

    def test_benchmark_rejects_failed_audit(self):
        self.a.write_bytes(b"altered")
        with patch("traceproof.benchmark.evaluate_manifest") as fn, \
             contextlib.redirect_stdout(io.StringIO()):
            rc = main(["video-benchmark", str(self.pairs_path), "--root",str(self.base),
                       "--audit-dataset",str(self.dataset_path)])
        self.assertEqual(rc,2)
        fn.assert_not_called()

    def test_benchmark_keeps_audit_digest(self):
        fake={"schema":"traceproof.benchmark.result.v1","summary":{}}
        with patch("traceproof.benchmark.evaluate_manifest", return_value=fake), \
             contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = main(["video-benchmark", str(self.pairs_path), "--root",str(self.base),
                       "--audit-dataset",str(self.dataset_path)])
        self.assertEqual(rc,0)
        result=json.loads(buf.getvalue())
        self.assertTrue(result["dataset_audit"]["checks_passed"])
        self.assertEqual(len(result["dataset_audit"]["audit_manifest_sha256"]),64)


if __name__ == "__main__":
    unittest.main()