from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from shared.config import CHROMA_PATH, DATA_DIR, SEED_DATA_DIR

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
# A new collection prevents reusing incompatible OpenAI/MiniLM vectors.
COLLECTION_NAME = "hr_handbook_multilingual_e5_small_v1"
_indexed = False


@dataclass
class SearchResult:
    content: str
    source: str
    score: float


def _chunk_markdown(text: str, source: str, chunk_size: int = 500) -> list[dict]:
    sections = re.split(r"\n(?=#{1,3}\s)", text)
    chunks: list[dict] = []
    for section in sections:
        section = section.strip()
        # A title with no policy text can outrank useful cross-language results.
        has_body = any(
            line.strip() and not re.match(r"^#{1,6}\s", line)
            for line in section.splitlines()
        )
        if not has_body:
            continue
        for i in range(0, len(section), chunk_size):
            chunk = section[i : i + chunk_size].strip()
            if chunk:
                chunks.append({"content": chunk, "source": source})
    return chunks


@lru_cache(maxsize=1)
def _embedding_model():
    return SentenceTransformer(
        EMBEDDING_MODEL,
        cache_folder=str(DATA_DIR / "models"),
        device="cpu",
    )


def _encode(texts: list[str], prefix: str) -> list[list[float]]:
    # E5 requires these English prefixes even for Chinese text.
    return _embedding_model().encode(
        [f"{prefix}: {text}" for text in texts],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()


def _get_client():
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def _get_collection():
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
        metadata={"hnsw:space": "cosine"},
    )


def ensure_index() -> None:
    global _indexed
    if _indexed:
        return

    collection = _get_collection()
    if collection.count() > 0:
        _indexed = True
        return

    all_chunks: list[dict] = []
    for path in sorted(SEED_DATA_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        all_chunks.extend(_chunk_markdown(text, path.name))

    if not all_chunks:
        _indexed = True
        return

    collection.upsert(
        ids=[f"chunk-{i}" for i in range(len(all_chunks))],
        embeddings=_encode([c["content"] for c in all_chunks], "passage"),
        documents=[c["content"] for c in all_chunks],
        metadatas=[{"source": c["source"]} for c in all_chunks],
    )
    _indexed = True


def search_handbook(query: str, top_k: int = 3) -> list[SearchResult]:
    ensure_index()
    collection = _get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(
        query_embeddings=_encode([query], "query"),
        n_results=min(top_k, collection.count()),
    )

    search_results: list[SearchResult] = []
    if not results["documents"] or not results["documents"][0]:
        return search_results

    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        search_results.append(
            SearchResult(
                content=doc,
                source=meta.get("source", "unknown"),
                score=1.0 - dist if dist is not None else 0.0,
            )
        )
    return search_results


def format_search_results(results: list[SearchResult]) -> str:
    if not results:
        return "No relevant handbook sections found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] Source: {r.source}\n{r.content}")
    return "\n\n".join(parts)
