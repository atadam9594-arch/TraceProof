import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from traceproof.ai_origin import assess_file, parse_c2pa_report


def report(source="trainedAlgorithmicMedia", signed=True, bad=False):
    manifest = {"assertions": [{"label": "c2pa.actions.v2", "data": {"actions": [
        {"action": "c2pa.created", "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/" + source}
    ]}}]}
    if signed:
        manifest["signature_info"] = {"issuer": "Test issuer"}
    return {"active_manifest": "test", "manifests": {"test": manifest},
            "validation_status": [{"code":"fake"}] if bad else []}


class AiOriginTests(unittest.TestCase):
    def test_credential_ai_claim(self):
        r = parse_c2pa_report(report(), file_bound=True)
        self.assertEqual(r["outcome"], "ai_provenance_credential")
        self.assertIsNone(r["ai_probability"])
    def test_plain_json_not_verified(self):
        self.assertEqual(parse_c2pa_report(report())["outcome"], "unverified_ai_declaration")
    def test_unsigned_not_verified(self):
        self.assertEqual(parse_c2pa_report(report(signed=False),file_bound=True)["outcome"], "unverified_ai_declaration")
    def test_invalid_credential_not_accepted(self):
        self.assertEqual(parse_c2pa_report(report(bad=True),file_bound=True)["outcome"], "invalid_credential")
    def test_no_active_manifest_undetermined(self):
        self.assertEqual(parse_c2pa_report({})["outcome"], "undetermined")
    def test_non_ai_action_not_human(self):
        self.assertEqual(parse_c2pa_report(report("digitalCapture"),file_bound=True)["outcome"], "undetermined")
    def test_composite_partial(self):
        r = parse_c2pa_report(report("compositeWithTrainedAlgorithmicMedia"),file_bound=True)
        self.assertEqual(r["signals"][0]["scope"], "AI composite / partial contribution")
    def test_ignores_free_text_with_ai_keywords(self):
        r = report("digitalCapture")
        r["manifests"]["test"]["title"] = "generated with an AI model"
        self.assertEqual(parse_c2pa_report(r,file_bound=True)["outcome"], "undetermined")
    def test_file_defaults_to_no_network(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"photo.jpg";p.write_bytes(b"hello")
            with patch("traceproof.ai_origin.subprocess.run") as run:
                r=assess_file(p)
                run.assert_not_called()
            self.assertEqual(r["outcome"],"inspection_not_run")
            self.assertEqual(len(r["file"]["sha256"]),64)
    def test_report_unbound(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"photo.jpg";p.write_bytes(b"hello")
            m=Path(d)/"report.json";m.write_text(json.dumps(report()))
            r=assess_file(p,report_json=m)
            self.assertEqual(r["outcome"],"unverified_ai_declaration")
            self.assertFalse(r["report_bound_to_file_by_this_run"])
    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a";p.write_bytes(b"a")
            link=Path(d)/"b";link.symlink_to(p)
            with self.assertRaises(ValueError):assess_file(link)
    def test_missing_c2patool(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a";p.write_bytes(b"a")
            with patch("traceproof.ai_origin.shutil.which",return_value=None):
                r=assess_file(p,allow_external_provenance=True)
            self.assertEqual(r["outcome"],"inspection_unavailable")