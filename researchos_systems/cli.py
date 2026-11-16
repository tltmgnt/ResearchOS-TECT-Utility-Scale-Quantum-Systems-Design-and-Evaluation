"""Reproducible quantum systems design and workflow evaluation CLI."""
import argparse
import sys
from pathlib import Path
from .records import read_json, sha, validate
from .model import analyze
from .workflow import report, run, verify_bundle, verify_evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "run", "verify", "report", "hash"):
        p = sub.add_parser(command)
        p.add_argument("path", type=Path)
        if command == "run":
            p.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "hash":
            print(sha(args.path.read_bytes()))
        elif args.command == "validate":
            r = validate(read_json(args.path))
            verify_evidence(r, args.path.parent)
            print("Record and evidence checksums valid; scientific claims are not assessed.")
        elif args.command == "run":
            run(args.path, args.output)
            print(f"Created systems-study bundle: {args.output}")
        elif args.command == "verify":
            verify_bundle(args.path)
            print("Bundle hashes and result/report/CSV reproduction verified; not an authenticity attestation.")
        else:
            verify_bundle(args.path)
            print(report(read_json(args.path / "record.json"), read_json(args.path / "results.json")), end="")
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
