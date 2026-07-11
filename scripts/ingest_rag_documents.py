"""
ingest_rag_documents.py — Phase 4 offline ingestion entrypoint.

Run once before serving, and again whenever a policy changes (only changed
sections are re-embedded). Use --full to force a complete rebuild.

Run:  python scripts/ingest_rag_documents.py
      python scripts/ingest_rag_documents.py --full
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.rag.ingestion_pipeline import ingest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", type=Path, default=None)
    parser.add_argument("--full", action="store_true", help="force full rebuild")
    args = parser.parse_args()

    stats = ingest(policies_dir=args.policies, full_rebuild=args.full)
    print("ingestion complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
