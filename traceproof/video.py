"""Bounded, offline video frame fingerprints; ffmpeg and ffprobe required."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from .lineage import image_hash, image_distance

MAX_VIDEO_BYTES = 250_000_000
MAX_DURATION = 3600
MAX_SAMPLES = 32

def _run(argv, timeout=15):
    try:
        return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=True).stdout
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as exc:
        raise ValueError("Video decoder failed or exceeded resource limits") from exc

def fingerprint_video(path, samples=12):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_VIDEO_BYTES:
        raise ValueError("Invalid video or file exceeds 250 MB")
    if not isinstance(samples,int) or not 1<=samples<=MAX_SAMPLES:
        raise ValueError("Samples must be between 1 and 32")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are required for video analysis")
    info=json.loads(_run(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","json",str(p)],timeout=10))
    duration=float(info.get("format",{}).get("duration",0))
    if not 0<duration<=MAX_DURATION:
        raise ValueError("Video duration must be between 0 and 3600 seconds")
    frames=[]
    for i in range(samples):
        second=round(duration*(i+.5)/samples,3)
        png=_run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
            "-i",str(p),"-ss",str(second),"-frames:v","1",
            "-vf","scale=160:90:force_original_aspect_ratio=decrease",
            "-f","image2pipe","-vcodec","png","pipe:1"],timeout=10)
        digest=image_hash(png)
        if digest:
            frames.append({"second":second,"dhash":digest})
    return {"schema":"traceproof.video.v1","name":p.name,"duration_seconds":round(duration,3),
            "sampled_frames":frames,"sampling":"uniform-midpoints",
            "limitations":["Sparse frames can miss edits","Perceptual similarity is not origin proof",
                           "No inference of chronology or edit direction"]}

def compare_videos(left,right,threshold=6,samples=12):
    a=fingerprint_video(left,samples=samples);b=fingerprint_video(right,samples=samples)
    matches=[]
    for x in a["sampled_frames"]:
        candidates=[(image_distance(x["dhash"],y["dhash"]),y)
                    for y in b["sampled_frames"]]
        if candidates:
            d,y=min(candidates,key=lambda t:t[0])
            if d<=threshold:
                matches.append({"left_second":x["second"],"right_second":y["second"],
                                "hamming_distance":d})
    return {"schema":"traceproof.video.compare.v1","left":a,"right":b,
            "matched_samples":matches,"relation":"video_similarity_candidate" if matches else "unresolved",
            "warning":"Sample matches are heuristic and do not prove origin, chronology, or manipulation."}