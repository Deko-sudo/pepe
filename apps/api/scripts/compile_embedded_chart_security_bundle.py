from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.embedded_chart_security_bundle import compile_security_bundle


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile the immutable embedded-chart security bundle.",
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    manifest = json.loads(arguments.manifest.read_text())
    if not isinstance(manifest, dict):
        raise ValueError("embedded-chart security manifest must be a JSON object")
    compile_security_bundle(manifest, arguments.output)


if __name__ == "__main__":
    main()
