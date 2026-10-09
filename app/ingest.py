"""Load runbooks / past incidents and split them into retrievable chunks."""
import json
import re
from pathlib import Path

from langchain_core.documents import Document

SOURCES = (("runbook", "runbooks"), ("incident", "incidents"))


def chunk_text(text: str, max_chars: int = 700, overlap_blocks: int = 1) -> list[str]:
    """Paragraph-aware chunking with a small overlap of whole paragraphs."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for block in blocks:
        if current and size + len(block) > max_chars:
            chunks.append("\n\n".join(current))
            current = current[-overlap_blocks:] if overlap_blocks else []
            size = sum(len(b) for b in current)
        current.append(block)
        size += len(block)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_documents(data_dir: Path, max_chars: int = 700) -> list[Document]:
    docs: list[Document] = []
    for kind, sub in SOURCES:
        for path in sorted((Path(data_dir) / sub).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = _title(text, path.stem)
            for i, chunk in enumerate(chunk_text(text, max_chars)):
                content = chunk if i == 0 else f"{title}\n{chunk}"  # keep context in later chunks
                docs.append(
                    Document(
                        page_content=content,
                        metadata={"source": f"{sub}/{path.name}", "chunk": i, "kind": kind, "title": title},
                    )
                )
    return docs


def load_fixes(data_dir: Path) -> dict[str, dict]:
    """Approved fixes: the only actions the agent is ever allowed to propose."""
    items = json.loads((Path(data_dir) / "approved_fixes.json").read_text(encoding="utf-8"))
    return {item["id"]: item for item in items}
