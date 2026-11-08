# TraceProof — Evidence-first media analysis

[![Verify ProofGraph](https://github.com/atadam9594-arch/TraceProof/actions/workflows/tests.yml/badge.svg)](https://github.com/atadam9594-arch/TraceProof/actions/workflows/tests.yml)
[![Windows preview](https://github.com/atadam9594-arch/TraceProof/actions/workflows/windows-desktop.yml/badge.svg)](https://github.com/atadam9594-arch/TraceProof/actions/workflows/windows-desktop.yml)

**Latest preview: v0.11.0** · Python 3.10+ · MIT license · Offline-first · English / Türkçe / Español

TraceProof builds portable evidence records and discovers **candidate relationships** between local files and videos. It does not claim to determine whether a file is “real,” created by AI, authentic, original, or legally admissible. Exact hashes, heuristic similarity, and independently trusted attestations are distinct kinds of evidence.

## Download and launch

**Windows preview:** [TraceProof v0.11.0 — GitHub Releases](https://github.com/atadam9594-arch/TraceProof/releases/tag/v0.11.0)

Download `TraceProof.exe` and optionally check it against `TraceProof.exe.sha256`. Double-click the executable; it starts a **local-only** service and opens a browser tab. Close the console to stop it. The preview is **unsigned** and is not a Windows installer; SmartScreen warnings are possible. Video decoding requires **FFmpeg and ffprobe separately installed** and available on PATH. Pillow is included in the Windows build.

**Python install** on Windows, Linux, or macOS:

```bash
git clone https://github.com/atadam9594-arch/TraceProof.git
cd TraceProof
python -m pip install -e ".[images,signing]"
python -m traceproof desktop
```

Alternatively, `python -m traceproof serve` serves the workspace at `http://127.0.0.1:8765`. The application does **not** connect to a cloud analysis service.

## Capabilities

| Module | What it does | What it cannot establish |
| --- | --- | --- |
| ProofGraph | Local SHA-256 evidence registration, event-chain replay and conflicting claim observations | Whether a claim is factually true |
| ProofBundle | Export/verify ZIP evidence, optional Ed25519 signature and original-file inclusion | Identity of a signer without separately trusted keys; trusted time |
| File compare | Exact byte matches, normalized text and optional image perceptual hints | Source, authorship or editing direction |
| Relationship graph | Search for exact / similar relations in selected local files | Definitive provenance links |
| Video Lab | Compare two local MP4/MOV/MKV/WebM videos using bounded, sampled frame fingerprints | Forensic certification, AI authorship or edit detection |

**Video Lab v0.11.0** accepts up to **250 MB per file**, transferred to the server **on the same computer** in **1 MiB chunks** rather than loading whole videos into browser memory. Its progress percentage describes **local file transfer only**, not completion of video analysis. Jobs report analyzing/done/failed states; cancellation is supported. Source videos are staged in temporary storage and removed after the job ends or is cancelled. A single concurrent staging/analysis session is allowed. Session results expire after a period of inactivity. Availability checks report whether FFmpeg, ffprobe and Pillow are installed.

The similarity engine hashes entire files for `byte_identical`, filters low-information frames, and requires at least two informative and visually distinct matches in chronological order before reporting a `video_similarity_candidate`. This is an **uncalibrated heuristic**, not a statistical accuracy guarantee. Sparse sampling may miss changes and yield false matches. Some codecs/videos cannot be decoded.

## Command-line examples

```bash
# Evidence case and bundle
python -m traceproof new --subject "Was this file modified?" --out case.json
python -m traceproof add-file --case case.json --file example.png --id source1
python -m traceproof pack case.json --out proof.zip
python -m traceproof verify proof.zip

# Relationship inspection
python -m traceproof compare first.png second.jpg
python -m traceproof lineage-scan ./samples

# Video comparison and self-contained, escaped offline HTML report
python -m traceproof video-analyze clip.mp4 --samples 12
python -m traceproof video-compare clip1.mp4 clip2.mp4 --samples 16 --html comparison.html
```

Python CLI video analysis accepts videos up to 250 MB and at most 60 minutes (where decodable). Video sampling requires `ffmpeg`, `ffprobe`, and the `Pillow` Python library. HTML comparison reports are **not** signed ProofBundles. Optional signing uses Ed25519 via the `cryptography` extra; trusted signers must be independently verified.

## Security, privacy and limits

- The local HTTP listener binds to **127.0.0.1** and checks Host/Origin. Do not expose it through a public proxy, tunnel or untrusted local access.
- Video data crosses from your browser to a server **on your own computer**, not to an internet service. Original evidence files registered in ProofGraph are hashed inside the browser; this is a separate workflow.
- The video staging limit is 2 files × 250 MB and 1 active session. It may require up to roughly 500 MB of free temporary disk space plus decoder overhead. It is not designed for adversarial remote deployment.
- Case notes, filenames and hashes can be sensitive. Review exports before sharing. A hash can identify membership in known datasets.
- A valid unsigned event chain can be recreated by anybody. A valid signature without separately trusted key ownership does not prove real-world identity, evidence chronology or authenticity.
- This is a **pre-release research tool**; it has not passed independent forensic validation, representative false-match benchmarking, accessibility certification or an external security audit.

## Tests and development

```bash
python -m unittest discover -s tests -v
python scripts/video_regression.py      # requires FFmpeg + Pillow
python scripts/upload_regression.py     # requires FFmpeg + Pillow
node --check traceproof/static/app.js
node --check traceproof/static/video.js
```

GitHub Actions runs tests across Python 3.10–3.13. A separate Windows job builds the unsigned `TraceProof.exe`, starts it and checks localhost pages before publishing the preview.

See [release notes](RELEASE_NOTES.md), [roadmap](ROADMAP.md), [security notes](SECURITY.md) and [license](LICENSE). The older TraceProof AI v0.2 experiment is **not included** or cryptographically revalidated by this companion. Its external reports may only be registered as hashed references.
