# TraceProof product strategy — beyond accuracy claims

## Product thesis

The product is **not** an "all media, 99.9% accurate" classifier. It is a falsifiable evidence graph that distinguishes verifiable byte integrity, provenance attestations, contextual observations, and unavailable evidence. The differentiation is from reusable verification and well-described uncertainty, not a novel detector score.

## Historical foundation: v0.3 (delivered)
- Browser-side SHA-256 with no content upload to cloud.
- Event-sourced case and independently replayed audit ledger.
- Portable verifiable ProofBundle with opt-in original attachments and Ed25519 signatures.
- Counter-evidence and missing-evidence agenda.
- CLI and local UI, EN/TR/ES.
- Legacy TraceProof v0.2 JSON report hash-attachment (not original report analysis).

## Current: v0.11.1 (Windows preview)
- Downloadable unsigned Windows executable with local browser workspace and automated GUI-route startup checks.
- End-to-end 250 MB/video local chunked analysis, temporary staging, progress and cancellation.
- Comparison analysis uses SHA-256 byte matching plus conservative frame similarity evidence, not authorship probabilities.
- 104 automated unit/integration tests and synthetic FFmpeg regression suite (not a real-world accuracy benchmark).

## Next priorities
- Representative independent data set and well-labeled false-positive/false-negative evaluation.
- Native desktop shell, accessible user experience and code signing; FFmpeg installation assistance.
- Improve upload resumption, immediate cancel of FFmpeg and automatic cleanup of idle sessions.
- Reproducible packages, security audit, threat-model verification, multi-platform releases and internationalization coverage.

## Historical planning: v0.4 — model and provenance interoperability
- Integrate preexisting v0.2 C2PA verifier via explicit adapter with trust-list validation, test vectors and signed-manifest replay.
- Deterministic import adapters for open-source forensic tooling with provenance of each *tool version* and *verification operation*.
- Privacy-preserving text similarity and image perceptual similarity fingerprints explicitly labeled non-cryptographic.
- Robust multi-case relationship graph (original → excerpt → crop → repost), with fingerprints and false-match evaluation.
- Pluggable calibrated detectors for text, audio, video, images, software only with measurable out-of-distribution abstention.

## v0.5 — external trust and anti-fraud resilience
- Third-party timestamps and immutable transparency log integration with opt-in endpoints; key transparency and rotation.
- Hard attack benchmarks: metadata stripping, recompression, crop, deepfake re-generation, synthetic text editing, prompt attacks, poisoned metadata, adversarial data.
- Adversarial verifier fuzzing, ZIP-bomb and parser misuse testing, PDF/image format parser isolation.
- Self-serve reproducibility packages with reference assets and independent metric replication.

## Operational quality gates
- Cryptographic verifier test suite including forged, partially rewritten, and unsigned artifacts.
- Independent third-party C2PA conformance tests; never claim compatibility based on parser success alone.
- Recall, precision, specificity, expected calibration error, coverage-vs-risk curves by language/medium/model, including genuinely unseen models and lossy transformations.
- Accessibility, RTL support, localization coverage, mobile and browser coverage.
- Public security policy, threat model and coordinated disclosure.

## Known limitations of v0.3
- No proof of authorship, no trusted external clock, no C2PA verification *in this companion*, no AI detection training.
- The user-provided previous version is not automatically included; only its report hashes can be registered.
- The current UI verifies small ZIP bundles (up to 5 MB input); use CLI for larger artifacts.
- File type sniffing is contextual only and does not parse full media structures.

## v0.4 milestone 1 — local lineage comparison (implemented)
- `python -m traceproof compare left.txt right.txt` compares byte integrity and explainable normalized-text similarity.
- `python -m traceproof lineage-scan folder/` identifies exact and normalized-text duplicate groups in a local folder.
- No upload; no inferred authorship, chronological order, or image perceptual match.
- Similarity candidates are explicitly *not* independently verified provenance.

## Status at v0.11.0 (8 November 2026)

**Completed and available in the open-source preview:** event-chained evidence cases, portable bundles, local verification and optional key-based signing, text/image relationship candidates, chronological frame-sample video candidates, EN/TR/ES local interface, Windows portable EXE, local videos up to 250 MB transferred in bounded chunks, cancellation/status/cleanup, multi-Python CI and Windows binary smoke testing.

**v0.12 priorities (not implemented yet):**

1. **Real-world evaluation suite:** documented positive/negative fixtures spanning camera captures, re-encodes, crops, overlays, black frames, variable frame rates, audio-only sections and duration mismatches. Report false-positive/false-negative measurements per dataset, with no invented global accuracy percentage.
2. **Safer decode execution:** improved sandbox strategy for untrusted codecs, running-process cancellation that terminates FFmpeg promptly, explicit total-time limits, startup orphan-upload cleanup, disk quota monitoring and concurrency testing.
3. **User experience:** native-style Windows launcher and installer options, accessible progress/error states, 100% translation coverage, navigation and keyboard support, clearer distinction between byte-identical and candidate similarity.
4. **Trust and export:** combine video reports with ProofGraph as *observations* without converting heuristic matches into verified claims; reproducible signed release provenance and SBOM.
5. **Cross-platform delivery:** reproducible macOS/Linux builds and installer update strategy subject to code-signing access.

**Shipping gate:** test on real independent data and complete at least one external code/security review before making production or forensic-grade claims. Video comparison is investigative assistance, not authenticity certification or AI-content detection.
