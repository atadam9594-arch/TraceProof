# TraceProof v0.11.0 — Large-file local Video Lab

Released as an **unsigned Windows desktop preview** and open-source Python application.

## What changed

- Replaced the browser's old 2.5 MB base64 video submission path with a **bounded, streaming upload protocol** for up to **250 MB per video**, 1 MiB per chunk. Data goes to the loopback server on the same machine, not to a cloud service.
- New local upload sessions use unguessable tokens, declared file sizes, monotonically checked offsets, temporary storage and one active session at a time.
- Added local transfer progress, cancellation, status polling and cleanup when processing completes or fails. Progress does not estimate the duration of FFmpeg analysis.
- Added a local decoder dependency/capability endpoint and multilingual (English, Turkish, Spanish) status messages.
- Kept the older short-video comparison API only for backward compatibility; the UI uses streaming.
- Automated tests cover session validation, origin enforcement, chunk limits, cancellation, cleanup, missing tools, and complete >2.5 MB HTTP transfers. Tests also cover evidence/ProofBundle and image/text/video matching.
- Windows GitHub Actions creates a self-contained `TraceProof.exe`, smoke-tests localhost pages and publishes the pre-release with a SHA-256 checksum.

## Installation

Download the Windows executable and checksum from [v0.11.0 Releases](https://github.com/atadam9594-arch/TraceProof/releases/tag/v0.11.0). Alternatively install Python requirements and run `python -m traceproof desktop`. FFmpeg/ffprobe are not bundled with the Windows binary.

## Scope and cautions

The video feature compares candidate similarities only: it cannot prove media provenance, detect all modifications, or identify AI-generated content reliably. No real-world precision/recall percentage is claimed. Unsupported codecs, corrupt media, sparse sampling and misleading perceptual hashes remain limitations. The Windows preview is unsigned, not an installer or security-reviewed production release. Temporary media is stored only on the local machine and removed after session cleanup; case exports may contain sensitive notes and hashes.

---

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