"""
rag/chunking.py — structure-aware chunking of the policy corpus.

Uses LlamaIndex's MarkdownNodeParser to split on headers, then packs into
~256-400 token chunks with ~40-60 token overlap. Each chunk carries:
  - a stable, deterministic node id  (filename::section::n)  -> section-level
    granularity means editing one section re-embeds only that section's chunks
  - metadata: source (filename), section (nearest header)

The deterministic id is what makes incremental re-ingestion work (Phase 4 pipeline).
"""
from __future__ import annotations

from pathlib import Path

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode


def load_policy_documents(policies_dir: Path) -> list[Document]:
    """One Document per policy file, tagged with its source filename."""
    docs: list[Document] = []
    for path in sorted(policies_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(Document(text=text, metadata={"source": path.name}))
    return docs


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 320,
    chunk_overlap: int = 50,
) -> list[BaseNode]:
    """Header-aware split, then token-size packing, with deterministic ids."""
    md_parser = MarkdownNodeParser()
    sentence_splitter = SentenceSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    section_nodes = md_parser.get_nodes_from_documents(docs)
    nodes = sentence_splitter.get_nodes_from_documents(
        [Document(text=n.get_content(), metadata=n.metadata) for n in section_nodes]
    )

    # deterministic ids: source::section::running-index-within-section
    counters: dict[tuple[str, str], int] = {}
    for node in nodes:
        source = node.metadata.get("source", "unknown")
        section = _nearest_header(node) or "body"
        key = (source, section)
        idx = counters.get(key, 0)
        counters[key] = idx + 1
        node.id_ = f"{source}::{_slug(section)}::{idx}"
        node.metadata["section"] = section
    return nodes


def _nearest_header(node: BaseNode) -> str | None:
    # MarkdownNodeParser stores header path in metadata keys like "Header_1" etc.
    for key in ("Header 3", "Header 2", "Header 1", "header_path"):
        if key in node.metadata and node.metadata[key]:
            return str(node.metadata[key])
    return None


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in text.lower()).strip("-")[:40]
