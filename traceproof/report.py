"""Standalone, portable HTML presentation of video similarity evidence.

No JavaScript, active content, network resources, remote fonts or images.
Every untrusted field is escaped before insertion into the HTML document.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path


def render_video_report(data):
    """Render an analysis result as a neutral, offline HTML report."""
    if not isinstance(data, dict) or data.get("schema") != "traceproof.video.compare.v2":
        raise ValueError("Expected TraceProof video comparison v2")
    left, right = data["left"], data["right"]
    relation = data.get("relation", "unresolved")
    labels = {
        "byte_identical": "Byte-for-byte identical videos",
        "video_similarity_candidate": "Potential visual overlap (review required)",
        "unresolved": "No supported match established",
    }
    if relation not in labels:
        raise ValueError("Unknown comparison relation")
    rows = []
    for match in data.get("matched_samples", []):
        rows.append("<tr>" + "".join("<td>" + escape(str(match.get(k, ""))) + "</td>"
                    for k in ("left_second", "right_second", "hamming_distance")) + "</tr>")
    if not rows:
        rows.append('<tr><td colspan="3">No matched samples</td></tr>')
    def v(obj, key):
        return escape(str(obj.get(key, "unknown")))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>TraceProof · Video analysis report</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:850px;margin:2rem auto;padding:0 1rem;color:#17202a;background:#fafbfd}}h1{{letter-spacing:-.03em}}.tag{{font-size:.8rem;letter-spacing:.12em;color:#536779}}.box{{border:1px solid #d9e2e9;border-radius:12px;padding:1.25rem;margin:1rem 0;background:white}}table{{width:100%;border-collapse:collapse}}th,td{{padding:.6rem;text-align:left;border-bottom:1px solid #ddd}}th{{background:#edf1f5}}.caution{{border-left:4px solid #8f661b;padding:1rem;background:#fff7df}}code{{word-break:break-all}}</style>
</head><body><div class="tag">TRACEPROOF · OFFLINE ANALYSIS REPORT · v2</div>
<h1>Video comparison</h1><p class="caution"><strong>Evidence caveat:</strong> Sampled-frame matches are investigative hints only. They cannot establish authorship, authenticity, edit direction, manipulation, chronology, or AI-generated content. A missing match does not establish that videos are different.</p>
<section class="box"><h2>Result</h2><p><strong>{escape(labels[relation])}</strong></p><p>Algorithm: ordered unique informative frame matching · minimum two visually distinct matches for a similarity candidate.</p></section>
<section class="box"><h2>Compared videos</h2><p><strong>Left:</strong> {v(left, 'name')} · {v(left, 'duration_seconds')} s</p><p><strong>SHA-256:</strong> <code>{v(left,'sha256')}</code></p><p><strong>Right:</strong> {v(right, 'name')} · {v(right, 'duration_seconds')} s</p><p><strong>SHA-256:</strong> <code>{v(right,'sha256')}</code></p></section>
<section class="box"><h2>Candidate frame pairs</h2><table><thead><tr><th>Left (s)</th><th>Right (s)</th><th>Hamming distance</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
<section class="box"><h2>How to reproduce</h2><p>Use the source files with <code>python -m traceproof video-compare LEFT RIGHT</code>. FFmpeg and Pillow are required; frames are sampled at uniformly spaced midpoints.</p><p>Raw structured results should be retained alongside the original files. A standalone HTML report by itself is <strong>not a cryptographically signed ProofBundle</strong>.</p></section>
</body></html>'''


def write_video_report(data, path):
    target = Path(path)
    target.write_text(render_video_report(data), encoding="utf-8")
    return target