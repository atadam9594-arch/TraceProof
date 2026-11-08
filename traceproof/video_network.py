"""Offline, bounded multi-video similarity graph.

Graph links are investigative candidates, not evidence of provenance, chronology,
authorship, authenticity, or edit direction. No source videos are exported.
"""
from __future__ import annotations

import hashlib
from html import escape
import json
import math
from pathlib import Path
import re
import time

from .benchmark import VIDEO_EXTENSIONS
from .video import fingerprint_video, compare_video_fingerprints

SCHEMA = 'traceproof.video.network.v1'
MAX_VIDEOS = 12
MAX_TOTAL_BYTES = 1_000_000_000
MAX_REPORT_BYTES = 1_000_000


def _safe_videos(directory: str | Path, limit: int):
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Video scan root must be an ordinary directory')
    files = sorted((p for p in root.iterdir()
                    if p.suffix.lower() in VIDEO_EXTENSIONS and p.is_file() and not p.is_symlink()),
                   key=lambda p: (p.name.casefold(), p.name))
    if not files:
        raise ValueError('Directory contains no supported video files')
    if len(files) > limit:
        raise ValueError(f'Directory contains {len(files)} videos; maximum permitted is {limit}. Use a smaller directory.')
    total = 0
    for p in files:
        size = p.stat().st_size
        if not 0 < size <= 250_000_000:
            raise ValueError('Videos must be nonempty and each at most 250 MB')
        total += size
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Combined video size exceeds 1 GB')
    return files, total


def _digest(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _components(ids, edges):
    parent = {ident: ident for ident in ids}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for edge in edges:
        a, b = find(edge['source']), find(edge['target'])
        if a != b:
            parent[max(a,b)] = min(a,b)
    clusters = {}
    for ident in ids:
        clusters.setdefault(find(ident), []).append(ident)
    return sorted((sorted(members) for members in clusters.values()), key=lambda members: members[0])


def scan_video_network(directory: str | Path, *, samples: int = 8,
                       max_videos: int = MAX_VIDEOS, fingerprinter=None):
    if type(samples) is not int or not 2 <= samples <= 16:
        raise ValueError('Samples must be an integer between 2 and 16')
    if type(max_videos) is not int or not 2 <= max_videos <= MAX_VIDEOS:
        raise ValueError('Maximum videos must be between 2 and 12')
    files, total_bytes = _safe_videos(directory, max_videos)
    if len(files) < 2:
        raise ValueError('Select at least two videos to build a relationship graph')
    start = time.monotonic()
    fp = fingerprinter or fingerprint_video
    nodes, edges = [], []
    sampled = {}
    errors = 0
    # Read/digest each file only locally. Successful and failed decodes are explicit.
    for idx, path in enumerate(files, start=1):
        ident = f'v{idx:03d}'
        node = {'id': ident, 'name': path.name, 'size_bytes': path.stat().st_size,
                'status': 'unresolved'}
        try:
            result = fp(str(path), samples=samples)
            if not isinstance(result, dict) or result.get('schema') != 'traceproof.video.v2':
                raise ValueError('Unexpected video fingerprint response')
            sha = result.get('sha256')
            if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
                raise ValueError('Missing video SHA-256')
            node['sha256'] = sha
            node['sampled_frames'] = len(result.get('sampled_frames', []))
            node['duration_seconds'] = result.get('duration_seconds')
            node['status'] = 'analyzed'
            sampled[ident] = result
        except (ValueError, RuntimeError, OSError, TypeError, KeyError):
            errors += 1
            node['status'] = 'decode_error'
            node['error_type'] = 'video_analysis_failed'
        nodes.append(node)
    for i, left in enumerate(nodes):
        if left['id'] not in sampled:
            continue
        for right in nodes[i+1:]:
            if right['id'] not in sampled:
                continue
            relation = compare_video_fingerprints(sampled[left['id']],sampled[right['id']])
            if relation['relation'] != 'unresolved':
                edges.append({
                    'source': left['id'], 'target': right['id'],
                    'relation': relation['relation'],
                    'informative_sample_matches': relation['informative_sample_matches'],
                    'sample_times': relation['matched_samples'][:16],
                })
    components = _components([node['id'] for node in nodes], edges)
    analyzed = len(sampled)
    pair_count = analyzed * (analyzed-1)//2
    return {
        'schema': SCHEMA,
        'summary': {
            'videos': len(nodes), 'analyzed': analyzed, 'decode_errors': errors,
            'pair_comparisons': pair_count, 'candidate_edges': len(edges),
            'byte_identical_edges': sum(x['relation'] == 'byte_identical' for x in edges),
            'similarity_edges': sum(x['relation'] == 'video_similarity_candidate' for x in edges),
            'unresolved_pairs': pair_count-len(edges),
            'connected_groups': len(components), 'total_input_bytes': total_bytes,
            'samples_per_video': samples, 'elapsed_seconds': round(time.monotonic()-start,3),
        },
        'nodes': nodes,
        'edges': edges,
        'groups': components,
        'limitations': [
            'Links are candidate relations, not provenance, edit direction, chronology, or AI authorship',
            'Unresolved does not prove that videos are unrelated; sparse sampling can miss edits',
            'Indirect graph connections do not imply pairwise similarity or common origin',
            'No validated false-positive rate or calibrated confidence is supplied',
            'Original media is not included; exported names and hashes may be sensitive',
        ],
    }


def validate_network_report(data: object):
    """Validate user-supplied network JSON before rendering offline HTML."""
    if not isinstance(data, dict) or data.get('schema') != SCHEMA:
        raise ValueError('Invalid video network report')
    nodes, edges = data.get('nodes'), data.get('edges')
    if not isinstance(nodes, list) or not 2 <= len(nodes) <= MAX_VIDEOS or not isinstance(edges, list) or len(edges) > 66:
        raise ValueError('Report exceeds video graph limits')
    ids = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError('Invalid video graph node')
        ident, name = node.get('id'), node.get('name')
        if not isinstance(ident,str) or not re.fullmatch(r'v\d{3}',ident) or ident in ids:
            raise ValueError('Invalid or duplicate video graph node id')
        if not isinstance(name,str) or not 1 <= len(name) <= 240:
            raise ValueError('Invalid video name')
        ids.add(ident)
    seen = set()
    for edge in edges:
        if not isinstance(edge,dict): raise ValueError('Invalid graph edge')
        a, b = edge.get('source'),edge.get('target')
        if a not in ids or b not in ids or a == b:
            raise ValueError('Invalid graph edge references')
        pair = tuple(sorted((a,b)))
        if pair in seen or edge.get('relation') not in ('byte_identical','video_similarity_candidate'):
            raise ValueError('Invalid or duplicated graph relation')
        seen.add(pair)
    return data


def render_network_report(data: dict):
    validate_network_report(data)
    nodes = data['nodes']; edges = data['edges']; n=len(nodes)
    positions = {node['id']: (500 + 365*math.cos(2*math.pi*i/n-math.pi/2),
                              430 + 310*math.sin(2*math.pi*i/n-math.pi/2))
                 for i,node in enumerate(nodes)}
    vectors = []
    for edge in edges:
        x1,y1=positions[edge['source']];x2,y2=positions[edge['target']]
        color = '#4ade80' if edge['relation']=='byte_identical' else '#fbbf24'
        vectors.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="3" opacity=".85"/>')
    for node in nodes:
        x,y=positions[node['id']]; label=escape(node['name'][:30]);ident=escape(node['id'])
        fill = '#395b68' if node.get('status') == 'decode_error' else '#195a81'
        vectors.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="33" fill="{fill}" stroke="#b1d6f2" stroke-width="2"/>')
        vectors.append(f'<text x="{x:.1f}" y="{y+5:.1f}" font-size="15" text-anchor="middle" fill="white">{ident}</text>')
        vectors.append(f'<text x="{x:.1f}" y="{y+52:.1f}" font-size="12" text-anchor="middle" fill="#e2e8f0">{label}</text>')
    s=data.get('summary',{})
    summary = ' · '.join(f'{escape(str(k))}: {escape(str(s.get(k,"—")))}' for k in ('videos','candidate_edges','byte_identical_edges','similarity_edges','unresolved_pairs','decode_errors'))
    rows = ''.join(f'<tr><td>{escape(e["source"])}</td><td>{escape(e["target"])}</td><td>{escape(e["relation"])}</td><td>{int(e.get("informative_sample_matches",0))}</td></tr>' for e in edges)
    if not rows:
        rows='<tr><td colspan="4">No candidate links detected. Unresolved does not mean unrelated.</td></tr>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TraceProof · Video Network</title><style>body{{background:#0a1425;color:#ecf1fb;font:16px system-ui;margin:32px auto;max-width:1120px;padding:0 15px}}h1{{color:#7bd1ff}}.meta{{color:#cbd5e1}}svg{{max-width:100%;height:auto;background:#0f2035;border:1px solid #304963;border-radius:14px}}table{{border-collapse:collapse;width:100%;margin-top:20px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #304963}}.note{{margin-top:24px;color:#d5dfeb}}</style></head><body><h1>TraceProof · Video Network</h1><p class="meta">{summary}</p><svg viewBox="0 0 1000 860" role="img" aria-label="Video candidate relationship graph">{''.join(vectors)}</svg><p class="meta">Green: exact SHA-256 match · Amber: heuristic video overlap · Missing link: unresolved</p><h2>Candidate links</h2><table><thead><tr><th>From</th><th>To</th><th>Relation</th><th>Matched samples</th></tr></thead><tbody>{rows}</tbody></table><p class="note">Similarity is not proof of provenance, chronology, modification or AI authorship. The dataset was not independently validated. No original videos are embedded in this report.</p></body></html>'''


def save_network_report(data, path):
    html = render_network_report(data)
    Path(path).write_text(html, encoding='utf-8')
    return Path(path)