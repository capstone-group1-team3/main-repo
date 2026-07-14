"""Create a local Docker Compose environment file without exposing secrets."""

from __future__ import annotations

import secrets
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".env.example"
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation",
        action="store_true",
        help="create .env.eval with isolated-evaluation metadata enabled",
    )
    args = parser.parse_args()
    target = ROOT / (".env.eval" if args.evaluation else ".env")
    if target.exists():
        print(f"{target.name} already exists; leaving it unchanged")
        return

    replacements = {
        "NEO4J_PASSWORD": secrets.token_urlsafe(24),
        "JWT_SECRET": secrets.token_urlsafe(48),
        "EVALUATION_METADATA_ENABLED": "true" if args.evaluation else "false",
    }
    output: list[str] = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        key, separator, _value = line.partition("=")
        if separator and key in replacements:
            output.append(f"{key}={replacements[key]}")
        else:
            output.append(line)

    target.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Created {target.name} with generated local credentials; values were not printed")


if __name__ == "__main__":
    main()
