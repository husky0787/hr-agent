import concurrent.futures
import json
import math
import threading

import pytest

from shared import rag


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    source = tmp_path / "seed"
    source.mkdir()
    monkeypatch.setattr(rag, "SEED_DATA_DIR", source)
    monkeypatch.setattr(rag, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(rag, "DOCUMENT_FILENAMES", frozenset({"policy.md", "security.md"}))
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "3")
    rag._queries.clear()
    calls = []
    lock = threading.Lock()
    def encode(texts, task):
        with lock:
            calls.append((texts, task))
        return [[1.0, 0.0, 0.0] for text in texts]
    monkeypatch.setattr(rag, "_encode", encode)
    return source, calls


def test_tasks_are_api_parameters_not_text_prefixes_and_query_cache_is_reused(corpus):
    source, calls = corpus
    text = "## Annual leave\nEmployees receive 25 days of paid leave."
    (source / "policy.md").write_text(text, encoding="utf-8")
    results = rag.search_handbook("每年有多少天年假？")
    assert results[0].content == text
    assert results[0].source == "policy.md"
    assert calls == [([text], "retrieval.passage"), (["每年有多少天年假？"], "retrieval.query")]
    rag.search_handbook("每年有多少天年假？")
    assert len(calls) == 2


def test_persistent_manifest_and_incremental_updates(corpus):
    source, calls = corpus
    (source / "policy.md").write_text("Leave policy", encoding="utf-8")
    (source / "security.md").write_text("Security policy", encoding="utf-8")
    first = rag.ensure_index()
    assert first.count() == 2
    assert rag.ensure_index().name == first.name
    assert len(calls) == 1
    (source / "policy.md").write_text("Updated leave", encoding="utf-8")
    second = rag.ensure_index()
    assert second.name != first.name
    assert calls[-1] == (["Updated leave"], "retrieval.passage")
    (source / "security.md").unlink()
    third = rag.ensure_index()
    assert third.count() == 1
    assert len(calls) == 2


def test_legacy_vectors_untouched_and_unlisted_files_not_indexed(corpus):
    source, _ = corpus
    client = rag._get_client()
    legacy = client.create_collection("hr_handbook_multilingual_e5_small_v1", embedding_function=None)
    legacy.add(ids=["legacy"], documents=["old"], embeddings=[[0.1, 0.2]])
    (source / "private.md").write_text("Private", encoding="utf-8")
    (source / "policy.md").write_text("Leave", encoding="utf-8")
    assert rag.ensure_index().get()["documents"] == ["Leave"]
    assert legacy.count() == 1


def test_failed_rebuild_leaves_previous_manifest_and_does_not_serve_stale_policy(corpus, monkeypatch):
    source, _ = corpus
    (source / "policy.md").write_text("Old leave", encoding="utf-8")
    rag.ensure_index()
    old = rag._read_manifest()
    (source / "policy.md").write_text("New leave", encoding="utf-8")
    def fail(*args):
        raise rag.EmbeddingError("offline")
    monkeypatch.setattr(rag, "_encode", fail)
    with pytest.raises(rag.EmbeddingError):
        rag.search_handbook("leave")
    assert rag._read_manifest() == old


def test_concurrent_first_build_is_deduplicated(corpus):
    source, calls = corpus
    (source / "policy.md").write_text("Annual leave", encoding="utf-8")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        names = list(executor.map(lambda _: rag.ensure_index().name, range(2)))
    assert names[0] == names[1]
    assert len(calls) == 1


def test_empty_headings_need_no_embedding(corpus):
    source, calls = corpus
    (source / "policy.md").write_text("# Policies\n\n## Leave", encoding="utf-8")
    assert rag.search_handbook("年假") == []
    assert calls == []


@pytest.mark.parametrize("vector", [[0, 0, 0], [1, 2], [math.nan, 0, 0], [math.inf, 0, 0], [True, 0, 0], "oops"])
def test_bad_vectors_rejected(vector):
    with pytest.raises(rag.EmbeddingError):
        rag._validate_vectors({"data": [{"index": 0, "embedding": vector}]}, 1, 3)


def test_out_of_order_vectors_sorted_and_normalized():
    vectors = rag._validate_vectors({"data": [{"index": 1, "embedding": [0, 2, 0]},
                                            {"index": 0, "embedding": [3, 0, 0]}]}, 2, 3)
    assert vectors == [[1, 0, 0], [0, 1, 0]]
    with pytest.raises(rag.EmbeddingError):
        rag._validate_vectors({"data": [{"index": 1, "embedding": [0, 2, 0]}]}, 1, 3)


def test_api_payload_and_invalid_credentials_no_retry(monkeypatch):
    import asyncio
    import httpx
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    original = httpx.AsyncClient
    calls = []
    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(401, json={"error": "never shown"})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    with pytest.raises(rag.EmbeddingError):
        asyncio.run(rag._embed_async(["年假"], "retrieval.query", {**rag._settings(), "dimensions": 3}))
    assert len(calls) == 1
    assert calls[0]["task"] == "retrieval.query"
    assert calls[0]["embedding_type"] == "float"


def test_transient_embedding_connection_is_retried_once(monkeypatch):
    import asyncio
    import httpx
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    original = httpx.AsyncClient
    calls = []
    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("temporary")
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1, 0, 0]}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    assert asyncio.run(rag._embed_async(["年假"], "retrieval.query", {**rag._settings(), "dimensions": 3})) == [[1, 0, 0]]
    assert len(calls) == 2
