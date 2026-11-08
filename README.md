# TraceProof — Evidence-first media analysis

**TraceProof v0.13.0 preview** · Python 3.10+ · MIT open source · English / Türkçe / Español.

TraceProof builds a reusable record of evidence, verifies hashes and signed bundles, and identifies *possible* similarities in text, images and videos. It is **not** an AI-authorship detector, proof of source identity or a certified forensic instrument.

## Run the Windows preview

The unsigned Windows preview is published under [GitHub Releases](https://github.com/atadam9594-arch/TraceProof/releases); select the latest verified release, download `TraceProof.exe` and compare its checksum to `TraceProof.exe.sha256`. It starts a local browser-based UI bound to `127.0.0.1`. Close the console to exit. SmartScreen may warn; there is no installer or code-signing certificate.

FFmpeg and ffprobe must be installed **separately** for video decoding. They are not bundled. Open `/setup` in TraceProof for local installation guidance. This page does not download or execute any installers.

## Run from source

```bash
git clone https://github.com/atadam9594-arch/TraceProof.git
cd TraceProof
python -m pip install -e ".[images,signing]"
python -m traceproof desktop
```

Other commands: `python -m traceproof serve` opens the fixed-port browser UI; `python -m traceproof doctor --check` verifies FFmpeg/ffprobe/Pillow. `--json` provides machine-readable results. Optionally set `TRACEPROOF_FFMPEG_DIR` to a directory containing trusted `ffmpeg` and `ffprobe` executables to avoid changing PATH, then restart TraceProof.

## Video Lab

Open `/video` to inspect two local MP4/MOV/MKV/WebM files, up to 250 MB each. Video files cross only from the browser to the same computer's loopback HTTP process using 1 MiB chunks and temporary storage, not to cloud servers. Video sample matches are heuristic; they do not establish originality, chronology, editing direction, falsehood or AI authorship. The CLI allows `video-compare`, `video-analyze` and offline HTML report export.

## Benchmark Lab and Dataset Audit

Open `/benchmark` to visualize JSON evaluation results from *user-labeled* video-pair manifests. The browser does not upload the JSON. Benchmark reports show dataset-specific confusion counts, group breakdowns and 95% Wilson intervals, which are not universal accuracy guarantees.

**New in v0.13:** a dataset auditor checks videos against curator-declared SHA-256 values and refuses incomplete coverage, mismatched files or unconfirmed usage rights. It does **not** verify licenses, consent, sources or ground-truth labels; those remain curator assertions. To use a custom licensed data collection:

```bash
python -m traceproof dataset-audit audit.json --root ./data --benchmark-manifest pairs.json --out audit-result.json
python -m traceproof video-benchmark pairs.json --root ./data --audit-dataset audit.json --samples 16 --out evaluation.json --html evaluation.html
```

See [Dataset Audit Guide](docs/VIDEO_DATASETS.md) and [Benchmark Guide](docs/BENCHMARK.md). No representative, independently validated third-party corpus is shipped or evaluated; synthetic tests cannot substantiate real-world accuracy.

## Reproducible tests

```bash
python -m unittest discover -s tests -q
python scripts/video_regression.py
python scripts/upload_regression.py
python scripts/benchmark_regression.py
python scripts/dataset_audit_regression.py
node --check traceproof/static/app.js
node --check traceproof/static/video.js
node --check traceproof/static/benchmark.js
node --check traceproof/static/setup.js
```

FFmpeg/ffprobe and Pillow are required for the video regressions. GitHub Actions tests Python 3.10–3.13; a Windows job creates and smoke-tests the `.exe` before publishing a versioned pre-release.

## Limits and open work

TraceProof is a research preview. Signed ProofBundle verification cannot by itself prove real-world identity or trusted timestamps. Unsigned event chains can be recreated by adversaries. Video decoders process untrusted inputs and have not been independently audited. Continue with [Security](SECURITY.md), [Roadmap](ROADMAP.md) and [Release Notes](RELEASE_NOTES.md).