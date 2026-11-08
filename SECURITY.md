# Security considerations

## Threat model

This prototype can establish archive and event-chain self-consistency. Without an external trust anchor, an attacker can alter and recompute an **unsigned** chain. A bundle signed with a local Ed25519 key can verify a signature but does not prove the signer's legal identity. A bundle signed by an unknown key is still untrusted until a public key is obtained through a separately trusted channel.

No trusted capture time is claimed: `created_at_local_clock` is only a timestamp recorded by the computer's clock. Case creation is not evidence the file existed at that time. SHA-256 reveals exact byte matches, not authorship or semantic veracity.

The local web frontend hashes files using the browser WebCrypto API; source media never transits to the server. The loopback server refuses foreign host/origin requests and JSON uses a strict size cap. There is no authentication beyond loopback access; do not expose or reverse-proxy this prototype publicly.

The ZIP verifier rejects path traversal, unexpected entries, duplicate entry names, encrypted archives, symlink entries, excessive size and suspicious compression. Independent audits and fuzzing are still required before treating the verifier as security hardened. ZIP packages are read into memory; archive limits are defined in `bundle.py`.

Data entered in notes and filenames **is** embedded in the case/ZIP. Case exports need privacy review before sharing. Hashes may reveal membership in known-file datasets.

## Vulnerability reporting

Before production deployment: create a monitored security contact, report handling SLA and supported version policy. Do not publish unreviewed vulnerability proof-of-concepts with sensitive media attached.