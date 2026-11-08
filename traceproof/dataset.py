"""Bounded, entirely offline integrity and rights-assertion audit of benchmark videos.

A curator-supplied metadata record is NOT proof of license, consent, source,
label accuracy, or provenance. Only file bytes matching recorded SHA-256 are
cryptographically verifiable here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

from .benchmark import _relative_video, load_manifest, MAX_VIDEO_BYTES

SCHEMA = "traceproof.dataset.audit.v1"
REPORT_SCHEMA = "traceproof.dataset.audit.result.v1"
MAX_AUDIT_BYTES = 1_000_000
MAX_FILES = 200
SPDX_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-+]{0,79}\Z")
SHA_PATTERN = re.compile(r"[a-f0-9]{64}\Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as data:
        for block in iter(lambda: data.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= MAX_AUDIT_BYTES:
        raise ValueError("Audit manifest is missing, symlinked or exceeds 1 MB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Audit manifest is not valid UTF-8 JSON") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "curator", "label_method", "files"} or data["schema"] != SCHEMA:
        raise ValueError("Unsupported audit manifest schema")
    for key in ("curator", "label_method"):
        if not isinstance(data[key], str) or not 3 <= len(data[key].strip()) <= 300:
            raise ValueError("Curator and label method must be described")
    files = data["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("Audit manifest must describe 1–200 videos")
    seen = set()
    for f in files:
        if not isinstance(f, dict) or set(f) != {"path", "sha256", "license_spdx", "source_url", "rights_confirmed"}:
            raise ValueError("Each video needs path, sha256, license_spdx, source_url and rights_confirmed")
        path_name = f["path"]
        if not isinstance(path_name, str) or not path_name or path_name in seen:
            raise ValueError("Invalid or duplicated video path")
        seen.add(path_name)
        if not isinstance(f["sha256"], str) or not SHA_PATTERN.fullmatch(f["sha256"]):
            raise ValueError("Invalid SHA-256")
        if not isinstance(f["license_spdx"], str) or not SPDX_PATTERN.fullmatch(f["license_spdx"]):
            raise ValueError("License must use a short SPDX expression identifier")
        if not isinstance(f["source_url"], str) or not f["source_url"].startswith("https://") or len(f["source_url"]) > 1000:
            raise ValueError("Source must be described by an HTTPS URL")
        if type(f["rights_confirmed"]) is not bool:
            raise ValueError("Rights confirmation must be a boolean attestation")
    return data


def audit_dataset(audit_path: str | Path, *, root: str | Path | None = None,
                  benchmark_manifest: str | Path | None = None) -> dict:
    audit_path = Path(audit_path)
    data = _load(audit_path)
    base = Path(root).resolve(strict=True) if root is not None else audit_path.resolve(strict=True).parent
    if not base.is_dir():
        raise ValueError("Dataset root must be a directory")
    entries = []
    known = set()
    for f in data["files"]:
        name = f["path"]
        record = {"path": name, "hash_match": False,
                  "rights_asserted": f["rights_confirmed"],
                  "metadata_present": True, "status": "unchecked"}
        try:
            video = _relative_video(base, name)
            record["hash_match"] = _sha256(video) == f["sha256"]
            record["status"] = "ok" if record["hash_match"] and f["rights_confirmed"] else "review_required"
            if not record["hash_match"]:
                record["reason"] = "sha256_mismatch"
            elif not f["rights_confirmed"]:
                record["reason"] = "rights_unconfirmed"
        except (OSError, ValueError):
            record["status"] = "review_required"
            record["reason"] = "unavailable_or_invalid_path"
        entries.append(record)
        known.add(name)
    pair_coverage = None
    if benchmark_manifest is not None:
        manifest = load_manifest(benchmark_manifest)
        used = {p[s] for p in manifest["pairs"] for s in ("left", "right")}
        # Every referenced file must be listed in the audit manifest.
        unlisted = sorted(used - known)
        pair_coverage = {"listed": len(used) - len(unlisted),
                         "referenced": len(used), "unlisted": unlisted}
    passed = all(e["status"] == "ok" for e in entries) and (pair_coverage is None or not pair_coverage["unlisted"])
    return {
        "schema": REPORT_SCHEMA,
        "audit_manifest_sha256": _sha256(audit_path),
        "curator_asserted": True,
        "ok": passed,
        "videos_checked": len(entries),
        "hash_matches": sum(e["hash_match"] for e in entries),
        "rights_asserted": sum(e["rights_asserted"] for e in entries),
        "entries": entries,
        "benchmark_coverage": pair_coverage,
        "limitations": [
            "Verified SHA-256 checks file bytes only, not video authenticity or provenance",
            "Licenses, sources, usage rights and labels are curator assertions, not independently verified",
            "Source URLs are recorded but never visited or verified by TraceProof",
            "Only a licensed, consented and well-labeled dataset can support meaningful evaluation",
        ],
    }