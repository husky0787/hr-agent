import numpy as np
import pytest

from shared import rag


class RecordingEncoder:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return np.tile([1.0, 0.0, 0.0], (len(texts), 1))


@pytest.fixture
def isolated_rag(tmp_path, monkeypatch):
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    monkeypatch.setattr(rag, "SEED_DATA_DIR", seed_dir)
    monkeypatch.setattr(rag, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(rag, "_indexed", False)
    encoder = RecordingEncoder()
    monkeypatch.setattr(rag, "_embedding_model", lambda: encoder)
    return seed_dir, encoder


def test_prefixes_are_only_encoded_not_returned_in_citations(isolated_rag):
    seed_dir, encoder = isolated_rag
    document = "## Annual leave\nEmployees receive 25 days of paid leave."
    (seed_dir / "policy.md").write_text(document, encoding="utf-8")

    results = rag.search_handbook("每年有多少天年假？")

    assert len(results) == 1
    assert results[0].content == document
    assert results[0].source == "policy.md"
    assert results[0].score == pytest.approx(1.0)
    assert encoder.calls[0][0] == [f"passage: {document}"]
    assert encoder.calls[1][0] == ["query: 每年有多少天年假？"]
    assert all(kwargs["normalize_embeddings"] for _, kwargs in encoder.calls)
    assert "Source: policy.md" in rag.format_search_results(results)


def test_legacy_vectors_are_preserved_and_not_reused(isolated_rag):
    seed_dir, _ = isolated_rag
    legacy = rag._get_client().create_collection("hr_handbook", embedding_function=None)
    legacy.add(ids=["legacy"], documents=["Old policy"], embeddings=[[0.1, 0.2]])
    (seed_dir / "new.md").write_text("New handbook policy", encoding="utf-8")

    rag.ensure_index()

    assert legacy.count() == 1
    assert rag._get_collection().get()["documents"] == ["New handbook policy"]


def test_persisted_index_does_not_reencode_documents(isolated_rag, monkeypatch):
    seed_dir, encoder = isolated_rag
    (seed_dir / "policy.md").write_text("Annual leave policy", encoding="utf-8")
    rag.ensure_index()
    assert len(encoder.calls) == 1

    monkeypatch.setattr(rag, "_indexed", False)
    rag.ensure_index()

    assert len(encoder.calls) == 1
    assert rag._get_collection().count() == 1


@pytest.mark.parametrize("contents", ["", "# Handbook\n\n## Annual Leave"])
def test_empty_or_heading_only_corpus_needs_no_model(isolated_rag, contents):
    seed_dir, encoder = isolated_rag
    (seed_dir / "headings.md").write_text(contents, encoding="utf-8")
    assert rag.search_handbook("年假") == []
    assert encoder.calls == []
