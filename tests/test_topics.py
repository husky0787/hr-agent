import pytest

from shared import rag
from shared.documents import DOCUMENT_TITLES
from shared.topics import ALIASES, detect_topics, inventory

ORIGINAL = '請介紹公司的有薪年假、醫療保險登記期限及健康津貼。'


def test_inventory_covers_every_current_document_heading():
    topics = inventory()
    assert len(topics) == 40
    assert {topic.source for topic in topics} == set(DOCUMENT_TITLES)
    assert {topic.heading for topic in topics} == set(ALIASES)
    # Every heading can be recognized on its own, including nested words such as 侍產假.
    for topic in topics:
        assert detect_topics(topic.heading) == [topic]


@pytest.mark.parametrize('query, expected', [
    (ORIGINAL, ['公司有薪年假', '醫療保險登記', '健康津貼']),
    ('Annual leave, medical insurance registration and wellness allowance?',
     ['公司有薪年假', '醫療保險登記', '健康津貼']),
    ('年假、医疗保险和 wellness stipend', ['公司有薪年假', '醫療保險登記', '健康津貼']),
    ('VPN設定、2FA期限及 password 管理', ['VPN 設定', '雙重認證', '密碼管理']),
    ('侍產假與產假', ['侍產假', '產假']),
    ('年假結轉、報銷流程、工程團隊', ['未放取年假及結轉', '報銷審批及付款', '工程團隊專屬安排']),
    ('年假幾多日？年假點申請？', ['公司有薪年假']),
    ('cryptography steam passwordless', []),
    ('公司可否帶寵物上班？', []),
])
def test_bilingual_topics_order_deduplication_and_boundaries(query, expected):
    assert [topic.heading for topic in detect_topics(query)] == expected


@pytest.fixture
def topic_index(tmp_path, monkeypatch):
    seed = tmp_path / 'seed'
    seed.mkdir()
    monkeypatch.setattr(rag, 'SEED_DATA_DIR', seed)
    monkeypatch.setattr(rag, 'CHROMA_PATH', tmp_path / 'chroma')
    monkeypatch.setenv('EMBEDDING_DIMENSIONS', '3')
    monkeypatch.setattr(rag, 'DOCUMENT_FILENAMES', frozenset({'employee-handbook.md', 'benefits-guide.md'}))
    # Annual leave deliberately loses the broad top-3 search to the other benefits and sick leave.
    (seed / 'employee-handbook.md').write_text('## 公司有薪年假\n每年 25 天。\n\n## 病假及醫生證明書\n每年 12 天。', encoding='utf-8')
    (seed / 'benefits-guide.md').write_text('## 醫療保險登記\n入職 30 天內。\n\n## 健康津貼\n每年 HKD 2000。', encoding='utf-8')
    rag._queries.clear()
    calls = []
    def encode(texts, task):
        calls.append((texts, task))
        return [[0.0, 1.0, 0.0] if task == 'retrieval.passage' and '25 天' in text
                else [1.0, 0.0, 0.0] for text in texts]
    monkeypatch.setattr(rag, '_encode', encode)
    yield calls
    rag._queries.clear()


def test_compound_query_recovers_missing_annual_leave_in_one_embedding_batch(topic_index):
    old = rag.search_handbook(ORIGINAL)
    assert not any('25 天' in row.content for row in old)
    rows = rag.search_documents(ORIGINAL)
    assert len(rows) == 3
    assert ['25 天' in rows[0].content, '30 天' in rows[1].content, '2000' in rows[2].content] == [True] * 3
    assert all('12 天' not in row.content for row in rows)
    assert topic_index[-1] == ([topic.query for topic in detect_topics(ORIGINAL)], 'retrieval.query')
    calls = len(topic_index)
    assert rag.search_documents(ORIGINAL) == rows
    assert len(topic_index) == calls
    # Equivalent English phrasing reuses the same focused topic vectors.
    assert rag.search_documents('annual leave, medical insurance and wellness') == rows
    assert len(topic_index) == calls


def test_unknown_topic_keeps_vector_search_and_question_intent(topic_index):
    query = 'Can I bring my pet to work?'
    assert rag.search_documents(query) == rag.search_handbook(query)
    assert topic_index[-1] == ([query], 'retrieval.query')


def test_round_robin_budget_keeps_every_topic_before_extra_chunks(monkeypatch):
    topics = inventory()[:4]
    class Index:
        def count(self):
            return 12
    monkeypatch.setattr(rag, 'ensure_index', lambda: Index())
    monkeypatch.setattr(rag, '_query_vectors', lambda queries: [[1.0]] * len(queries))
    def search(vector, count, topic):
        return [rag.SearchResult(f'{topic.heading}-{n}', topic.source, 0.9) for n in range(2)]
    monkeypatch.setattr(rag, '_search', search)
    rows = rag.search_documents('compound', topics)
    assert len(rows) == 6
    assert [row.content for row in rows[:4]] == [f'{topic.heading}-0' for topic in topics]


def test_too_many_topics_asks_to_narrow_before_any_api(monkeypatch):
    def forbidden():
        raise AssertionError('No index or API needed')
    monkeypatch.setattr(rag, 'ensure_index', forbidden)
    with pytest.raises(rag.EmbeddingError, match='最多六項'):
        rag.search_documents('many', inventory()[:7])
