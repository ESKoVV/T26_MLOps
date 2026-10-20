from __future__ import annotations

import argparse
import json
from pathlib import Path

from mlops_flight_delay.api import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    schema = create_app().openapi()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OpenAPI сохранён: {args.output}")


if __name__ == "__main__":
    main()
