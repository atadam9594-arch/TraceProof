# TraceProof — ProofGraph v0.8.0

**Evidence-first verification, not a magical AI-detector percentage.**

ProofGraph is an independently runnable **v0.8.0 companion module** for the earlier TraceProof AI v0.2.0 prototype. The earlier source ZIP was located but could not be materialized in this session, so v0.2's original C2PA/Ed25519/Smaug implementation has **not** been copied, modified, or retested. The companion runs on its own and can register v0.2 JSON reports by hash without pretending to have cryptographically re-verified them. It adds:

1. **Event-sourced ProofGraph.** Every case event hashes the previous event; replay independently checks the chain *and* reconstructs the case snapshot.
2. **Counter-evidence.** Each claim shows supporting observations, contradicting observations, and unanswered questions. Conflicting observations remain "contested" rather than being averaged into a confident-looking number.
3. **Portable ProofBundle.** A canonical case, calculated evaluation, digest manifest, optional included originals, and optional Ed25519 signature in one ZIP.
4. **Independent, offline verification.** No API key, account, external server, or proprietary runtime needed. A separate trusted key is required for verified signer identity. By default originals are *excluded*.
5. **Local-first multilingual interface.** English default; Turkish and Spanish selector. Hashing of source files happens in the user's browser; only the SHA-256, filename, sniffed file type, and size go to the loopback HTTP app. This local server binds to `127.0.0.1` only.
6. **Explicit epistemic limits.** A valid file hash does not establish that a claim is true, a valid signature does not establish real-world identity, and an unsigned event chain is recomputable by anyone. There is no AI-authorship detection model in this companion.

## Run (Python 3.10+)

```bash
git clone https://github.com/atadam9594-arch/TraceProof.git
cd TraceProof
python -m traceproof serve
```

Open `http://127.0.0.1:8765/` in your browser. Requires **no pip install** for ordinary case building and unsigned bundle verification. Files are *not uploaded* to an internet service.

To use optional Ed25519 signing:

```bash
python -m pip install cryptography
python -m traceproof keygen --private my-secret-key.pem --public my-public-key.pem
```

Keep the private key private. The local file's modification time is not proof of a trusted timestamp.

## CLI workflow

```bash
python -m traceproof new --subject "Was this supplied media modified?" --out case.json
python -m traceproof add-file --case case.json --file sample.png --id file1
python -m traceproof add-claim --case case.json --id claim1 --kind integrity --statement "Matches the separately trusted original"
python -m traceproof observe --case case.json --id obs1 --claim claim1 --artifact file1 --state unknown --source "Local inspection" --details '{"reason":"No independently trusted baseline"}'
python -m traceproof evaluate case.json
python -m traceproof pack case.json --out proof.zip
python -m traceproof verify proof.zip
```

If you explicitly wish to bundle an original or sign a bundle:

```bash
python -m traceproof pack case.json --out signed-proof.zip --include-file file1=sample.png --signing-key my-secret-key.pem
python -m traceproof verify signed-proof.zip --trusted-key my-public-key.pem --original file1=sample.png
```

To reference an earlier v0.2 JSON report, preserving its bytes by hash *without treating reported findings as independently validated*:

```bash
python -m traceproof attach-report --case case.json --id legacy1 --report old-report.json --summary "TraceProof AI v0.2 external assessment"
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Privacy and security

- Default exports contain hashes, filenames, case notes and the local timestamp. Even a cryptographic hash of a known work can disclose whether it was examined; review case notes before sharing.
- A signed bundle provides integrity tied to an Ed25519 *key*, not verified identity. Compare public keys through a **separately trusted** channel. Signing is optional; unsigned bundles can be rewritten and rehashed by an adversary.
- The built-in server keeps no case database and listens only on loopback. Case state is held in the page until explicitly downloaded; refreshing loses unsaved work.
- The "supports" or "contradicts" field is an **analyst observation**, not a model inference or cryptographic truth. The API prohibits users from declaring their own observations as cryptographically verified.
- A ProofBundle does not establish truth, media authorship, certified capture time, legal admissibility, or C2PA authenticity.

## Architecture

`traceproof/core.py`: canonical event chain, deterministic replay, evaluated claims, local hash utility.

`traceproof/bundle.py`: portable archive builder/verifier, Ed25519 signing and trusted-key verification.

`traceproof/server.py`: local stateless HTTP backend.

`traceproof/static/`: mobile-friendly EN/TR/ES UI.

`traceproof/cli.py`: CLI for reproducible headless use.

License: MIT. See ROADMAP.md and SECURITY.md.


## v0.5 image similarity (optional Pillow dependency)

Install `pip install Pillow` to enable 64-bit dHash comparison of PNG/JPEG/WebP/BMP/TIFF.
`python -m traceproof compare image1.png image2.jpg` reports an `image_similarity_candidate`
when Hamming distance is <=6. `python -m traceproof lineage-scan DIR` includes these candidate edges.
This is a **heuristic**, not proof of origin, editing direction, authorship, or authenticity.
Crop matching is heuristic and limited; it cannot reliably determine the editing direction or detect composites. Video frame sampling is available separately using FFmpeg.

## v0.8.0: local comparison, lineage and video sampling

- Compare two files: `python -m traceproof compare path/to/a path/to/b`.
- Scan a directory for candidate relationships: `python -m traceproof lineage-scan DIR`.
- Sample local video frames (requires FFmpeg and ffprobe on PATH): `python -m traceproof video-analyze video.mp4`.
- Compare candidate video frame overlaps: `python -m traceproof video-compare first.mp4 second.mp4`.
- Launch the English-first local UI (language selector includes Turkish and Spanish): `python -m traceproof serve`.
- For image comparison install `python -m pip install -e '.[images]'`; for signing use `python -m pip install -e '.[signing]'`.

Similarity candidates and sampled-frame matches **do not establish source, chronology, provenance, alteration or AI authorship**. These functions are investigative leads only. Optional dependencies, native installers, desktop packaging and independent benchmarks remain future work.

Current state: **public pre-release source**, not a certified forensic tool. The v0.2 AI-analysis prototype is **not** bundled in this repository.
