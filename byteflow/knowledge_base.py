"""
ByteFlow Knowledge Base
========================
Index local files and folders so ByteFlow can answer questions about them.

Supports: .txt, .md, .py, .js, .ts, .html, .css, .json, .csv, .pdf (text)

How it works:
  1. User adds files/folders to the KB
  2. Files are chunked and stored with metadata in knowledge_base.json
  3. On query, relevant chunks are found by keyword/similarity search
  4. Top chunks are injected into the agent prompt as context

Simple keyword search (no vector embeddings needed — works offline with Ollama).
"""

from __future__ import annotations
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict


KB_FILE = Path(__file__).parent.parent / "byteflow_kb.json"
SUPPORTED_EXTS = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                  ".json", ".csv", ".yaml", ".yml", ".toml", ".sh", ".bat",
                  ".rst", ".tex", ".xml", ".sql"}
CHUNK_SIZE = 800       # chars per chunk
CHUNK_OVERLAP = 100    # overlap between chunks
MAX_CHUNKS = 5000      # max total chunks in KB


@dataclass
class KBChunk:
    chunk_id: str
    source: str         # file path
    title: str          # file name
    content: str
    chunk_idx: int
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "KBChunk":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class KBSource:
    source_id: str
    path: str
    title: str
    chunk_count: int
    size_bytes: int
    indexed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    kind: str = "file"   # file | folder

    def to_dict(self) -> dict:
        return asdict(self)


class KnowledgeBase:
    """
    Local knowledge base: index files, search them, answer questions.
    """

    def __init__(self, path: Path = KB_FILE):
        self._path = path
        self._chunks: dict[str, KBChunk] = {}
        self._sources: dict[str, KBSource] = {}
        self._load()

    # ── Index ──────────────────────────────────────────────────────────────────

    def add_file(self, file_path: str) -> dict:
        """Index a single file."""
        path = Path(os.path.expanduser(file_path))
        if not path.exists():
            return {"ok": False, "error": f"File not found: {file_path}"}
        if not path.is_file():
            return {"ok": False, "error": f"Not a file: {file_path}"}
        if path.suffix.lower() not in SUPPORTED_EXTS:
            return {"ok": False, "error": f"Unsupported type: {path.suffix}. Supported: {', '.join(SUPPORTED_EXTS)}"}

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"ok": False, "error": f"Cannot read file: {e}"}

        source_id = str(path.resolve())
        # Remove old chunks from this source
        self._chunks = {cid: c for cid, c in self._chunks.items() if c.source != source_id}

        chunks = self._chunk_text(content, str(path), path.name, source_id)
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

        self._sources[source_id] = KBSource(
            source_id=source_id,
            path=str(path),
            title=path.name,
            chunk_count=len(chunks),
            size_bytes=path.stat().st_size,
        )

        self._trim()
        self._save()
        return {"ok": True, "source": path.name, "chunks": len(chunks), "source_id": source_id}

    def add_folder(self, folder_path: str, recursive: bool = True) -> dict:
        """Index all supported files in a folder."""
        folder = Path(os.path.expanduser(folder_path))
        if not folder.is_dir():
            return {"ok": False, "error": f"Not a folder: {folder_path}"}

        results = []
        pattern = "**/*" if recursive else "*"
        for file in folder.glob(pattern):
            if file.is_file() and file.suffix.lower() in SUPPORTED_EXTS:
                r = self.add_file(str(file))
                results.append(r)

        ok = [r for r in results if r.get("ok")]
        fail = [r for r in results if not r.get("ok")]
        return {
            "ok": True,
            "folder": str(folder),
            "indexed": len(ok),
            "failed": len(fail),
            "total_chunks": sum(r.get("chunks", 0) for r in ok),
        }

    def remove_source(self, source_id: str) -> dict:
        """Remove a source and all its chunks from the KB."""
        if source_id not in self._sources:
            return {"ok": False, "error": "Source not found"}
        name = self._sources[source_id].title
        del self._sources[source_id]
        self._chunks = {cid: c for cid, c in self._chunks.items() if c.source != source_id}
        self._save()
        return {"ok": True, "removed": name}

    def _chunk_text(self, text: str, source: str, title: str, source_id: str) -> list[KBChunk]:
        """Split text into overlapping chunks."""
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end]
            chunk_id = f"{source_id}_{idx}"
            chunks.append(KBChunk(
                chunk_id=chunk_id,
                source=source_id,
                title=title,
                content=chunk_text,
                chunk_idx=idx,
            ))
            start += CHUNK_SIZE - CHUNK_OVERLAP
            idx += 1
        return chunks

    # ── Search ─────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Keyword-based search across all chunks.
        Scores chunks by how many query words appear in them.
        """
        if not self._chunks:
            return []

        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []
        for chunk in self._chunks.values():
            content_lower = chunk.content.lower()
            # Count matching words + boost for consecutive phrase match
            word_hits = sum(1 for w in query_words if w in content_lower)
            phrase_hit = 3 if query.lower() in content_lower else 0
            score = word_hits + phrase_hit
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "source": c.title,
                "path": c.source,
                "chunk_idx": c.chunk_idx,
                "score": s,
                "content": c.content,
                "preview": c.content[:200] + "..." if len(c.content) > 200 else c.content,
            }
            for s, c in scored[:top_k]
        ]

    def get_context(self, query: str, top_k: int = 3) -> str:
        """
        Get relevant context for injecting into an AI prompt.
        Returns a formatted string with the most relevant chunks.
        """
        results = self.search(query, top_k)
        if not results:
            return ""
        parts = [f"[Knowledge Base Context]\n"]
        for i, r in enumerate(results, 1):
            parts.append(f"--- Source: {r['source']} (chunk {r['chunk_idx']}) ---\n{r['content']}\n")
        return "\n".join(parts)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def sources(self) -> list[dict]:
        return [s.to_dict() for s in self._sources.values()]

    def stats(self) -> dict:
        return {
            "total_sources": len(self._sources),
            "total_chunks": len(self._chunks),
            "supported_extensions": sorted(SUPPORTED_EXTS),
            "max_chunks": MAX_CHUNKS,
        }

    def clear(self) -> dict:
        self._chunks = {}
        self._sources = {}
        self._save()
        return {"ok": True, "message": "Knowledge base cleared"}

    # ── Persistence ────────────────────────────────────────────────────────────

    def _trim(self):
        if len(self._chunks) > MAX_CHUNKS:
            # Remove oldest chunks
            sorted_chunks = sorted(self._chunks.values(), key=lambda c: c.indexed_at)
            to_remove = sorted_chunks[:len(self._chunks) - MAX_CHUNKS]
            for c in to_remove:
                del self._chunks[c.chunk_id]

    def _save(self):
        data = {
            "sources": {sid: s.to_dict() for sid, s in self._sources.items()},
            "chunks": {cid: c.to_dict() for cid, c in self._chunks.items()},
        }
        try:
            tmp = Path(str(self._path) + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
        except Exception as e:
            print(f"[KnowledgeBase] Save failed: {e}")

    def _load(self):
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for sid, s in data.get("sources", {}).items():
                self._sources[sid] = KBSource(**s)
            for cid, c in data.get("chunks", {}).items():
                self._chunks[cid] = KBChunk.from_dict(c)
        except Exception as e:
            print(f"[KnowledgeBase] Load failed: {e}")


_kb: KnowledgeBase = None

def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
