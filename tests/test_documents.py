"""Document API boundaries; no database or external API calls."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from shared.documents import DOCUMENT_FILENAMES


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_each_company_document_can_be_read(self):
        root = Path(__file__).resolve().parents[1] / "seed-data"
        for filename in DOCUMENT_FILENAMES:
            with self.subTest(filename=filename):
                response = self.client.get(f"/api/documents/{filename}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {
                    "filename": filename,
                    "content": (root / filename).read_text(encoding="utf-8"),
                })

    def test_unknown_and_private_files_are_not_exposed(self):
        for filename in (".env", "README.md", "unknown.md", "..%2F.env", "..%5C.env"):
            with self.subTest(filename=filename):
                response = self.client.get(f"/api/documents/{filename}")
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("content", response.json())

    def test_missing_known_document_returns_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("shared.documents.SEED_DATA_DIR", Path(directory)):
                response = self.client.get("/api/documents/employee-handbook.md")
        self.assertEqual(response.status_code, 404)

    def test_health_and_document_list_without_database_or_keys(self):
        with TestClient(app) as client:
            self.assertEqual(client.get('/health').json(), {'status': 'ok'})
            documents = client.get('/api/documents').json()['documents']
            self.assertEqual({item['filename'] for item in documents}, DOCUMENT_FILENAMES)
            for path in ('/api/employee/demo', '/api/onboarding/alex-chen/status', '/api/admin/checkins', '/api/evals/results'):
                self.assertEqual(client.get(path).status_code, 404)


if __name__ == "__main__":
    unittest.main()
