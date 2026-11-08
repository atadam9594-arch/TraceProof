"""Dataset-scoped, reproducible evaluation of candidate video overlap.

This module NEVER validates ground-truth labels or claims general accuracy.
The built-in engine decodes each unique video once per evaluation, caching in
memory only; no fingerprints, paths or videos are persisted by this module.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from .video import compare_videos, fingerprint_video, compare_video_fingerprints

MANIFEST_SCHEMA = 'traceproof.benchmark.manifest.v1'
RESULT_SCHEMA = 'traceproof.benchmark.result.v1'
MAX_MANIFEST_BYTES = 1_000_000
MAX_PAIRS = 100
MAX_VIDEO_BYTES = 250_000_000
VALID_RELATIONS = {'byte_identical', 'video_similarity_candidate', 'unresolved'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv'}
ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{1,48}\Z')
# Two-sided 95% Wilson binomial interval, not a guarantee of generalization.
Z_95 = 1.959963984540054


def _rate(numerator: int, denominator: int):
    return round(numerator / denominator, 6) if denominator else None


def _wilson(successes: int, total: int):
    if not total:
        return None
    z2 = Z_95 ** 2
    mid = (successes + z2 / 2) / (total + z2)
    half = Z_95 * math.sqrt(successes * (total-successes) / total + z2 / 4) / (total + z2)
    return [round(max(0.0, mid-half), 6), round(min(1.0, mid+half), 6)]


def _relative_video(root: Path, name: object) -> Path:
    if not isinstance(name, str) or not name or len(name) > 240 or '\\' in name or ':' in name:
        raise ValueError('Video path must be a short, relative POSIX-style path')
    rel = Path(name)
    if rel.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Video path must stay under the declared dataset root')
    if rel.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError('Unsupported video file extension')
    candidate = root / rel
    if any(p.is_symlink() for p in (candidate, *candidate.parents) if p != root):
        raise ValueError('Symbolic links are not allowed in video paths')
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError('Missing video or path escapes dataset root') from exc
    if not resolved.is_file() or not 0 < resolved.stat().st_size <= MAX_VIDEO_BYTES:
        raise ValueError('Video must be nonempty and 250 MB or smaller')
    return resolved


def load_manifest(path: str | Path):
    manifest_path = Path(path)
    if not manifest_path.is_file() or manifest_path.is_symlink() or manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError('Manifest unavailable, symbolic link or exceeds 1 MB')
    try:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Manifest must be valid UTF-8 JSON') from exc
    if not isinstance(data, dict) or data.get('schema') != MANIFEST_SCHEMA:
        raise ValueError('Unsupported benchmark manifest schema')
    pairs = data.get('pairs')
    if not isinstance(pairs, list) or not 1 <= len(pairs) <= MAX_PAIRS:
        raise ValueError('Expected 1–100 benchmark pairs')
    seen = set()
    for pair in pairs:
        if not isinstance(pair, dict) or not set(pair) in ({'id','left','right','expected_overlap'},
                                                            {'id','left','right','expected_overlap','group'}):
            raise ValueError('Each pair needs id, left, right, expected_overlap and optional group')
        ident = pair['id']
        if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident) or ident in seen:
            raise ValueError('Invalid or duplicated pair id')
        seen.add(ident)
        if 'group' in pair and (not isinstance(pair['group'], str) or not ID_PATTERN.fullmatch(pair['group'])):
            raise ValueError('Group must be a short ASCII identifier')
        if type(pair['expected_overlap']) is not bool:
            raise ValueError('expected_overlap must be a boolean label')
        for side in ('left', 'right'):
            if not isinstance(pair[side], str):
                raise ValueError('Video paths must be strings')
    return data


def _summary(counts, total, elapsed_seconds=None):
    tp, fp, tn, fn, errors = (counts[k] for k in ('tp','fp','tn','fn','errors'))
    evaluated = tp+fp+tn+fn
    out = {
        'pairs':total, 'evaluated':evaluated, 'errors':errors,
        'true_positive':tp, 'false_positive':fp, 'true_negative':tn, 'false_negative':fn,
        'precision':_rate(tp,tp+fp), 'recall':_rate(tp,tp+fn),
        'false_positive_rate':_rate(fp,fp+tn), 'specificity':_rate(tn,tn+fp),
        'accuracy':_rate(tp+tn,evaluated), 'coverage':_rate(evaluated,total),
        'confidence_intervals_95':{
            'precision':_wilson(tp,tp+fp), 'recall':_wilson(tp,tp+fn),
            'false_positive_rate':_wilson(fp,fp+tn),
            'specificity':_wilson(tn,tn+fp),
            'accuracy':_wilson(tp+tn,evaluated),
            'coverage':_wilson(evaluated,total)
        }
    }
    if elapsed_seconds is not None:
        out['elapsed_seconds'] = round(elapsed_seconds,3)
    return out


def evaluate_manifest(manifest: str | Path, *, root: str | Path | None = None,
                      samples: int = 12, comparator=None, cache: bool = True,
                      fingerprinter=None):
    if type(samples) is not int or not 1 <= samples <= 32:
        raise ValueError('Samples must be an integer between 1 and 32')
    if type(cache) is not bool:
        raise ValueError('cache must be a boolean')
    manifest_input = Path(manifest)
    data = load_manifest(manifest_input)
    manifest_path = manifest_input.resolve(strict=True)
    dataset_root = Path(root).resolve(strict=True) if root is not None else manifest_path.parent
    if not dataset_root.is_dir():
        raise ValueError('Dataset root must be a directory')
    fingerprint = fingerprinter if fingerprinter is not None else fingerprint_video
    # Cache only when using built-in comparator; third-party engines may carry
    # state and are invoked pair-by-pair as before.
    fingerprints = {}
    cache_hits = decoded = 0
    counts = {'tp':0,'fp':0,'tn':0,'fn':0,'errors':0}
    per_group = {}
    records = []
    start = time.monotonic()

    def get_fp(path):
        nonlocal cache_hits,decoded
        key = str(path)
        if cache and key in fingerprints:
            cache_hits += 1
            value = fingerprints[key]
        else:
            try:
                value = fingerprint(str(path), samples=samples)
            except (ValueError, RuntimeError, OSError, TypeError) as exc:
                value = exc
            decoded += 1
            if cache:
                fingerprints[key] = value
        if isinstance(value, Exception):
            raise value
        return value

    for pair in data['pairs']:
        beginning = time.monotonic()
        group = pair.get('group','all')
        bucket = per_group.setdefault(group, {'tp':0,'fp':0,'tn':0,'fn':0,'errors':0,'total':0})
        bucket['total'] += 1
        record = {'id':pair['id'], 'group':group, 'expected_overlap':pair['expected_overlap']}
        try:
            left = _relative_video(dataset_root, pair['left'])
            right = _relative_video(dataset_root, pair['right'])
            if comparator is not None:
                result = comparator(str(left),str(right),samples=samples)
            else:
                left_fp = get_fp(left)
                right_fp = get_fp(right)
                result = compare_video_fingerprints(left_fp,right_fp)
            relation = result.get('relation') if isinstance(result,dict) else None
            if relation not in VALID_RELATIONS:
                raise ValueError('Unknown comparison result relation')
            predicted = relation != 'unresolved'
            record.update({'status':'evaluated','relation':relation,'predicted_overlap':predicted})
            name = ('tp' if pair['expected_overlap'] else 'fp') if predicted else ('fn' if pair['expected_overlap'] else 'tn')
            counts[name] += 1
            bucket[name] += 1
        except (ValueError, RuntimeError, OSError, TypeError):
            counts['errors'] += 1
            bucket['errors'] += 1
            # Do not leak filesystem paths or ffmpeg stderr into exported reports.
            record.update({'status':'error','error_type':'evaluation_failed'})
        record['elapsed_ms'] = round((time.monotonic() - beginning)*1000,1)
        records.append(record)
    summary = _summary(counts,len(records),time.monotonic()-start)
    summary['unique_decodes'] = decoded if comparator is None else None
    summary['fingerprint_cache_hits'] = cache_hits if comparator is None else None
    summary['cache_enabled'] = cache if comparator is None else False
    return {
        'schema':RESULT_SCHEMA, 'manifest_schema':MANIFEST_SCHEMA,
        'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        'samples':samples, 'summary':summary,
        'groups':{name:_summary(bucket,bucket['total']) for name,bucket in sorted(per_group.items())},
        'pairs':records,
        'limitations':[
            'Labels are supplied by dataset curator and are not independently verified',
            '95% Wilson intervals describe sampling variability under binomial assumptions, not domain-shift uncertainty',
            'Rates and confidence intervals apply only to this dataset; do not advertise them as universal accuracy',
            'Errors are excluded from confusion counts but reduce coverage',
            'Candidate overlap does not establish source, chronology, edit direction or AI authorship'
        ]
    }