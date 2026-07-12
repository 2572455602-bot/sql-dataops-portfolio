"""Public command-line interface used by the Makefile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ecommerce_dataops.demo_data import generate_demo_dataset
from ecommerce_dataops.pipeline import run_pipeline
from ecommerce_dataops.settings import project_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Six-table e-commerce SparkSQL/DataOps pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Generate a deterministic six-table fixture and run the pipeline")
    demo.add_argument("--users", type=int, default=5000, help="Number of synthetic demo users")
    demo.add_argument("--no-publish", action="store_true", help=argparse.SUPPRESS)
    demo.add_argument("--runtime-root", type=Path, help=argparse.SUPPRESS)

    full = subparsers.add_parser("full", help="Run against an external six-table dataset directory")
    full.add_argument("--data-dir", type=Path, required=True, help="Absolute path containing the six contracted CSV files")
    full.add_argument("--no-publish", action="store_true", help=argparse.SUPPRESS)
    full.add_argument("--runtime-root", type=Path, help=argparse.SUPPRESS)
    return parser


def main() -> None:
    args = _parser().parse_args()
    root = project_root()
    try:
        if args.command == "demo":
            demo_root = args.runtime_root.resolve() if args.runtime_root is not None else root
            input_dir = demo_root / "data" / "demo" / "ecommerce"
            rows = generate_demo_dataset(input_dir, users=args.users)
            print(
                f"Generated deterministic DEMO DATA: {sum(rows.values()):,} rows "
                f"across six tables for {args.users:,} users"
            )
            mode = "demo"
        else:
            input_dir = args.data_dir
            mode = "portfolio"
        manifest = run_pipeline(
            root,
            input_dir,
            mode,
            runtime_root=args.runtime_root,
            publish=not args.no_publish,
        )
        print(json.dumps(manifest, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        print(f"Pipeline failed without publishing: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
