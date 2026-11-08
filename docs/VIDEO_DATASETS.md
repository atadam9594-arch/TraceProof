# Preparing an auditable TraceProof video benchmark

This is a reproducible **integrity and disclosure** workflow. It cannot certify
copyright, consent, origin, ground-truth labels or the safety of third-party videos.
Do not download, distribute or process media unless permitted by applicable law
and the dataset license. Do not use sensitive media without an appropriate basis.

## 1. Source, label and split a licensed dataset

Document the actual rights holder, a license compatible with video analysis and
publication of derivative results, source URLs, and the method for determining
whether pairs truly overlap. Avoid accidental leakage across train/validation/test:
clips cut from the same original should remain within the same partition.
Separate re-encodings, crops, overlays, still frames, blank screens, transcoded
formats, and genuinely unrelated videos. Include hard negatives: videos showing
common scenes, logos, intros and stock backgrounds. Respect data subject consent.

TraceProof has **not** independently sourced a representative licensed dataset.
Please do not confuse the synthetic FFmpeg scenarios in tests with a validated
real-world accuracy benchmark.

## 2. Create a SHA-256 audit manifest

Save as `audit.json` beside the media. Use real local SHA-256 values instead of
zeros, and link to the actual source of each file. Every item declares licensing
and usage rights; these fields are *curator assertions* only.

```json
{
  "schema": "traceproof.dataset.audit.v1",
  "curator": "Name of dataset curator or institution",
  "label_method": "Human review, original edit chain, or independently known scene ID",
  "files": [
    {
      "path": "clips/source.mp4",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "license_spdx": "CC-BY-4.0",
      "source_url": "https://example.org/replace-with-original-source",
      "rights_confirmed": false
    }
  ]
}
```

The example is intentionally **not** valid as a trustworthy audit: the hash is
a placeholder and rights are unconfirmed. Never set `rights_confirmed: true`
unless you have actually checked permission; it still does not independently
validate the license.

## 3. Make your pair-label manifest

The v1 benchmark manifest contains `pairs` with `id`, `left`, `right`,
`expected_overlap: true/false`, and optional group names such as `reencode`,
`crop`, `unrelated`, `hard_negative`. Paths are relative to the dataset root.
Every referenced clip must appear in the audit manifest to pass coverage.

## 4. Verify, evaluate and report

```sh
python -m traceproof dataset-audit audit.json --root ./data --benchmark-manifest pairs.json --out audit-result.json
python -m traceproof video-benchmark pairs.json --root ./data --audit-dataset audit.json --samples 16 --out evaluation.json --html evaluation.html
```

`dataset-audit` exits with code 2 if a hash mismatch, missing file, incomplete
coverage or unconfirmed rights is found. `video-benchmark --audit-dataset` then
refuses to run if that audit fails and embeds the audit-manifest digest in the
result. Validation is performed **locally**, without checking external links.

Publish the benchmark's dataset version, manifest SHA-256, selection rules,
license conditions, label-review protocol, splits, test environments and failures.
Report per-group confusion counts, precision/recall/false-positive rate and
coverage. Wilson intervals in the UI assume independent samples; overlapping
pairs or repeated base videos violate that assumption and can make those
intervals misleadingly narrow.

**No dataset-wide result determines AI authorship or legal authenticity.**