# TraceProof v0.12.0 — Benchmark Lab and repeatable evaluation

- New browser-based **Benchmark Lab** for visualizing independently labeled video-pair results; English, Turkish and Spanish. Reads local JSON without sending it to any server.
- Reproducible command-line benchmarking now includes data-set-specific confidence intervals (95% Wilson), per-group confusion matrices and transparent error/coverage reporting.
- **Memoized video fingerprints** in a benchmark run; repeated source videos are decoded once per run rather than once per pair. `--no-cache` is available to compare workloads.
- New self-contained, escaped offline HTML report via `video-benchmark --html report.html` and optional result JSON output.
- Unit/integration tests for cache hits, cache-disabled mode, failed decodes, Wilson bounds, per-group metrics, malformed input, cross-site escaping and the HTML/JS/CSS routes.
- Release remains an **unsigned Windows research preview**, with FFmpeg and ffprobe supplied separately. No representative real-world validation set is included; **no accuracy percentage is claimed for production data**.

---

# TraceProof v0.10.0 — desktop preview and conservative video analysis

- Added a native-compatible launcher (`desktop_launcher.py`, `python -m traceproof desktop`) which opens the localhost workspace in the default browser. The server binds to a random free loopback port; no account or cloud deployment is required.
- Added GitHub Actions Windows executable build (`Build Windows desktop preview`), producing a downloadable `TraceProof-Windows-Preview` artifact after a successful Windows build. Windows executables are **unsigned preview builds**, not production-approved installers. FFmpeg remains a separate optional video analysis prerequisite.
- Strengthened video comparison: SHA-256 identifies byte-identical files; comparison of nonidentical files now uses only informative frames, aligns frame pairs in chronological order, prevents reuse of one frame as many matches, and requires at least two visually diverse matched frames for a similarity candidate.
- Reduced misleading matches from blank/low-detail frames. These methods are heuristic and need representative datasets before any accuracy claims.
- Added standalone, HTML-escaped offline video reports from CLI (`video-compare FIRST SECOND --html report.html`), with clear evidence limitations.
- Added repeatable synthetic FFmpeg regression scenarios, including reencoded videos and unrelated flat video.
- Added unit tests for algorithm safeguards, HTML escaping, and desktop launch path.

## Known limitations

- The browser Video Lab v0.9 endpoint still accepts short files only (2.5 MB per video); the CLI can analyze local files up to 250 MB.
- A Windows GitHub Actions build is an unsigned preview and may trigger Microsoft Defender SmartScreen. Inspect the source and build before running.
- PyInstaller packaging does not include FFmpeg/ffprobe. Install those tools separately to enable video analysis.
- No video similarity result establishes identity, chronology, authorship, editing direction or whether AI was involved.
- This release has not been independently audited or calibrated on a representative real-world video corpus.