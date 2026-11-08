# TraceProof v0.10.0 — Desktop preview and cautious video matching

- Windows executable preview automatically built by GitHub Actions, downloadable as `TraceProof-Windows-Preview` after successful builds. It opens the loopback-only web app in the user's default browser using an available dynamic port. It is unsigned and does not include FFmpeg.
- Python desktop launcher: `python -m traceproof desktop`.
- Video fingerprint engine v2: complete-file SHA-256, entropy filtering of low-detail frames, ordered one-to-one frame matching and minimum visually distinct frame evidence for candidate overlaps.
- Offline, escaped, no-script HTML comparison report: `video-compare LEFT RIGHT --samples 16 --html report.html`.
- Automated pure-Python unit tests, Windows build validation, and repeatable synthetic FFmpeg scenarios with re-encoding and negative control.
- **No accuracy percentage, authenticity claim, editing direction or AI-author decision is implied.** Only a preview; no independent security audit.

---

# v0.7.0 — Local comparison workspace

- Added a bilingual/trilingual file comparison panel integrated into the existing web UI.
- Added `POST /api/compare` with strict 3 MB per-file limits, JSON payload validation and localhost-only origin checks.
- Refactored file comparison to support in-memory bytes, retaining the existing CLI and scan functionality.
- Added integration tests for the local HTTP comparison endpoint and text normalization.

## Limitations
- Browser comparisons transmit bytes to the loopback HTTP server, **not** to a cloud service. Other case artifacts continue to be hashed in the browser.
- Visual similarity requires the optional Pillow package; crop matches are heuristic and can produce false positives.
- This is a development preview, not a forensic certification or AI-authorship detector.