# Demonstration

`demo-case.json` is a synthetic example investigation with **conflicting, human-supplied observations**. The SHA-256 is a placeholder and no source image is provided. Neither observation proves anything about the original media.

`demo-proofbundle.zip` is a genuine **unsigned** ProofBundle built from that synthetic case; it can be opened and independently verified with:

```bash
python -m traceproof verify examples/demo-proofbundle.zip
python -m traceproof evaluate examples/demo-case.json
```

The case evaluation will show `contested` and the archive verification will show `bundle_valid: true` **without** concluding that the image is genuine.