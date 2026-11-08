# Security considerations

## Threat model

This prototype can establish archive and event-chain self-consistency. Without an external trust anchor, an attacker can alter and recompute an **unsigned** chain. A bundle signed with a local Ed25519 key can verify a signature but does not prove the signer's legal identity. A bundle signed by an unknown key is still untrusted until a public key is obtained through a separately trusted channel.

No trusted capture time is claimed: `created_at_local_clock` is only a timestamp recorded by the computer's clock. Case creation is not evidence the file existed at that time. SHA-256 reveals exact byte matches, not authorship or semantic veracity.

The local web frontend hashes files using the browser WebCrypto API; source media never transits to the server. The loopback server refuses foreign host/origin requests and JSON uses a strict size cap. There is no authentication beyond loopback access; do not expose or reverse-proxy this prototype publicly.

The ZIP verifier rejects path traversal, unexpected entries, duplicate entry names, encrypted archives, symlink entries, excessive size and suspicious compression. Independent audits and fuzzing are still required before treating the verifier as security hardened. ZIP packages are read into memory; archive limits are defined in `bundle.py`.

Data entered in notes and filenames **is** embedded in the case/ZIP. Case exports need privacy review before sharing. Hashes may reveal membership in known-file datasets.

## Vulnerability reporting

Before production deployment: create a monitored security contact, report handling SLA and supported version policy. Do not publish unreviewed vulnerability proof-of-concepts with sensitive media attached.

## Setup Lab and Dataset Audit (v0.13)

The setup endpoint checks local executable readiness using argument-list subprocesses with strict timeouts. It does **not** install packages, read private configuration paths into the JSON report, or invoke a shell. It may execute `ffmpeg`/`ffprobe` found on PATH or explicitly selected using `TRACEPROOF_FFMPEG_DIR`; only point to trusted binaries. The separate official FFmpeg website link is user-initiated.

A dataset audit validates content hashes under a specified root, requires non-symlinked files and no path traversal, and stores curator-provided license/source/rights assertions. A hash verifies exact bytes, **not** permission, informed consent, lawful use, license validity, provenance or label accuracy. HTTPS source URLs are not fetched or verified. Do not interpret a passing audit as permission to distribute media.


## Video Network and FFmpeg CLI (v0.14.0)

- `video-network` is an explicit local CLI operation; it reads only supported video extensions from one non-recursive folder, rejects direct symlinks, and limits the input to 12 files, 250 MB/file, and 1 GB combined. FFmpeg still parses untrusted media, so a decoder vulnerability is not eliminated by these limits.
- Graph JSON exports contain only basenames, hashes and comparison signals, but hashes and basenames may still reveal private information. The standalone HTML report escapes input text and includes no `<script>` or remote resources.
- Browser graph import uses `File.text()` and DOM text nodes; the JSON does not travel to the local HTTP server. Saved graph files are not proof of the history of their inputs. The report has no digital signature.
- `ffmpeg-register` executes the selected local tools with `-version` and saves the chosen directory in a per-user local file, atomically with POSIX mode 0600. Registration is initiated explicitly by the user; only select executables from a separately trusted publisher. Preferences are not sent to any cloud service.
- No SHA-256-only match demonstrates a verified publisher, author, trusted capture time, legal custody, image authenticity or AI authorship; approximate links may be false positives or false negatives.

## AI-origin provenance adapter (development branch)

The experimental `ai-check` command does not run external tools or make network requests by default. Running `c2patool` requires the user's `--allow-external-provenance` flag; c2patool may fetch remotely hosted C2PA credentials. Do not use that option for confidential content without understanding remote retrieval implications. Imported JSON reports are not cryptographically tied to the submitted file and cannot establish its origin. A live C2PA signature status without independently trusted issuer validation is also not proof of real-world identity. No AI-detector scores are currently calibrated or offered by this adapter.
