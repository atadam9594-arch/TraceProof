"""Evidence-first AI origin assessment. No universal AI detector is claimed.

C2PA validation is delegated to c2patool, and is never run implicitly:
its reader can fetch externally hosted C2PA manifests. User consent is required.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

SCHEMA = "traceproof.ai_origin.v1"
MAX_FILE_BYTES = 250_000_000
MAX_REPORT_BYTES = 2_000_000
AI_SOURCE_TYPES = frozenset((
    "trainedAlgorithmicMedia", "trainedAlgorithmicData",
    "compositeWithTrainedAlgorithmicMedia",
))


def _result(outcome, *, signals=None, problems=None, tool="none", file_bound=False):
    return {
        "schema": SCHEMA,
        "outcome": outcome,
        "signals": signals or [],
        "problems": problems or [],
        "tool": tool,
        "report_bound_to_file_by_this_run": file_bound,
        "ai_probability": None,
        "human_probability": None,
        "limitations": [
            "A C2PA claim is not a general-purpose AI classifier",
            "An absent AI declaration never proves human authorship",
            "C2PA credentials may be removed by editing or sharing",
            "Signature validity does not establish signer identity without a separately trusted authority",
            "This version has no independently calibrated text, image, audio or video AI detector",
        ],
    }


def parse_c2pa_report(report, *, file_bound=False):
    """Interpret active C2PA creation actions only; never trust a pasted JSON report.

    A report from a live c2patool run can be tied to a file read by that tool,
    but the issuer's real identity remains unverified without separate trust.
    """
    if not isinstance(report, dict):
        raise ValueError("C2PA report must be a JSON object")
    manifests = report.get("manifests")
    active = report.get("active_manifest")
    if not isinstance(manifests, dict) or not isinstance(active, str) or active not in manifests:
        return _result("undetermined", problems=["No active C2PA manifest in report"], tool="c2patool", file_bound=file_bound)
    manifest = manifests[active]
    if not isinstance(manifest, dict):
        return _result("invalid_credential", problems=["Invalid active manifest structure"], tool="c2patool", file_bound=file_bound)
    problems = report.get("validation_status") or []
    if not isinstance(problems, list):
        return _result("invalid_credential", problems=["Malformed validation status"], tool="c2patool", file_bound=file_bound)
    # Validator can report problems either at store level or manifest level.
    manifest_status = manifest.get("validation_status") or []
    if not isinstance(manifest_status, list):
        return _result("invalid_credential", problems=["Malformed manifest status"], tool="c2patool", file_bound=file_bound)
    bad = bool(problems or manifest_status)
    signals = []
    for assertion in manifest.get("assertions", []):
        if not isinstance(assertion, dict):
            continue
        label = assertion.get("label", "")
        if label not in ("c2pa.actions", "c2pa.actions.v2"):
            continue
        data = assertion.get("data", {})
        if not isinstance(data, dict):
            continue
        actions = data.get("actions", [])
        if not isinstance(actions, list):
            continue
        for action in actions[:100]:
            if not isinstance(action, dict):
                continue
            kind = action.get("action")
            source = action.get("digitalSourceType", "")
            if not isinstance(source, str) or not isinstance(kind, str):
                continue
            tail = source.rsplit("/", 1)[-1]
            if tail not in AI_SOURCE_TYPES:
                continue
            if kind not in ("c2pa.created", "c2pa.placed", "c2pa.edited"):
                continue
            signals.append({
                "source": "C2PA action declaration", "action": kind,
                "digital_source_type": tail,
                "scope": "AI-generated or AI-involved" if tail != "compositeWithTrainedAlgorithmicMedia" else "AI composite / partial contribution",
            })
    if bad:
        return _result("invalid_credential", signals=signals,
                       problems=["C2PA tool reported validation problems; claims must not be accepted"],
                       tool="c2patool", file_bound=file_bound)
    if not signals:
        return _result("undetermined", problems=["No recognized AI source declaration in active credential"],
                       tool="c2patool", file_bound=file_bound)
    signed = isinstance(manifest.get("signature_info"), dict) and bool(manifest["signature_info"])
    if file_bound and signed:
        return _result("ai_provenance_credential", signals=signals,
                       problems=["Signer trust and real-world identity have not been independently established"],
                       tool="c2patool", file_bound=True)
    return _result("unverified_ai_declaration", signals=signals,
                   problems=["Imported or unsigned claims are not independently verified for this file"],
                   tool="c2patool", file_bound=file_bound)


def _sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assess_file(path, *, allow_external_provenance=False, report_json=None):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or not 0 < p.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError("Input must be a non-symlink regular file from 1 byte to 250 MB")
    digest = _sha256(p)
    if report_json is not None:
        source = Path(report_json)
        if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("C2PA report must be a regular JSON file of at most 2 MB")
        try:
            report = json.loads(source.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid external JSON report") from exc
        result = parse_c2pa_report(report, file_bound=False)
    elif not allow_external_provenance:
        result = _result("inspection_not_run", problems=[
            "Automatic C2PA inspection requires explicit opt-in because c2patool can fetch remote manifests",
            "Use --allow-external-provenance after reviewing the privacy implications",
        ])
    else:
        exe = shutil.which("c2patool")
        if not exe:
            result = _result("inspection_unavailable", problems=[
                "c2patool is not installed; install it independently to enable optional C2PA validation"
            ])
        else:
            # Limit output before loading into memory; avoid shell and cap wall-clock time.
            try:
                with tempfile.TemporaryFile(mode="w+b") as out:
                    completed = subprocess.run([exe, str(p.resolve())], stdout=out,
                                               stderr=subprocess.DEVNULL,
                                               timeout=30, check=False, stdin=subprocess.DEVNULL)
                    out.seek(0, 2)
                    if out.tell() > MAX_REPORT_BYTES:
                        raise ValueError("C2PA report exceeds safe output limit")
                    out.seek(0)
                    payload = out.read()
                if completed.returncode != 0:
                    result = _result("inspection_failed", problems=["C2PA verifier could not inspect this asset"])
                else:
                    try:
                        report = json.loads(payload.decode("utf-8"))
                    except (UnicodeError, json.JSONDecodeError):
                        result = _result("inspection_failed", problems=["C2PA verifier returned invalid JSON"])
                    else:
                        result = parse_c2pa_report(report, file_bound=True)
            except (OSError, subprocess.TimeoutExpired):
                result = _result("inspection_failed", problems=["C2PA tool timed out or failed to start"])
    result["file"] = {"name": p.name, "sha256": digest, "size_bytes": p.stat().st_size}
    return result