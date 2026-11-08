# TraceProof v0.14.0 — Video Network and portable FFmpeg registration

- New offline `video-network` CLI analyzes 2–12 videos (up to 250 MB each / 1 GB combined), computing fingerprints once and producing candidate relationship links for up to 66 pairs. Failures, exact byte matches, unresolved pairs and connected groups are reported explicitly.
- New `--out network.json --html network.html` exports JSON and a **script-free, offline SVG/HTML relationship diagram** with HTML-escaped filenames and strict report validation. No original video is exported.
- New `/network` viewer renders saved JSON locally in English, Turkish and Spanish. No file is uploaded to the app server; browser DOM uses `textContent`, not untrusted HTML.
- Windows `TraceProof.exe` now supports selected offline CLI commands, including `ffmpeg-register --dir PATH` and `ffmpeg-forget`. Per-user configuration remembers the trusted FFmpeg directory without PATH edits, Python installation, or automatic executable downloads. Registration verifies tools by executing their `-version` commands. Use only trusted software.
- Added deterministic duplicate/similarity/negative/error tests and an FFmpeg-generated end-to-end video network regression with an unrelated-content negative control. GitHub verifies CLI commands and localhost pages in the packaged Windows executable.
- Scope remains **open-source research preview**, not forensic certification, source authentication, an AI detector, or a real-world benchmark accuracy guarantee. FFmpeg is not included in the binary; Windows builds are unsigned.

---

# TraceProof v0.13.0 — FFmpeg Setup Lab and Auditable Dataset Gate

- English/Turkish/Spanish Setup Lab at `/setup` checks ffmpeg/ffprobe execution and Pillow installation locally without network or automatic installation.
- `traceproof doctor [--json] [--check]` provides portable diagnostics; `TRACEPROOF_FFMPEG_DIR` supports trusted custom binary directories without PATH edits.
- Dataset Audit verifies declared file SHA-256 hashes, rejects symlinks and directory traversal, checks audit/benchmark pair coverage, and records curator-asserted licensing metadata. It does NOT verify actual rights, source URLs, consent or ground-truth quality.
- `video-benchmark --audit-dataset FILE` rejects failed audits and embeds the audit manifest digest in the output for traceability.
- New tests exercise missing FFmpeg, timeouts, localhost Setup page, integrity mismatches, incomplete pair coverage and the fail-closed benchmark gate. Synthetic end-to-end FFmpeg scenario verifies detection of file tampering.
- Windows executable is unsigned, and external FFmpeg is not bundled. No claim of certified forensic accuracy or AI authorship detection.

---

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