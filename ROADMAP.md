# Primary mission: AI-generated content detection

**User outcome:** Upload or select text, image, audio, video or software/document files and assess whether they were AI-generated, AI-assisted, or cannot be determined. Always expose evidence, limitations and uncertainty. The past v0.3–v0.14 evidence / media graph development is supporting infrastructure, **not the primary product**.

## Development direction (v0.15 and beyond)

1. **Provenance foundation (started):** interpret verified C2PA actions and optional origin-specific watermark APIs with explicit user consent. Signed claims must be validated against trustworthy certificate/issuer policy, not merely trusted because JSON says so. Missing signals always mean unknown, never human-created.
2. **Media-specific detection models:** image AI-generation detector(s), sampled-video/frame analyses, synthetic voice/audio detector(s), and text/structured file classifiers. Every model must disclose origin, license, version, supported languages/codecs, calibration set and conditions where it abstains.
3. **Controlled benchmarks:** human vs synthetic pairs from sources not used in training; model-family holdout; recompression, screenshots, crop, translation and paraphrase tests; stratified false-positive rates, uncertainty intervals and population drift tests.
4. **Honest multimodal synthesis:** separate strong signed provenance from fallible ML signals, never add independent-looking scores from correlated evidence, and offer *uncertain / insufficient evidence* as a first-class result.
5. **Unified UI:** select/upload artifact → modality identification → evidence provenance/model adapters → source-linked decision report → optional ProofBundle; default English with fully localized Turkish/Spanish views, opt-in cloud adapters only.
6. **Security and accessibility:** local-first runtime by default, trusted dependency provision, constrained file decoders, personal-data handling, code signing and independent audits.

**Do not promise 100% detection of every AI-generated item.** An unknown generator, new model, AI-edited human material, and stripped C2PA signatures create irreducible uncertainty.

---

# Current milestone: v0.14.0 (delivered)

- Local multi-video relationship network (2–12 videos), bounded resource usage, cached one-pass fingerprints, and exact/heuristic edge distinction.
- Script-free standalone SVG diagram, multilingual browser network JSON viewer, and synthetic FFmpeg end-to-end regression with negative controls.
- Per-user trusted FFmpeg directory registration available from the Windows `.exe`; no automatic downloads or silent code execution.

**Next high-value gates:** genuinely independent, licensed dataset labels and out-of-distribution evaluation; cross-platform signed native desktop installers; user-friendly trusted FFmpeg provisioning with licensing review; interruptible FFmpeg worker cancellation; explicit memory/disk and supply-chain security audit. Current tests do not establish real-world false-match rates.

---

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

## v0.13 milestone

- Local system diagnostics, portable FFmpeg binary discovery and multilingual Setup Lab.
- Dataset integrity manifest and a benchmark audit gate that requires exact hash matches and curator rights assertions.
- Synthetic regression exercises file tampering, but there is still no independently sourced representative licensed video corpus or external scientific validation.

## Next validation gates

- Independently documented, licensed and consent-aware real-world video pairs with disjoint source-level test splits.
- Field testing on multiple Windows configurations, accessible visual interface, installer signing and independent security assessment.
- Decoding cancellation improvements, bounded memory and automated FFmpeg license compliance guidance.