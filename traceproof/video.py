"""Bounded, offline video fingerprinting and conservative candidate matching.

Similarity signals are not evidence of provenance, AI authorship, or edit direction.
Video decoding requires FFmpeg; image fingerprints require Pillow.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess

from .lineage import image_hash, image_distance

MAX_VIDEO_BYTES = 250_000_000
MAX_DURATION = 3600
MAX_SAMPLES = 32
# Images with almost no texture or brightness variation are non-discriminative.
MIN_ENTROPY = 1.5
MIN_VISUAL_DIVERSITY = 10


def _run(argv, timeout=15):
    try:
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=True).stdout
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as exc:
        raise ValueError("Video decoder failed or exceeded resource limits") from exc


def _entropy(png):
    """Shannon entropy of a small grayscale thumbnail, in bits per pixel."""
    from PIL import Image, ImageOps
    with Image.open(BytesIO(png)) as img:
        gray = ImageOps.exif_transpose(img).convert("L")
        return round(gray.resize((64, 64), Image.Resampling.LANCZOS).entropy(), 3)


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint_video(path, samples=12):
    p = Path(path)
    if not p.is_file() or p.is_symlink() or not 0 < p.stat().st_size <= MAX_VIDEO_BYTES:
        raise ValueError("Invalid video or file exceeds 250 MB")
    if type(samples) is not int or not 1 <= samples <= MAX_SAMPLES:
        raise ValueError("Samples must be between 1 and 32")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are required for video analysis")

    metadata = json.loads(_run([
        "ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
        "-show_entries", "format=duration", "-of", "json", str(p)
    ], timeout=10))
    try:
        duration = float(metadata.get("format", {}).get("duration", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid video duration") from exc
    if not 0 < duration <= MAX_DURATION:
        raise ValueError("Video duration must be between 0 and 3600 seconds")

    frames = []
    for i in range(samples):
        second = round(duration * (i + .5) / samples, 3)
        png = _run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-protocol_whitelist", "file,pipe", "-ss", str(second), "-i", str(p),
            "-frames:v", "1", "-vf", "scale=160:90:force_original_aspect_ratio=decrease",
            "-f", "image2pipe", "-vcodec", "png", "pipe:1"
        ], timeout=12)
        digest = image_hash(png)
        if digest is not None:
            entropy = _entropy(png)
            frames.append({
                "second": second, "dhash": digest,
                "entropy": entropy, "informative": entropy >= MIN_ENTROPY
            })

    return {
        "schema": "traceproof.video.v2", "name": p.name,
        "sha256": _sha256(p), "size": p.stat().st_size,
        "duration_seconds": round(duration, 3),
        "sampled_frames": frames, "sampling": "uniform-midpoints",
        "limitations": [
            "Sparse sampling can miss edits",
            "Uniform / blank frames are ignored for similarity matching",
            "No inference of origin, chronology, AI authorship, or edit direction"
        ]
    }


def match_fingerprints(a, b, threshold=6):
    """Find one-to-one, chronologically ordered matches of informative frames.

    Restricts false positives from black frames and repetitive segments; it does
    not calibrate a probability or establish real-world authenticity.
    """
    if type(threshold) is not int or not 0 <= threshold <= 64:
        raise ValueError("Hamming threshold must be between 0 and 64")
    left = [f for f in a["sampled_frames"] if f.get("informative", True)]
    right = [f for f in b["sampled_frames"] if f.get("informative", True)]
    if not left or not right:
        return []

    # Objective: most pairs, then smallest total Hamming distance.
    @lru_cache(maxsize=None)
    def solve(i, j):
        if i == len(left) or j == len(right):
            return (0, 0, ())
        candidates = [solve(i + 1, j), solve(i, j + 1)]
        distance = image_distance(left[i]["dhash"], right[j]["dhash"])
        if distance <= threshold:
            n, negdist, pairs = solve(i + 1, j + 1)
            candidates.append((n + 1, negdist - distance, ((i, j, distance),) + pairs))
        return max(candidates, key=lambda choice: (choice[0], choice[1]))

    _, _, pairs = solve(0, 0)
    return [{
        "left_second": left[i]["second"],
        "right_second": right[j]["second"],
        "hamming_distance": d,
        "left_dhash": left[i]["dhash"],
        "right_dhash": right[j]["dhash"],
    } for i, j, d in pairs]


def _diverse(matches):
    hashes = [m["left_dhash"] for m in matches]
    return any(image_distance(x, y) >= MIN_VISUAL_DIVERSITY
               for i, x in enumerate(hashes) for y in hashes[i + 1:])


def compare_video_fingerprints(left, right, threshold=6):
    """Compare previously sampled fingerprints; safe to test without FFmpeg."""
    exact = bool(left.get("sha256") and left.get("sha256") == right.get("sha256")
                 and left.get("size") == right.get("size"))
    matches = match_fingerprints(left, right, threshold)
    candidate = len(matches) >= 2 and _diverse(matches)
    relation = ("byte_identical" if exact else
                "video_similarity_candidate" if candidate else "unresolved")
    public_matches = [{k: m[k] for k in ("left_second", "right_second", "hamming_distance")}
                      for m in matches]
    return {
        "schema": "traceproof.video.compare.v2",
        "left": left, "right": right,
        "matched_samples": public_matches,
        "informative_sample_matches": len(public_matches),
        "relation": relation,
        "match_policy": "ordered_unique_pairs_two_distinct_informative_frames",
        "warning": "Similarity is a heuristic, not proof of provenance, editing direction, chronology, or AI authorship."
    }


def compare_videos(left, right, threshold=6, samples=12):
    a = fingerprint_video(left, samples=samples)
    b = fingerprint_video(right, samples=samples)
    return compare_video_fingerprints(a, b, threshold=threshold)