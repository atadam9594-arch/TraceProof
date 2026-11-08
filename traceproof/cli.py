"""Offline-first TraceProof command-line tool."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .core import append_event, describe_file, evaluate, load_case, new_case, save_case, InvalidCase
from .bundle import create_keypair, make_bundle, verify_bundle
from .lineage import compare, scan


def _mapping(items):
    out = {}
    for item in items or []:
        if "=" not in item:
            raise InvalidCase("Expected ID=PATH")
        k, v = item.split("=", 1)
        if not k or not v or k in out:
            raise InvalidCase("Invalid or duplicated ID=PATH")
        out[k] = v
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="traceproof", description="Evidence-first, no fake AI detection percentage")
    sub = p.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("new"); x.add_argument("--subject", required=True); x.add_argument("--out", required=True)
    x = sub.add_parser("add-file"); x.add_argument("--case", required=True); x.add_argument("--file", required=True); x.add_argument("--id", required=True)
    x = sub.add_parser("add-claim"); x.add_argument("--case", required=True); x.add_argument("--id", required=True); x.add_argument("--statement", required=True); x.add_argument("--kind", choices=["authorship","integrity","provenance","context","other"], default="other")
    x = sub.add_parser("observe"); x.add_argument("--case", required=True); x.add_argument("--id", required=True); x.add_argument("--claim", required=True); x.add_argument("--artifact"); x.add_argument("--source", required=True); x.add_argument("--state", choices=["supports","contradicts","unknown"], required=True); x.add_argument("--details", default="{}", help="JSON object")
    x = sub.add_parser("attach-report"); x.add_argument("--case", required=True); x.add_argument("--id", required=True); x.add_argument("--report", required=True); x.add_argument("--summary", default="Legacy tool report; unverified by this module")
    x = sub.add_parser("evaluate"); x.add_argument("case")
    x = sub.add_parser("pack"); x.add_argument("case"); x.add_argument("--out", required=True); x.add_argument("--include-file", action="append", default=[], metavar="ID=PATH"); x.add_argument("--signing-key")
    x = sub.add_parser("verify"); x.add_argument("bundle"); x.add_argument("--trusted-key"); x.add_argument("--original", action="append", default=[], metavar="ID=PATH")
    x = sub.add_parser("keygen"); x.add_argument("--private", required=True); x.add_argument("--public", required=True)
    x = sub.add_parser("compare"); x.add_argument("left"); x.add_argument("right")
    x = sub.add_parser("lineage-scan"); x.add_argument("directory")
    x = sub.add_parser("video-analyze"); x.add_argument("video"); x.add_argument("--samples",type=int,default=12)
    x = sub.add_parser("video-compare"); x.add_argument("left"); x.add_argument("right"); x.add_argument("--samples",type=int,default=12); x.add_argument("--html")
    x = sub.add_parser("video-benchmark"); x.add_argument("manifest"); x.add_argument("--root"); x.add_argument("--samples", type=int, default=12); x.add_argument("--out"); x.add_argument("--html"); x.add_argument("--no-cache",action="store_true"); x.add_argument("--audit-dataset")
    x = sub.add_parser("dataset-audit"); x.add_argument("audit"); x.add_argument("--root"); x.add_argument("--benchmark-manifest"); x.add_argument("--out")
    x = sub.add_parser("video-network"); x.add_argument("directory"); x.add_argument("--samples", type=int, default=8); x.add_argument("--max-videos", type=int, default=12); x.add_argument("--out"); x.add_argument("--html")
    x = sub.add_parser("ffmpeg-register"); x.add_argument("--dir", required=True)
    sub.add_parser("ffmpeg-forget")
    x = sub.add_parser("doctor"); x.add_argument("--json", action="store_true"); x.add_argument("--check", action="store_true")
    x = sub.add_parser("serve"); x.add_argument("--port", type=int, default=8765)
    sub.add_parser("desktop")
    args = p.parse_args(argv)
    try:
        if args.cmd == "new":
            save_case(new_case(args.subject), args.out)
        elif args.cmd in ("add-file", "add-claim", "observe", "attach-report"):
            case = load_case(args.case)
            if args.cmd == "add-file":
                case = append_event(case, "artifact_added", describe_file(args.file, args.id))
            elif args.cmd == "add-claim":
                case = append_event(case, "claim_added", {"id": args.id, "statement": args.statement, "kind": args.kind})
            elif args.cmd == "observe":
                case = append_event(case, "observation_added", {"id": args.id, "claim_id": args.claim, "artifact_id": args.artifact,
                    "source": args.source, "state": args.state, "trust": "contextual", "details": json.loads(args.details)})
            else:
                import hashlib
                data = Path(args.report).read_bytes()
                case = append_event(case, "report_attached", {"id": args.id, "sha256": hashlib.sha256(data).hexdigest(),
                    "name": Path(args.report).name, "summary": args.summary})
            save_case(case, args.case)
        elif args.cmd == "evaluate":
            print(json.dumps(evaluate(load_case(args.case)), ensure_ascii=False, indent=2))
        elif args.cmd == "pack":
            make_bundle(load_case(args.case), args.out, _mapping(args.include_file), args.signing_key)
            print(f"Bundle saved to {args.out}")
        elif args.cmd == "verify":
            result = verify_bundle(args.bundle, args.trusted_key, _mapping(args.original))
            print(json.dumps(result, indent=2))
            if not result["all_external_matches"]:
                return 2
        elif args.cmd == "keygen":
            print("Public key SHA256:", create_keypair(args.private, args.public))
        elif args.cmd == "compare":
            print(json.dumps(compare(args.left,args.right),ensure_ascii=False,indent=2))
        elif args.cmd == "lineage-scan":
            print(json.dumps(scan(args.directory),ensure_ascii=False,indent=2))
        elif args.cmd == "video-analyze":
            from .video import fingerprint_video
            print(json.dumps(fingerprint_video(args.video,args.samples),indent=2))
        elif args.cmd == "video-compare":
            from .video import compare_videos
            comparison=compare_videos(args.left,args.right,samples=args.samples)
            if args.html:
                from .report import write_video_report
                write_video_report(comparison,args.html)
            print(json.dumps(comparison,indent=2))
        elif args.cmd == "video-benchmark":
            from .benchmark import evaluate_manifest
            audit_info = None
            if args.audit_dataset:
                from .dataset import audit_dataset
                audit_info = audit_dataset(args.audit_dataset, root=args.root or Path(args.manifest).resolve().parent,
                                           benchmark_manifest=args.manifest)
                if not audit_info["ok"]:
                    print(json.dumps(audit_info, indent=2, ensure_ascii=False))
                    return 2
            result = evaluate_manifest(args.manifest, root=args.root, samples=args.samples, cache=not args.no_cache)
            if audit_info is not None:
                result["dataset_audit"] = {
                    "audit_manifest_sha256": audit_info["audit_manifest_sha256"],
                    "videos_checked": audit_info["videos_checked"],
                    "checks_passed": audit_info["ok"],
                    "rights_only_curator_asserted": True
                }
            if args.html:
                from .benchmark_report import write_benchmark_report
                write_benchmark_report(result,args.html)
            encoded = json.dumps(result, indent=2, ensure_ascii=False)
            if args.out:
                Path(args.out).write_text(encoded + "\n", encoding="utf-8")
            print(encoded)
        elif args.cmd == "dataset-audit":
            from .dataset import audit_dataset
            report = audit_dataset(args.audit, root=args.root, benchmark_manifest=args.benchmark_manifest)
            encoded = json.dumps(report, indent=2, ensure_ascii=False)
            if args.out:
                Path(args.out).write_text(encoded + "\n", encoding="utf-8")
            print(encoded)
            if not report["ok"]:
                return 2
        elif args.cmd == "video-network":
            from .video_network import scan_video_network, save_network_report
            graph = scan_video_network(args.directory, samples=args.samples, max_videos=args.max_videos)
            if args.out:
                Path(args.out).write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if args.html:
                save_network_report(graph, args.html)
            print(json.dumps(graph, indent=2, ensure_ascii=False))
        elif args.cmd == "ffmpeg-register":
            from .diagnostics import register_ffmpeg_directory
            print(json.dumps(register_ffmpeg_directory(args.dir), ensure_ascii=False, indent=2))
        elif args.cmd == "ffmpeg-forget":
            from .diagnostics import clear_ffmpeg_directory
            print(json.dumps(clear_ffmpeg_directory()))
        elif args.cmd == "doctor":
            from .diagnostics import diagnose, guidance
            info = diagnose()
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print("TraceProof video readiness:", "READY" if info["ready"] else "SETUP REQUIRED")
                for key, obj in info["components"].items():
                    print(" -", key + ":", "ready" if obj["ready"] else "missing or not usable", obj["version"] or "")
                if not info["ready"]:
                    for line in guidance(info["platform"]):
                        print(" -", line)
            if args.check and not info["ready"]:
                return 2
        elif args.cmd == "serve":
            from .server import serve
            serve(args.port)
        elif args.cmd == "desktop":
            from .desktop import launch
            return launch()
        return 0
    except (InvalidCase, ValueError, OSError, RuntimeError) as e:
        print("TraceProof error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())