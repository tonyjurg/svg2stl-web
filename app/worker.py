"""One-shot conversion worker launched by the web process.

Running Gmsh in a child process gives every request fresh global state and lets
the web layer enforce a hard timeout by terminating the worker if necessary.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from app.converter import convert_svg_to_stl


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--thickness", required=True, type=float)
    parser.add_argument("--height", required=True, type=float)
    parser.add_argument("--border", required=True, type=float)
    parser.add_argument("--definition", required=True, type=int)
    parser.add_argument("--mode", choices=("stencil", "shape"), default="stencil")
    args = parser.parse_args(argv)

    try:
        report = convert_svg_to_stl(
            args.input,
            args.output,
            thickness_mm=args.thickness,
            height_mm=args.height,
            border_mm=args.border,
            definition=args.definition,
            output_mode=args.mode,
        )
    except Exception as error:  # The parent returns this as a safe user error.
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1

    print(json.dumps(asdict(report)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
