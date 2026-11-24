"""Verify a fresh app process cannot import obsolete database/model dependencies."""
import os
from pathlib import Path
import subprocess
import sys


def test_document_only_startup_with_no_keys_or_database():
    root = Path(__file__).resolve().parents[1]
    code = '''
import importlib.abc, sys
class BlockLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'sentence_transformers', 'psycopg') or fullname in ('shared.db', 'shared.tasks'):
            raise AssertionError('Legacy import: ' + fullname)
sys.meta_path.insert(0, BlockLegacy())
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    assert client.get('/health').status_code == 200
    assert len(client.get('/api/documents').json()['documents']) == 4
    assert client.get('/api/documents/employee-handbook.md').status_code == 200
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=root, env={**os.environ,
        'PYTHONPATH': str(root) + os.pathsep + str(root / 'backend'), 'DATABASE_URL': 'invalid',
        'OPENAI_API_KEY': '', 'XAI_API_KEY': '', 'EMBEDDING_API_KEY': '',
    }, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
