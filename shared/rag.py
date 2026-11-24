"""API-only embeddings and an atomically published, content-addressed Chroma index."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import threading
import time
import uuid

from filelock import FileLock
import httpx

from shared.config import CHROMA_PATH, SEED_DATA_DIR, positive_int
from shared.documents import DOCUMENT_FILENAMES, DOCUMENT_TITLES
from shared.topics import Topic, detect_topics

logger = logging.getLogger(__name__)
_index_lock = threading.Lock()
_cache_lock = threading.Lock()
_queries: OrderedDict[tuple[str, str], list[float]] = OrderedDict()
_clients: dict[str, object] = {}
_client_lock = threading.Lock()


class EmbeddingError(Exception):
    """Safe retrieval error without upstream response bodies or credentials."""


@dataclass
class SearchResult:
    content: str
    source: str
    score: float


def _settings() -> dict:
    return {
        "provider": "jina",
        "base_url": (os.getenv("EMBEDDING_BASE_URL") or "https://api.jina.ai/v1").rstrip("/"),
        "model": os.getenv("EMBEDDING_MODEL") or "jina-embeddings-v4",
        "dimensions": positive_int("EMBEDDING_DIMENSIONS", 2048),
        "document_task": "retrieval.passage", "query_task": "retrieval.query",
        "normalization": "l2", "chunking": "headings-500-v2",
    }


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _validate_vectors(payload: dict, count: int, dimensions: int) -> list[list[float]]:
    try:
        rows = payload["data"]
        if not isinstance(rows, list) or len(rows) != count:
            raise ValueError
        if sorted(row["index"] for row in rows) != list(range(count)):
            raise ValueError
        vectors = []
        for row in sorted(rows, key=lambda row: row["index"]):
            vector = row["embedding"]
            if not isinstance(vector, list) or len(vector) != dimensions:
                raise ValueError
            if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in vector):
                raise ValueError
            norm = math.sqrt(sum(n * n for n in vector))
            if not norm or not math.isfinite(norm):
                raise ValueError
            vectors.append([n / norm for n in vector])
        return vectors
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise EmbeddingError("文件搜尋服務返回無效向量，請稍後再試。") from None


async def _embed_async(texts: list[str], task: str, settings: dict) -> list[list[float]]:
    key = os.getenv("EMBEDDING_API_KEY", "")
    if not key:
        raise EmbeddingError("文件搜尋尚未設定 API Key；你仍可直接閱讀文件。")
    budget = positive_int("EMBEDDING_TIMEOUT_SECONDS", 60)
    started = time.monotonic()
    body = {"model": settings["model"], "input": texts, "task": task,
            "dimensions": settings["dimensions"], "embedding_type": "float", "return_multivector": False}

    async def attempt():
        async with httpx.AsyncClient(timeout=httpx.Timeout(budget, connect=min(5, budget))) as client:
            for number in range(2):
                try:
                    response = await client.post(f"{settings['base_url']}/embeddings",
                        headers={"Authorization": f"Bearer {key}"}, json=body)
                except httpx.TransportError:
                    if number == 0:
                        await asyncio.sleep(1)
                        continue
                    raise
                if (response.status_code == 429 or response.status_code >= 500) and number == 0:
                    await asyncio.sleep(1)
                    continue
                if response.status_code >= 300:
                    logger.warning("embedding failed status=%s", response.status_code)
                    raise EmbeddingError("暫時未能搜尋文件，請稍後再試；你仍可直接閱讀原文。")
                try:
                    payload = response.json()
                except ValueError:
                    raise EmbeddingError("文件搜尋服務返回無效回覆。") from None
                vectors = _validate_vectors(payload, len(texts), settings["dimensions"])
                usage = payload.get("usage", {})
                logger.info("embedding task=%s count=%s seconds=%.2f tokens=%s", task, len(texts),
                            time.monotonic() - started, usage.get("total_tokens"))
                return vectors
        raise EmbeddingError("暫時未能搜尋文件。")

    try:
        return await asyncio.wait_for(attempt(), timeout=budget)
    except (httpx.TransportError, asyncio.TimeoutError):
        raise EmbeddingError("文件搜尋連線逾時，請稍後再試；你仍可直接閱讀原文。") from None


def _encode(texts: list[str], task: str) -> list[list[float]]:
    return asyncio.run(_embed_async(texts, task, _settings())) if texts else []


def _chunk_markdown(text: str, source: str, chunk_size: int = 500) -> list[dict]:
    chunks = []
    for section in re.split(r"\n(?=#{1,3}\s)", text):
        section = section.strip()
        if not any(line.strip() and not re.match(r"^#{1,6}\s", line) for line in section.splitlines()):
            continue
        heading = next((line.lstrip("# ") for line in section.splitlines() if line.startswith("#")), source)
        for offset in range(0, len(section), chunk_size):
            content = section[offset:offset + chunk_size].strip()
            if content:
                chunks.append({"id": _digest([source, heading, content]), "content": content,
                               "source": source, "heading": heading})
    return chunks


def _get_client():
    import chromadb
    from chromadb.config import Settings

    path = str(Path(CHROMA_PATH).resolve())
    with _client_lock:
        if path not in _clients:
            _clients[path] = chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))
        return _clients[path]


def _read_manifest() -> dict:
    try:
        return json.loads((Path(CHROMA_PATH) / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ensure_index():
    root = Path(CHROMA_PATH)
    root.mkdir(parents=True, exist_ok=True)
    with _index_lock, FileLock(str(root / "index.lock"), timeout=180):
        documents = {}
        seed = Path(SEED_DATA_DIR).resolve()
        for filename in sorted(DOCUMENT_FILENAMES):
            path = (seed / filename).resolve()
            if path.parent != seed:
                raise EmbeddingError("文件路徑不合法，暫時未能建立搜尋索引。")
            if path.is_file():
                documents[filename] = path.read_text(encoding="utf-8")
        settings = _settings()
        settings_id = _digest(settings)
        sources = {name: _digest(content) for name, content in documents.items()}
        fingerprint = _digest([settings_id, sources])
        client = _get_client()
        previous = _read_manifest()
        old = None
        if previous.get("collection"):
            try:
                old = client.get_collection(previous["collection"], embedding_function=None)
            except Exception:
                old = None
        if previous.get("fingerprint") == fingerprint and old is not None:
            return old
        rows = {row["id"]: row for name, text in documents.items() for row in _chunk_markdown(text, name)}
        reusable = {}
        if old is not None and previous.get("settings_id") == settings_id:
            data = old.get(include=["embeddings"])
            reusable = dict(zip(data["ids"], data["embeddings"]))
        pending = [row for ident, row in rows.items() if ident not in reusable]
        for offset in range(0, len(pending), 32):
            batch = pending[offset:offset + 32]
            vectors = _encode([row["content"] for row in batch], "retrieval.passage")
            reusable.update(zip([row["id"] for row in batch], vectors))
        name = f"hr_api_{fingerprint[:20]}_{uuid.uuid4().hex[:8]}"
        collection = client.create_collection(name, embedding_function=None, metadata={"hnsw:space": "cosine"})
        temporary = root / f"manifest-{uuid.uuid4().hex}.tmp"
        try:
            if rows:
                collection.add(ids=list(rows), documents=[row["content"] for row in rows.values()],
                    metadatas=[{"source": row["source"], "heading": row["heading"]} for row in rows.values()],
                    embeddings=[list(reusable[ident]) for ident in rows])
            manifest = {"fingerprint": fingerprint, "settings_id": settings_id, "settings": settings,
                        "sources": sources, "collection": name, "chunks": len(rows)}
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, root / "manifest.json")
        except Exception:
            client.delete_collection(name)
            raise
        finally:
            temporary.unlink(missing_ok=True)
        if old is not None and old.name.startswith("hr_api_"):
            client.delete_collection(old.name)
        return collection


def _query_vectors(queries: list[str]) -> list[list[float]]:
    settings_id = _digest(_settings())
    vectors = {}
    with _cache_lock:
        for query in queries:
            key = (settings_id, query)
            if key in _queries:
                vectors[query] = _queries[key]
                _queries.move_to_end(key)
    missing = list(dict.fromkeys(query for query in queries if query not in vectors))
    if missing:
        vectors.update(zip(missing, _encode(missing, "retrieval.query")))
        with _cache_lock:
            for query in missing:
                key = (settings_id, query)
                _queries[key] = vectors[query]
                _queries.move_to_end(key)
            while len(_queries) > 128:
                _queries.popitem(last=False)
    return [vectors[query] for query in queries]


def _search(vector: list[float], top_k: int, topic: Topic | None = None) -> list[SearchResult]:
    with _index_lock:
        current = _read_manifest()
        collection = _get_client().get_collection(current["collection"], embedding_function=None)
        if not collection.count():
            return []
        scope = {"where": {"$and": [{"source": topic.source}, {"heading": topic.heading}]}} if topic else {}
        result = collection.query(query_embeddings=[vector], n_results=min(top_k, collection.count()), **scope)
    return [SearchResult(doc, meta["source"], 1.0 - distance)
            for doc, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])]


def search_handbook(query: str, top_k: int = 3) -> list[SearchResult]:
    if not ensure_index().count():
        return []
    return _search(_query_vectors([query])[0], top_k)


def search_documents(query: str, topics: list[Topic] | None = None) -> list[SearchResult]:
    """Cover each recognized topic before admitting extra chunks (six total)."""
    if topics is None:
        topics = detect_topics(query, SEED_DATA_DIR, sorted(DOCUMENT_FILENAMES))
    if len(topics) > 6:
        raise EmbeddingError("問題涉及較多主題，請每次查詢最多六項，讓答案涵蓋每一項。")
    if len(topics) < 2:
        return search_handbook(query)
    if not ensure_index().count():
        return []
    vectors = _query_vectors([topic.query for topic in topics])
    groups = [_search(vector, 2, topic) for topic, vector in zip(topics, vectors)]
    merged, seen = [], set()
    for rank in range(2):
        for group in groups:
            if rank < len(group):
                row = group[rank]
                key = (row.source, row.content)
                if key not in seen:
                    seen.add(key)
                    merged.append(row)
                    if len(merged) == 6:
                        return merged
    return merged


def format_search_results(results: list[SearchResult]) -> str:
    return "\n\n".join(f"[{i}] Source: {DOCUMENT_TITLES.get(row.source, row.source)}\n{row.content}" for i, row in enumerate(results, 1)) or "No relevant document extracts found."
