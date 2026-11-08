# v0.12.0 state and upcoming work

**Delivered:** Data-set-scoped video overlap evaluation with in-memory reuse of per-video fingerprints, group metrics, Wilson confidence intervals, HTML report and multilingual local Benchmark Lab. Candidate relationships remain hypotheses, not provenance or AI-authorship decisions.

**Next:** (1) recruit properly licensed and independently labeled, diverse video benchmarks; (2) publish stratified false-positive/false-negative results with data limitations; (3) robust codec and FFmpeg installation UX with license compliance; (4) review resource limits and security threat model; (5) native signed installers, accessibility and internationalization audits.

---

# TraceProof product strategy — beyond accuracy claims

## Product thesis

The product is **not** an "all media, 99.9% accurate" classifier. It is a falsifiable evidence graph that distinguishes verifiable byte integrity, provenance attestations, contextual observations, and unavailable evidence. The differentiation is from reusable verification and well-described uncertainty, not a novel detector score.

## Current: v0.3 (delivered)
- Browser-side SHA-256 with no content upload to cloud.
- Event-sourced case and independently replayed audit ledger.
- Portable verifiable ProofBundle with opt-in original attachments and Ed25519 signatures.
- Counter-evidence and missing-evidence agenda.
- CLI and local UI, EN/TR/ES.
- Legacy TraceProof v0.2 JSON report hash-attachment (not original report analysis).

## Next: v0.4 — model and provenance interoperability
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