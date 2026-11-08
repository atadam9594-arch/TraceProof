# TraceProof security and privacy notes

TraceProof is a **local-only, open-source preview**, not independently audited forensic software. Please do not deploy the built-in HTTP server to public interfaces or trust it with hostile input at network scale.

## Trust boundaries

**ProofGraph and ProofBundles.** SHA-256 proves exact byte equality with a separately obtained reference, not content truth or authorship. An unsigned event chain can be changed and recalculated by anyone. Ed25519 validates a signature relative to a public key; externally trusted key identity is a separate step. Local file times are not a certified timestamp.

**Browser-to-local-server transfer.** Case artifact hashing uses browser WebCrypto. Video Lab instead transfers actual video bytes over HTTP **to the same computer's 127.0.0.1 listener**, never to an internet analysis API. “Local-first” is not the same as “the video never leaves the browser process.” The server checks Host and Origin and does not bind public network interfaces. Other local processes and software with the ability to send localhost requests are outside the protection of those checks; there is no multi-user access-control system.

**Temporary media.** Video uploads use opaque 48-character hexadecimal session tokens, a single active session, maximum 250 MB per video, two sides, 1 MiB chunks, strict sequential offsets, bounded durations/sampling and a 30-minute inactivity timeout. Filenames are not used as filesystem paths. Files are staged in a temporary directory, removed after completion/failure or cancellation cleanup, and not archived automatically. A running decoder may finish before cancellation cleanup completes. Forced termination or a power failure may leave operating-system temporary files; manage local disk permissions and sensitive data accordingly.

**Resource exhaustion.** Large videos require local disk space (potentially 500 MB for two originals), CPU, memory and FFmpeg subprocess resources. The app limits file sizes and sample counts but cannot guarantee defense against crafted media or an overfull disk. Only open video files you trust sufficiently for your local environment; update FFmpeg and Pillow regularly.

**Local HTTP exposure.** The UI uses a loopback-only HTTP server, strict JSON and chunk-size limits, no cloud credentials, and response security headers. This preview is *not* authenticated against other local applications and is not suitable for reverse-proxy, tunnel or shared-host deployment. Do not expose TCP ports or run the app with administrator privileges.

## ProofBundle validation

The ZIP verifier rejects path traversal, duplicate names, encrypted archives, suspicious compression, unexpected entries and symlink-like metadata. Nevertheless, fuzzing, parser-hardening reviews and an independent security assessment remain outstanding.

## Safe sharing and limitations

Case notes, filenames, recorded observation details, local timestamps, hashes and relationship reports may reveal sensitive information. Review exports before sharing. Video perceptual hashes are not forensic proof; similarity does not establish origin, chronology, identity, editing direction or AI authorship. The HTML report is escaped and offline but not a signed ProofBundle.

## Reporting issues

Open a GitHub issue for non-sensitive bugs. **Do not post vulnerabilities with private evidence or personal media publicly.** For sensitive vulnerabilities, use GitHub's private vulnerability reporting feature if available, or request a private contact channel before sharing details. We have not committed to a production response SLA or security certification.
