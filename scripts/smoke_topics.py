"""Live topic/retrieval check using configured Jina; --chat also calls the chat API.

Run: python scripts/smoke_topics.py [--chat]
Writes public policy extracts and results to ignored data/topic-smoke.json; no keys.
"""
import argparse
import asyncio
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]

from shared import rag
from shared.config import DATA_DIR
from shared.topics import detect_topics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chat', action='store_true')
    args = parser.parse_args()
    original = '請介紹公司的有薪年假、醫療保險登記期限及健康津貼。'
    cases = [original, 'Annual leave, medical insurance registration and wellness allowance?',
             '年假、医疗保险和 wellness stipend', 'VPN設定、2FA期限及 password 管理']
    expected = [['25 天', '30 天', '2,000']] * 3 + [['Cisco AnyConnect', '48 小時', '1Password']]
    report = {'checks': [], 'embedding_batches': []}
    encode = rag._encode
    def track(texts, task):
        report['embedding_batches'].append({'task': task, 'count': len(texts)})
        return encode(texts, task)
    rag._encode = track
    try:
        for query, facts in zip(cases, expected):
            topics = detect_topics(query)
            rows = rag.search_documents(query, topics)
            content = '\n'.join(row.content for row in rows)
            assert all(fact in content for fact in facts), 'Missing required policy extract'
            row = {'question': query, 'topics': [topic.heading for topic in topics],
                   'sources': list(dict.fromkeys(row.source for row in rows)),
                   'chunks': len(rows), 'facts_found': facts}
            report['checks'].append(row)
            print(json.dumps(row, ensure_ascii=True), flush=True)
        if args.chat:
            from agent.multi_agent import run_async
            result = asyncio.run(run_async(original))
            compact = re.sub(r'[,\s]', '', result['response'])
            assert all(value in compact for value in ('25', '30', '2000'))
            assert set(result['citations']) == {'employee-handbook.md', 'benefits-guide.md'}
            assert '.md' not in result['response']
            report['chat'] = result
            print(json.dumps({'chat': 'passed', 'provider': result['provider'],
                              'response': result['response']}, ensure_ascii=True), flush=True)
    finally:
        rag._encode = encode
        (DATA_DIR / 'topic-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'embedding_batches': report['embedding_batches']}))


if __name__ == '__main__':
    main()
