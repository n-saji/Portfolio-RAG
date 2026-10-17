import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.memory_service import valid_session_id


class FakeGraph:
    def invoke(self, inputs):
        return {"answer": f"I heard: {inputs['question']}", "classification": "resume", "documents": []}


class ApiTests(unittest.TestCase):
    def test_chat_sets_session_and_restores_its_messages(self):
        with patch("app.api.routes.build_graph", return_value=FakeGraph()), \
             patch("app.api.routes.save_exchange") as save, \
             patch("app.api.routes.get_chat_messages", return_value=[{"role": "user", "content": "Hi"}]):
            client = TestClient(app)
            result = client.post("/api/v1/advanced-chat", json={"question": " Where do you work? "})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["answer"], "I heard: Where do you work?")
            self.assertTrue(valid_session_id(client.cookies.get("session_id")))
            save.assert_called_once()
            history = client.get("/api/v1/history")
            self.assertEqual(history.json()["messages"], [{"role": "user", "content": "Hi"}])

    def test_blank_question_is_rejected(self):
        response = TestClient(app).post("/api/v1/advanced-chat", json={"question": "   "})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
