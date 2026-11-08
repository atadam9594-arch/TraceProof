"""Privacy-preserving portable ProofBundles and independent verification."""
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import zipfile
from .core import canonical, sha, utc_now, validate_case, evaluate, InvalidCase

BUNDLE_FORMAT = "traceproof.bundle.v1"
MAX_UNPACKED = 250 * 1024 * 1024
MAX_ENTRY = 200 * 1024 * 1024
MAX_COUNT = 256


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _load_crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        return Ed25519PrivateKey, Ed25519PublicKey, serialization
    except ImportError as e:
        raise RuntimeError("Signing requires optional package: pip install cryptography") from e


def create_keypair(private_path, public_path):
    EdPriv, _, serial = _load_crypto()
    private = EdPriv.generate()
    raw_private = private.private_bytes(serial.Encoding.PEM, serial.PrivateFormat.PKCS8, serial.NoEncryption())
    raw_public = private.public_key().public_bytes(serial.Encoding.PEM, serial.PublicFormat.SubjectPublicKeyInfo)
    dest = Path(private_path)
    if dest.exists() or Path(public_path).exists():
        raise FileExistsError("Refusing to overwrite key files")
    with os.fdopen(os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as f:
        f.write(raw_private)
    Path(public_path).write_bytes(raw_public)
    return _digest(private.public_key().public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw))


def _sign(data, private_path):
    EdPriv, _, serial = _load_crypto()
    key = serial.load_pem_private_key(Path(private_path).read_bytes(), password=None)
    if not isinstance(key, EdPriv):
        raise InvalidCase("Not an Ed25519 signing key")
    pub = key.public_key().public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw)
    return {"algorithm": "Ed25519", "public_key_b64": base64.b64encode(pub).decode(),
            "public_key_sha256": _digest(pub), "signature_b64": base64.b64encode(key.sign(data)).decode(),
            "trust_warning": "A signature proves possession of a key, not the real-world identity of its owner."}


def make_bundle(case, output=None, include_files=None, signing_key=None):
    """No originals included by default. include_files maps artifact ID to filesystem path."""
    validate_case(case)
    included = {}
    artifacts = {a["id"]: a for a in case["state"]["artifacts"]}
    include_files = include_files or {}
    if len(include_files) > MAX_COUNT - 8:
        raise InvalidCase("Too many bundled originals")
    for artifact_id, path in include_files.items():
        if artifact_id not in artifacts or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", artifact_id):
            raise InvalidCase("Unknown artifact identifier")
        p = Path(path)
        if not p.is_file() or p.stat().st_size > MAX_ENTRY:
            raise InvalidCase("Invalid artifact file or too large")
        raw = p.read_bytes()
        if _digest(raw) != artifacts[artifact_id]["sha256"] or len(raw) != artifacts[artifact_id]["size"]:
            raise InvalidCase("Source artifact differs from recorded hash or size")
        included["artifacts/" + artifact_id] = raw
    case_bytes = canonical(case)
    evaluation_bytes = canonical(evaluate(case))
    manifest = {"format": BUNDLE_FORMAT, "created_at_local_clock": utc_now(),
                "case_sha256": _digest(case_bytes), "evaluation_sha256": _digest(evaluation_bytes),
                "ledger_head": case["events"][-1]["hash"],
                "included_files": {name: _digest(blob) for name, blob in sorted(included.items())},
                "privacy": "No originals unless explicitly included; hashes can still be linkable.",
                "timestamp_warning": "Local clock is not an independently trusted timestamp."}
    manifest_bytes = canonical(manifest)
    signature = _sign(manifest_bytes, signing_key) if signing_key else None
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        z.writestr("case.json", case_bytes)
        z.writestr("evaluation.json", evaluation_bytes)
        z.writestr("manifest.json", manifest_bytes)
        z.writestr("README.txt", (
            "TraceProof ProofBundle v0.3\n"
            "Independent verification: python -m traceproof.cli verify <bundle.zip>\n"
            "Verify against a separately trusted public key to authenticate the signing key.\n"
            "A valid archive alone does NOT prove the underlying content is true or human-created.\n"
            "All timestamps are based on a local clock, without external notarization.\n"
        ).encode("utf-8"))
        if signature:
            z.writestr("signature.json", canonical(signature))
        for name, blob in sorted(included.items()):
            z.writestr(name, blob)
    data = stream.getvalue()
    if output is not None:
        Path(output).write_bytes(data)
    return data


def _strict_zip(raw):
    z = zipfile.ZipFile(io.BytesIO(raw), "r")
    members = z.infolist()
    if not 3 <= len(members) <= MAX_COUNT:
        raise InvalidCase("Invalid number of archive entries")
    names = [n.filename for n in members]
    if len(names) != len(set(names)):
        raise InvalidCase("Duplicate archive path")
    mandatory = {"case.json", "evaluation.json", "manifest.json"}
    if not mandatory <= set(names):
        raise InvalidCase("Missing required bundle entries")
    for entry in members:
        name = entry.filename
        if entry.flag_bits & 1 or name.startswith(("/", "\\")) or "\\" in name or any(x == ".." for x in name.split("/")):
            raise InvalidCase("Unsafe archive entry")
        if name not in mandatory | {"README.txt", "signature.json"} and not re.fullmatch(r"artifacts/[a-zA-Z0-9_-]{1,64}", name):
            raise InvalidCase("Unexpected archive entry")
        mode = entry.external_attr >> 16
        if stat.S_IFMT(mode) == stat.S_IFLNK:
            raise InvalidCase("Symlinks are not accepted")
        if entry.file_size > MAX_ENTRY or entry.file_size < 0:
            raise InvalidCase("Oversized entry")
    if sum(n.file_size for n in members) > MAX_UNPACKED:
        raise InvalidCase("Excessive uncompressed archive size")
    if any(n.file_size > 1_000_000 and n.file_size > n.compress_size * 1000 for n in members):
        raise InvalidCase("Suspicious expansion ratio")
    return z, names


def verify_bundle(data_or_path, trusted_public_key=None, originals=None):
    """Do not elevate 'valid ledger' into truth of the claims or trusted timestamps."""
    if isinstance(data_or_path, (str, Path)):
        p = Path(data_or_path)
        if p.stat().st_size > MAX_UNPACKED:
            raise InvalidCase("Bundle ZIP is too large")
        raw = p.read_bytes()
    else:
        raw = data_or_path
    if len(raw) > MAX_UNPACKED:
        raise InvalidCase("Bundle ZIP is too large")
    try:
        with _strict_zip(raw)[0] as z:
            names = z.namelist()
            content = {name: z.read(name) for name in names if name != "README.txt"}
    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError, EOFError) as e:
        raise InvalidCase("Malformed proof bundle") from e
    for field in ("case.json", "evaluation.json", "manifest.json"):
        if len(content[field]) > 5_000_000:
            raise InvalidCase("Oversized JSON")
    try:
        case = json.loads(content["case.json"])
        eval_ = json.loads(content["evaluation.json"])
        manifest = json.loads(content["manifest.json"])
    except (UnicodeError, ValueError, TypeError) as e:
        raise InvalidCase("Malformed JSON document") from e
    validate_case(case)
    if canonical(case) != content["case.json"] or canonical(eval_) != content["evaluation.json"] or canonical(manifest) != content["manifest.json"]:
        raise InvalidCase("Noncanonical JSON in bundle")
    if canonical(eval_) != canonical(evaluate(case)):
        raise InvalidCase("Evaluation no longer matches case")
    if manifest.get("format") != BUNDLE_FORMAT or manifest.get("case_sha256") != _digest(content["case.json"]) or manifest.get("evaluation_sha256") != _digest(content["evaluation.json"]):
        raise InvalidCase("Document digest mismatch")
    if manifest.get("ledger_head") != case["events"][-1]["hash"]:
        raise InvalidCase("Ledger head mismatch")
    included = manifest.get("included_files")
    if not isinstance(included, dict) or set(included) != {n for n in content if n.startswith("artifacts/")}:
        raise InvalidCase("Artifact inventory mismatch")
    artifact_by_id = {a["id"]: a for a in case["state"]["artifacts"]}
    for name, expected in included.items():
        id_ = name.split("/", 1)[1]
        if id_ not in artifact_by_id or _digest(content[name]) != expected:
            raise InvalidCase("Bundled artifact checksum mismatch")
        if expected != artifact_by_id[id_]["sha256"] or len(content[name]) != artifact_by_id[id_]["size"]:
            raise InvalidCase("Bundled artifact not bound to case")
    checks = {}
    for id_, path in (originals or {}).items():
        if id_ not in artifact_by_id:
            raise InvalidCase("Unknown artifact for external comparison")
        with open(path, "rb") as f:
            h, size = hashlib.sha256(), 0
            for chunk in iter(lambda: f.read(1024*1024), b""):
                h.update(chunk)
                size += len(chunk)
        checks[id_] = h.hexdigest() == artifact_by_id[id_]["sha256"] and size == artifact_by_id[id_]["size"]
    signed, sig_valid, trust = "signature.json" in content, False, "unsigned"
    if signed:
        try:
            obj = json.loads(content["signature.json"])
            if set(obj) != {"algorithm", "public_key_b64", "public_key_sha256", "signature_b64", "trust_warning"} or obj["algorithm"] != "Ed25519":
                raise ValueError("Invalid signature format")
            pub = base64.b64decode(obj["public_key_b64"], validate=True)
            sig = base64.b64decode(obj["signature_b64"], validate=True)
            if len(pub) != 32 or len(sig) != 64 or obj["public_key_sha256"] != _digest(pub):
                raise ValueError("Invalid key or signature")
            _, Pub, serial = _load_crypto()
            Pub.from_public_bytes(pub).verify(sig, content["manifest.json"])
            sig_valid = True
            trust = "signature_valid_untrusted_identity"
            if trusted_public_key:
                trusted = serial.load_pem_public_key(Path(trusted_public_key).read_bytes())
                trusted_pub = trusted.public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw)
                if pub != trusted_pub:
                    raise InvalidCase("Signer does not match supplied trusted public key")
                trust = "signature_valid_trusted_key_match"
        except InvalidCase:
            raise
        except Exception as e:
            raise InvalidCase("Signature verification failed") from e
    elif trusted_public_key:
        raise InvalidCase("Trusted signer required but bundle is unsigned")
    return {"bundle_valid": True, "ledger_valid": True, "signature_present": signed,
            "signature_valid": sig_valid, "signer_trust": trust, "artifact_count": len(artifact_by_id),
            "bundled_originals": len(included), "external_file_matches": checks,
            "all_external_matches": all(checks.values()),
            "warning": "Integrity verification is not a verdict on authorship, truth, or externally anchored time."}