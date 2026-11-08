# v0.7.0 — Local comparison workspace

- Added a bilingual/trilingual file comparison panel integrated into the existing web UI.
- Added `POST /api/compare` with strict 3 MB per-file limits, JSON payload validation and localhost-only origin checks.
- Refactored file comparison to support in-memory bytes, retaining the existing CLI and scan functionality.
- Added integration tests for the local HTTP comparison endpoint and text normalization.

## Limitations
- Browser comparisons transmit bytes to the loopback HTTP server, **not** to a cloud service. Other case artifacts continue to be hashed in the browser.
- Visual similarity requires the optional Pillow package; crop matches are heuristic and can produce false positives.
- This is a development preview, not a forensic certification or AI-authorship detector.