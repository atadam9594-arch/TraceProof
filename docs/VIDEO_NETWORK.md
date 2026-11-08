# Video Network — local batch analysis (v0.14.0)

TraceProof analyzes up to **12 video files in a single local directory** and shows **candidate** graph links. This is a privacy-first research feature, **not** a chain-of-custody determination, content-authenticity certificate, AI-authorship judgment or independent forensic assessment.

## Run on Windows without Python

1. Download the unsigned Windows preview from the [v0.14.0 GitHub release](https://github.com/atadam9594-arch/TraceProof/releases/tag/v0.14.0). Verify the accompanying SHA-256 checksum. It is not code-signed; Windows SmartScreen may warn.
2. Download and extract trusted FFmpeg / ffprobe binaries **yourself**, preferably using links from the official [FFmpeg download page](https://ffmpeg.org/download.html). TraceProof does not download executable tools for you, and FFmpeg licensing depends on the distribution.
3. In PowerShell, point the app at the extracted `bin` folder. Only use a folder whose executables you trust, because registration runs them with `-version`:

```powershell
.\TraceProof.exe ffmpeg-register --dir "C:\Tools\ffmpeg\bin"
.\TraceProof.exe doctor --json
.\TraceProof.exe video-network "C:\Users\You\Videos\Research" --samples 8 --out network.json --html network.html
```

Double-click `TraceProof.exe` to open the standard localhost app. Open **Video Network** from its home page and import `network.json` to view the graph interactively in English, Turkish, or Spanish. Or open the generated **`network.html`** directly in any browser; this standalone HTML contains a static SVG and needs no scripts, network or access to the original videos.

The source-code command is `python -m traceproof video-network videos/ --samples 8 --out network.json --html network.html` (or `traceproof video-network …` when installed).

Remove the registered folder preference with `TraceProof.exe ffmpeg-forget`. The per-user preference contains an absolute tools path and is not shared with any cloud server. A temporary `TRACEPROOF_FFMPEG_DIR` environment override still works.

## Input limits

- Supported files: MP4, MOV, WebM, MKV; one non-recursive directory.
- **2–12 videos**, **2–16 frames/video**, no symlinked files, max **250 MB/file** and **1 GB combined**.
- The engine fingerprints each video once, then compares fingerprints in memory: at most **66 pair checks**.
- Failures are reported as `decode_error`; paths and subprocess logs are not exported. Unsupported or encrypted media may fail.
- JSON exports contain filenames, SHA-256, sample times, frame-match counts and relationship candidates. Filenames and hashes can reveal sensitive information; review before sharing.

## Graph legend and interpretation

- Green: exact byte match (matching whole-file SHA-256 and byte size).
- Amber: **heuristic candidate** video overlap inferred from at least two chronologically ordered, informative and visually diverse sampled frames.
- No edge: **unresolved**. Sparse samples can miss an edit; a false match is possible; absence of an edge does not show that the files are unrelated.
- Connected nodes do **not** demonstrate common authorship, original/repost direction or that *all* members are pairwise similar; a node may be indirectly connected.

The network scan does not compute statistical confidence, general accuracy, source identity, or any claim about AI generation. For experiments with labeled videos use the separate [Benchmark Lab](BENCHMARK.md) and [Dataset Audit](VIDEO_DATASETS.md), including permission and source restrictions.