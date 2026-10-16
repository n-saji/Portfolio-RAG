import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.chat_service import answer


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_contract_and_cookie(self):
        fake = {"answer": "I built it in Go.", "documents": [{"kind": "project", "id": "1", "entity": "x", "url": "https://example.com"}], "sources": [], "timings": {}}
        with patch("app.api.routes.answer", return_value=fake):
            simple = self.client.post("/api/v1/chat", json={"question": "What did you build?"})
            advanced = self.client.post("/api/v1/advanced-chat", json={"question": "What did you build?"})
        self.assertEqual(200, simple.status_code)
        self.assertEqual("I built it in Go.", simple.json()["answer"])
        self.assertEqual("project", advanced.json()["classification"])
        self.assertIn("session_id", advanced.cookies)

    def test_blank_and_long_input(self):
        self.assertEqual(422, self.client.post("/api/v1/chat", json={"question": " "}).status_code)
        self.assertEqual(422, self.client.post("/api/v1/chat", json={"question": "x" * 501}).status_code)

    def test_provider_failure_is_safe(self):
        with patch("app.api.routes.answer", side_effect=RuntimeError("secret")):
            response = self.client.post("/api/v1/chat", json={"question": "Hello"})
        self.assertEqual(503, response.status_code)
        self.assertNotIn("secret", response.text)

    def test_confidential_request_does_not_retrieve(self):
        with patch("app.langgraph.graph.retrieve", side_effect=AssertionError("retrieval should not run")):
            response = answer("Share a confidential detail from your employer")
        self.assertIn("can't share", response["answer"])

    def test_unshared_personal_detail_stays_first_person(self):
        with patch("app.langgraph.graph.retrieve", side_effect=AssertionError("retrieval should not run")):
            response = answer("What is your favorite movie?")
        self.assertTrue(response["answer"].startswith(("I ", "I'm ")))
        self.assertEqual([], response["sources"])


if __name__ == "__main__":
    unittest.main()
