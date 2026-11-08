"""Event-sourced cases and explicit epistemic limits. Python standard library only."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "traceproof.case.v3"
GENESIS = "0" * 64
KINDS = {"authorship", "integrity", "provenance", "context", "other"}
STATES = {"supports", "contradicts", "unknown"}
TRUST = {"cryptographic", "contextual", "unverified"}
ACTIONS = {"case_created", "artifact_added", "claim_added", "observation_added", "report_attached"}
ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class InvalidCase(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _string(value, field, limit=1000, nullable=False):
    if not isinstance(value, str) or (not nullable and not value.strip()) or len(value) > limit:
        raise InvalidCase(f"Invalid {field}")
    return value


def _identifier(value, field):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise InvalidCase(f"Invalid {field}")
    return value


def _sha(value, field):
    if not isinstance(value, str) or not HEX_RE.fullmatch(value):
        raise InvalidCase(f"Invalid {field}: expected lowercase sha256")
    return value


def _simple_obj(value, field):
    if not isinstance(value, dict):
        raise InvalidCase(f"Invalid {field}")
    if len(canonical(value)) > 48_000:
        raise InvalidCase(f"{field} exceeds 48 KB")
    return deepcopy(value)


def _apply(state, action, payload):
    if not isinstance(payload, dict):
        raise InvalidCase("Payload must be an object")
    state = deepcopy(state)
    if action == "case_created":
        if state:
            raise InvalidCase("Case already created")
        _string(payload.get("subject"), "subject", 500)
        if set(payload) != {"subject"}:
            raise InvalidCase("Unexpected case_created fields")
        return {"schema": SCHEMA, "subject": payload["subject"], "artifacts": [], "claims": [], "observations": [], "reports": []}
    if not state:
        raise InvalidCase("case_created must be first")
    if action == "artifact_added":
        if set(payload) != {"id", "name", "sha256", "size", "media_type"}:
            raise InvalidCase("Invalid artifact fields")
        _identifier(payload.get("id"), "artifact id")
        _string(payload.get("name"), "name", 500)
        _sha(payload.get("sha256"), "artifact sha256")
        if type(payload.get("size")) is not int or not 0 <= payload["size"] <= 2**63 - 1:
            raise InvalidCase("Invalid artifact size")
        _string(payload.get("media_type"), "media_type", 128)
        if any(a["id"] == payload["id"] for a in state["artifacts"]):
            raise InvalidCase("Duplicate artifact ID")
        state["artifacts"].append(deepcopy(payload))
    elif action == "claim_added":
        if set(payload) != {"id", "statement", "kind"}:
            raise InvalidCase("Invalid claim fields")
        _identifier(payload.get("id"), "claim id")
        _string(payload.get("statement"), "statement", 2000)
        if payload.get("kind") not in KINDS:
            raise InvalidCase("Invalid claim kind")
        if any(c["id"] == payload["id"] for c in state["claims"]):
            raise InvalidCase("Duplicate claim ID")
        state["claims"].append(deepcopy(payload))
    elif action == "observation_added":
        if set(payload) != {"id", "claim_id", "artifact_id", "source", "state", "trust", "details"}:
            raise InvalidCase("Invalid observation fields")
        _identifier(payload.get("id"), "observation id")
        if any(o["id"] == payload["id"] for o in state["observations"]):
            raise InvalidCase("Duplicate observation ID")
        if payload.get("claim_id") not in [c["id"] for c in state["claims"]]:
            raise InvalidCase("Unknown claim")
        if payload.get("artifact_id") is not None and payload["artifact_id"] not in [a["id"] for a in state["artifacts"]]:
            raise InvalidCase("Unknown artifact")
        _string(payload.get("source"), "source", 250)
        if payload.get("state") not in STATES or payload.get("trust") not in TRUST:
            raise InvalidCase("Invalid observation classification")
        _simple_obj(payload.get("details"), "details")
        # Never allow a user's assertion to mint cryptographic trust.
        if payload["trust"] == "cryptographic":
            raise InvalidCase("Cryptographic evidence cannot be self-asserted; use a verified primitive")
        state["observations"].append(deepcopy(payload))
    elif action == "report_attached":
        if set(payload) != {"id", "sha256", "name", "summary"}:
            raise InvalidCase("Invalid report fields")
        _identifier(payload.get("id"), "report id")
        _sha(payload.get("sha256"), "report sha256")
        _string(payload.get("name"), "report name", 500)
        _string(payload.get("summary"), "report summary", 1200)
        if any(r["id"] == payload["id"] for r in state["reports"]):
            raise InvalidCase("Duplicate report ID")
        state["reports"].append(deepcopy(payload))
    else:
        raise InvalidCase(f"Unrecognized action: {action}")
    return state


def event_digest(entry):
    return sha({k: entry[k] for k in ("seq", "previous", "time", "action", "payload")})


def append_event(case, action, payload, time=None):
    if action not in ACTIONS:
        raise InvalidCase("Unknown action")
    events = case.get("events", []) if case else []
    before = replay(events) if events else {}
    state = _apply(before, action, payload)
    entry = {"seq": len(events), "previous": events[-1]["hash"] if events else GENESIS,
             "time": time or utc_now(), "action": action, "payload": deepcopy(payload)}
    _string(entry["time"], "time", 64)
    entry["hash"] = event_digest(entry)
    out = {"format": SCHEMA, "events": deepcopy(events) + [entry], "state": state}
    if len(canonical(out)) > 5_000_000:
        raise InvalidCase("Case exceeds 5MB")
    return out


def new_case(subject):
    return append_event(None, "case_created", {"subject": subject})


def replay(events):
    if not isinstance(events, list) or not events or len(events) > 10000:
        raise InvalidCase("Case must contain 1 to 10000 events")
    state, prev = {}, GENESIS
    for index, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != {"seq", "previous", "time", "action", "payload", "hash"}:
            raise InvalidCase(f"Malformed event {index}")
        if type(event["seq"]) is not int or event["seq"] != index or event["previous"] != prev:
            raise InvalidCase(f"Broken chain at event {index}")
        _string(event["time"], "timestamp", 64)
        if event["action"] not in ACTIONS or not isinstance(event["payload"], dict):
            raise InvalidCase(f"Invalid event {index}")
        if event_digest(event) != event["hash"]:
            raise InvalidCase(f"Modified event {index}")
        state = _apply(state, event["action"], event["payload"])
        prev = event["hash"]
    return state


def validate_case(case):
    if not isinstance(case, dict) or set(case) != {"format", "events", "state"} or case.get("format") != SCHEMA:
        raise InvalidCase("Unknown case format")
    state = replay(case["events"])
    if canonical(state) != canonical(case["state"]):
        raise InvalidCase("Case snapshot does not match replayed ledger")
    return True


def evaluate(case):
    """Describe competing evidence; never turn metadata into AI-detection probabilities."""
    validate_case(case)
    s = case["state"]
    rows = []
    for claim in s["claims"]:
        obs = [o for o in s["observations"] if o["claim_id"] == claim["id"]]
        supporting = [o["id"] for o in obs if o["state"] == "supports"]
        opposing = [o["id"] for o in obs if o["state"] == "contradicts"]
        conflicted = bool(supporting and opposing)
        status = "contested" if conflicted else ("supported_contextually" if supporting else "challenged" if opposing else "unresolved")
        rows.append({"id": claim["id"], "statement": claim["statement"], "kind": claim["kind"],
                     "status": status, "supporting": supporting, "opposing": opposing,
                     "unknown": [o["id"] for o in obs if o["state"] == "unknown"],
                     "missing": _missing(claim, obs, s)})
    return {"schema": "traceproof.evaluation.v3", "case_chain_valid": True,
            "overall": "unresolved" if not rows or any(r["status"] in {"unresolved", "contested"} for r in rows) else "review_required",
            "claim_results": rows,
            "limitations": ["A file hash proves byte equality to a known reference, not the truth of its content.",
                            "Local timestamps are not independently trusted timestamps.",
                            "Missing provenance does not prove human or AI authorship.",
                            "Case event integrity without a trusted external signature is not proof of who made the case."]}


def _missing(claim, observations, s):
    todo = []
    if not observations or all(o["state"] == "unknown" for o in observations):
        todo.append("Collect an independent corroborating source or original file")
    if claim["kind"] in ("authorship", "provenance"):
        todo.append("Obtain origin records or a verifiable signed content credential")
    if claim["kind"] == "integrity":
        todo.append("Compare against a separately trusted baseline hash or signed original")
    if any(o["state"] == "supports" for o in observations) and any(o["state"] == "contradicts" for o in observations):
        todo.append("Resolve conflicting observations; do not average them into a score")
    if not s["artifacts"]:
        todo.append("Attach a locally hashed artifact")
    return todo


def describe_file(path, artifact_id):
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    digest = hashlib.sha256()
    size = 0
    with p.open("rb") as f:
        first = f.read(64)
        digest.update(first)
        size += len(first)
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    media = sniff_type(first)
    return {"id": _identifier(artifact_id, "artifact ID"), "name": p.name[:500],
            "sha256": digest.hexdigest(), "size": size, "media_type": media}


def sniff_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "audio/wav"
    if data.startswith(b"fLaC"):
        return "audio/flac"
    if data.startswith(b"OggS"):
        return "audio/ogg"
    if data[4:8] == b"ftyp":
        return "video/mp4-or-quicktime"
    if data.startswith(b"PK\x03\x04"):
        return "application/zip"
    if data.startswith(b"ID3") or (len(data) > 1 and data[0] == 255 and data[1] & 0xe0 == 0xe0):
        return "audio/mpeg"
    return "application/octet-stream"


def load_case(path):
    p = Path(path)
    if p.stat().st_size > 5_000_000:
        raise InvalidCase("Case file too large")
    obj = json.loads(p.read_text(encoding="utf-8"))
    validate_case(obj)
    return obj


def save_case(case, path):
    validate_case(case)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix(p.suffix + ".tmp")
    temp.write_bytes(json.dumps(case, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"))
    temp.replace(p)