"""Real-model retrieval checks; opt in to the initial model download."""

import os

import pytest

from shared import rag

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_EMBEDDING_INTEGRATION") != "1",
    reason="Set RUN_EMBEDDING_INTEGRATION=1 to download and test the real E5 model",
)


@pytest.fixture
def isolated_index(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(rag, "_indexed", False)
    # A chat proxy key must not change the local embedding provider.
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-api-key")


@pytest.mark.parametrize(
    "query, source, expected",
    [
        ("What currency should Hong Kong expense claims use?", "benefits-guide.md", "港幣（HKD）"),
        ("報銷開支用甚麼貨幣？", "benefits-guide.md", "港幣（HKD）"),
        ("How many days of paid annual leave do employees receive?", "employee-handbook.md", "25 天"),
        ("員工每年有多少天有薪年假？", "employee-handbook.md", "25 天"),
        ("Which VPN should I install?", "it-setup.md", "Cisco AnyConnect"),
        ("我应该安装哪个虚拟专用网络软件？", "it-setup.md", "Cisco AnyConnect"),
        ("幾號出糧？", "employee-handbook.md", "出糧日期"),
        ("侍產假有幾多天？", "benefits-guide.md", "5 天侍產假"),
        ("產假有多少星期？", "benefits-guide.md", "14 星期產假"),
        ("強積金登記及供款紀錄在哪裏查詢？", "benefits-guide.md", "強積金登記"),
    ],
)
def test_seed_handbook_retrieval(isolated_index, query, source, expected):
    results = rag.search_handbook(query)
    assert any(r.source == source and expected in r.content for r in results)
    assert all("passage: " not in r.content for r in results)


def test_cross_language_recall_in_default_top_three(isolated_index, tmp_path, monkeypatch):
    seed_dir = tmp_path / "bilingual"
    seed_dir.mkdir()
    (seed_dir / "remote-en.md").write_text(
        "Employees may work from home three days per week with manager approval.",
        encoding="utf-8",
    )
    (seed_dir / "leave-zh.md").write_text(
        "公司育儿假政策：主要照顾者可享受十六周带薪育儿假。",
        encoding="utf-8",
    )
    (seed_dir / "security-en.md").write_text(
        "Enable disk encryption and two-factor authentication on your laptop.",
        encoding="utf-8",
    )
    (seed_dir / "expenses-en.md").write_text(
        "Submit itemized receipts to claim reimbursement for business travel expenses.",
        encoding="utf-8",
    )
    (seed_dir / "office-en.md").write_text(
        "Our headquarters is in Helsinki, with satellite offices in Stockholm and Berlin.",
        encoding="utf-8",
    )
    monkeypatch.setattr(rag, "SEED_DATA_DIR", seed_dir)

    # Match the app's top-3 retrieval contract; E5 does not guarantee top-1
    # cross-language ranking when same-language distractors are present.
    chinese_results = rag.search_handbook("每周可以在家办公几天？")
    english_results = rag.search_handbook("How much paid parental leave can I take?")
    assert len(chinese_results) == len(english_results) == 3
    assert "remote-en.md" in [r.source for r in chinese_results]
    assert "leave-zh.md" in [r.source for r in english_results]


def test_real_embedding_dimension_and_normalization():
    import numpy as np

    vectors = np.asarray(rag._encode(["annual leave", "带薪年假"], "query"))
    assert vectors.shape == (2, 384)
    assert np.isfinite(vectors).all()
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
