"""Opt-in real Jina tests; no local model download, GPT calls or PostgreSQL."""
import math
import os

import pytest

from shared import rag

pytestmark = pytest.mark.skipif(os.getenv("RUN_API_INTEGRATION") != "1", reason="Set RUN_API_INTEGRATION=1 to use the configured Jina API")


@pytest.fixture(scope="module", autouse=True)
def api_index(tmp_path_factory):
    if os.getenv("RUN_API_INTEGRATION") != "1":
        yield
        return
    patch = pytest.MonkeyPatch()
    patch.setattr(rag, "CHROMA_PATH", tmp_path_factory.mktemp("api-index") / "chroma")
    rag._queries.clear()
    yield
    patch.undo()


@pytest.mark.parametrize("query,source,expected", [
    ("How many days of paid annual leave do employees receive?", "employee-handbook.md", "25 天"),
    ("員工每年有多少天有薪年假？", "employee-handbook.md", "25 天"),
    ("Which VPN should I install?", "it-setup.md", "Cisco AnyConnect"),
    ("我應該安裝哪個 VPN？", "it-setup.md", "Cisco AnyConnect"),
    ("What currency should Hong Kong expense claims use?", "benefits-guide.md", "港幣（HKD）"),
    ("報銷開支用甚麼貨幣？", "benefits-guide.md", "港幣（HKD）"),
])
def test_real_bilingual_retrieval(query, source, expected):
    results = rag.search_handbook(query)
    assert any(row.source == source and expected in row.content for row in results)
    assert len(results) == 3


def test_api_dimension_and_normalization():
    vectors = rag._encode(["Annual leave", "有薪年假"], "retrieval.query")
    assert len(vectors) == 2
    assert all(len(vector) == 2048 for vector in vectors)
    assert all(math.isclose(sum(n*n for n in vector), 1, abs_tol=1e-5) for vector in vectors)
