"""Reproducible, dataset-scoped video-overlap evaluation.

Ground-truth labels are supplied by the dataset curator. This module does not
validate those labels and never represents dataset metrics as general accuracy.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from .video import compare_videos

MANIFEST_SCHEMA = 'traceproof.benchmark.manifest.v1'
RESULT_SCHEMA = 'traceproof.benchmark.result.v1'
MAX_MANIFEST_BYTES = 1_000_000
MAX_PAIRS = 100
MAX_VIDEO_BYTES = 250_000_000
VALID_RELATIONS = {'byte_identical', 'video_similarity_candidate', 'unresolved'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv'}


def _rate(numerator: int, denominator: int):
    return round(numerator / denominator, 6) if denominator else None


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
        if not isinstance(pair, dict) or set(pair) != {'id', 'left', 'right', 'expected_overlap'}:
            raise ValueError('Each pair requires id, left, right and expected_overlap')
        ident = pair['id']
        if not isinstance(ident, str) or not re.fullmatch('[A-Za-z0-9_-]{1,48}', ident) or ident in seen:
            raise ValueError('Invalid or duplicated pair id')
        seen.add(ident)
        if type(pair['expected_overlap']) is not bool:
            raise ValueError('expected_overlap must be a boolean label')
        for side in ('left', 'right'):
            if not isinstance(pair[side], str):
                raise ValueError('Video paths must be strings')
    return data


def evaluate_manifest(manifest: str | Path, *, root: str | Path | None = None,
                      samples: int = 12, comparator=None):
    if type(samples) is not int or not 1 <= samples <= 32:
        raise ValueError('Samples must be an integer between 1 and 32')
    manifest_input = Path(manifest)
    data = load_manifest(manifest_input)
    manifest_path = manifest_input.resolve(strict=True)
    dataset_root = Path(root).resolve(strict=True) if root is not None else manifest_path.parent
    if not dataset_root.is_dir():
        raise ValueError('Dataset root must be a directory')
    engine = comparator if comparator is not None else compare_videos
    records = []
    tp = fp = tn = fn = errors = 0
    start = time.monotonic()
    for pair in data['pairs']:
        beginning = time.monotonic()
        record = {'id': pair['id'], 'expected_overlap': pair['expected_overlap']}
        try:
            left = _relative_video(dataset_root, pair['left'])
            right = _relative_video(dataset_root, pair['right'])
            comparison = engine(str(left), str(right), samples=samples)
            relation = comparison.get('relation') if isinstance(comparison, dict) else None
            if relation not in VALID_RELATIONS:
                raise ValueError('Unknown comparison result relation')
            predicted = relation != 'unresolved'
            record.update({'status':'evaluated','relation':relation,'predicted_overlap':predicted})
            if predicted and pair['expected_overlap']: tp += 1
            elif predicted: fp += 1
            elif pair['expected_overlap']: fn += 1
            else: tn += 1
        except (ValueError, RuntimeError, OSError, TypeError) as exc:
            errors += 1
            # Do not leak absolute paths or FFmpeg stderr in public result reports.
            record.update({'status':'error','error_type':type(exc).__name__})
        record['elapsed_ms'] = round((time.monotonic() - beginning)*1000, 1)
        records.append(record)
    evaluated = tp + fp + tn + fn
    summary = {
        'pairs': len(records), 'evaluated':evaluated, 'errors':errors,
        'true_positive':tp, 'false_positive':fp, 'true_negative':tn, 'false_negative':fn,
        'precision':_rate(tp,tp+fp), 'recall':_rate(tp,tp+fn),
        'false_positive_rate':_rate(fp,fp+tn), 'specificity':_rate(tn,tn+fp),
        'accuracy':_rate(tp+tn,evaluated), 'coverage':_rate(evaluated,len(records)),
        'elapsed_seconds':round(time.monotonic()-start, 3)
    }
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return {'schema':RESULT_SCHEMA,'manifest_schema':MANIFEST_SCHEMA,
            'manifest_sha256':manifest_sha256, 'samples':samples,
            'summary':summary, 'pairs':records, 'limitations':[
                'Labels are supplied by the dataset curator and not independently verified',
                'Metrics describe only the submitted dataset; no universal accuracy is claimed',
                'Errors are excluded from the confusion matrix but reduce evaluation coverage',
                'Candidate overlap does not establish origin, chronology or AI authorship']}