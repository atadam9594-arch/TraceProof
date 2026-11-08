# Reproducible video-overlap benchmarks (experimental, v0.12.0)

A verification tool should measure its failure cases instead of claiming a universal accuracy percentage. This optional module evaluates **user-labeled video pairs** with the existing TraceProof video comparison engine. Results apply **only to the submitted dataset**. They are not an AI-authorship, originality or forensic-certification score.

## Prepare a dataset

Put the source videos and a JSON manifest in one directory. Filenames in the manifest must be **relative POSIX-style paths** inside the dataset root, with supported video extensions `.mp4`, `.mov`, `.webm` or `.mkv`. Each pair can optionally include `"group": "transcode"`, `"group": "repost"`, or another short alphanumeric group name. Keep up to 100 labeled pairs; each video is subject to the existing 250 MB limit. The dataset can be mounted/read locally and is never uploaded to a cloud service.

```json
{
  "schema": "traceproof.benchmark.manifest.v1",
  "pairs": [
    {"id": "exact-reference", "left": "original.mp4", "right": "duplicate.mp4", "expected_overlap": true},
    {"id": "transcode", "left": "original.mp4", "right": "transcoded.mp4", "expected_overlap": true},
    {"id": "negative", "left": "original.mp4", "right": "unrelated.mp4", "expected_overlap": false}
  ]
}
```

`expected_overlap` is **manually curated ground truth** that the two videos share identifiable visual source content. It is *not* a label for AI generation, source identity or whether an edit is malicious. Document the labeler's instructions and adjudication policy separately before publishing a meaningful benchmark.

## Run locally

Install the optional Pillow package and FFmpeg/ffprobe on PATH. Then run:

```bash
python -m traceproof video-benchmark /path/to/dataset/manifest.json --samples 12 --out result.json --html report.html
```

Use `--root /path/to/dataset` if the manifest is not in the dataset directory. Raw video paths remain local; the result records pair IDs, labels, output relation, status, elapsed time, counts, rates and limitations. **It does not serialize source paths**.

The generated HTML report is self-contained, script-free and escapes user-controlled strings. You can also launch the local TraceProof application and visit **/benchmark** to open its JSON in a multilingual dashboard (English/Türkçe/Español). That visualization uses local browser file reads; no benchmark data or video bytes are uploaded to an internet service. Video filenames are deliberately absent from exported benchmark results; pair IDs and group names remain visible.

The built-in engine **fingerprints each unique video only once per run** and reuses the in-memory result across pairs. This eliminates redundant video decoding and does not persist any original media or fingerprints. The CLI flag `--no-cache` forces re-decoding for performance comparisons. External plugin comparators keep their own evaluation behavior.

The result now includes a per-group breakdown, number of unique video decodes and cache hits, and **95% Wilson score intervals** for the core rates. Wilson intervals describe uncertainty *conditional on independent, randomly sampled pairs and correct labels*. Correlated source clips, selection bias, small denominators and dataset shift are not captured. Undefined denominators remain `null`.

Metrics count `byte_identical` and `video_similarity_candidate` as a *candidate positive*, and `unresolved` as a *negative*. There is no probabilistic classifier score.

- True/false positive and true/false negative counts: only for pairs that could be evaluated.
- Precision: TP / (TP + FP); recall: TP / (TP + FN); false-positive rate: FP / (FP + TN); specificity: TN / (TN + FP).
- Accuracy: (TP + TN) / evaluated pairs; coverage: evaluated pairs / all labeled pairs.
- Undefined ratios are **null**, never zero or 100%. Decode errors appear as explicit errors and reduce coverage.

## Reproducibility and honest reporting

For group-specific evaluation, prefer at least tens or hundreds of independent examples per condition; report confidence intervals and use held-out datasets. Report: exact dataset version and file checksums, dataset source and license, labeling protocol, positive/negative sample counts, video format/resolution/duration distribution, operating system, Python/FFmpeg/Pillow versions, sampling budget, excluded/error pairs, and a held-out validation set. Avoid choosing thresholds on the evaluation set. Publish confidence intervals and per-condition breakdowns before comparing against other systems. **A three-case synthetic smoke test is not evidence of real-world accuracy.**

Run the synthetic FFmpeg benchmark with:

```bash
python scripts/benchmark_regression.py
```

The generated media is temporary and is removed after tests. Zero results and missing denominators are not masked.