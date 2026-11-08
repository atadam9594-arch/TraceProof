# Security considerations

## Threat model

This prototype can establish archive and event-chain self-consistency. Without an external trust anchor, an attacker can alter and recompute an **unsigned** chain. A bundle signed with a local Ed25519 key can verify a signature but does not prove the signer's legal identity. A bundle signed by an unknown key is still untrusted until a public key is obtained through a separately trusted channel.

No trusted capture time is claimed: `created_at_local_clock` is only a timestamp recorded by the computer's clock. Case creation is not evidence the file existed at that time. SHA-256 reveals exact byte matches, not authorship or semantic veracity.

The case-building frontend hashes ordinary evidence files using browser WebCrypto; **Video Lab is different**: it transfers selected video bytes over loopback HTTP to the temporary storage of the local TraceProof process. Neither path uploads content to a cloud service. The loopback server refuses foreign host/origin requests and JSON uses a strict size cap. The upload endpoint uses unpredictable per-session tokens in addition to localhost host/origin controls, but there is no user authentication beyond access to the local process; do not expose or reverse-proxy this prototype publicly.

The ZIP verifier rejects path traversal, unexpected entries, duplicate entry names, encrypted archives, symlink entries, excessive size and suspicious compression. Independent audits and fuzzing are still required before treating the verifier as security hardened. ZIP packages are read into memory; archive limits are defined in `bundle.py`.

Data entered in notes and filenames **is** embedded in the case/ZIP. Case exports need privacy review before sharing. Hashes may reveal membership in known-file datasets.

## Video Lab transfer limits (v0.11.1)

- Only `127.0.0.1` is bound. The same-origin local server accepts a maximum of **one active comparison** with two declared files of up to 250,000,000 bytes each.
- HTTP file bodies are limited to 1,048,576 bytes per request and written sequentially to unpredictable temporary directories; no user-supplied filename is interpreted as a local filesystem path.
- Each comparison token is a random 192-bit value; chunks must match the expected side and offset. Missing chunks prevent decoding. Completed media is cleaned up. Canceled *running* decoders are allowed to finish before media removal, so cancellation is **not guaranteed to interrupt FFmpeg instantly**.
- Incomplete sessions expire after 30 minutes of inactivity **when a subsequent request causes cleanup**; temporary directories are also cleaned when the process exits normally. An unclean termination could leave operating-system temporary files and requires manual cleanup.
- External media decoders process untrusted local files. FFmpeg is invoked as a subprocess with explicit arguments, no shell, bounded sample count, timeouts and a restricted protocol whitelist. This is **not** a sandbox and decoding has not received an independent security audit.
- The local HTTP service does not provide multi-user authorization, quotas across separate processes or network isolation beyond its loopback binding. Do not put the server behind a public proxy.

## Vulnerability reporting

Before production deployment: create a monitored security contact, report handling SLA and supported version policy. Do not publish unreviewed vulnerability proof-of-concepts with sensitive media attached.