import unittest
from datetime import date
from unittest.mock import patch

from app.knowledge import build_chunks
from app.services.chat_service import answer
from app.services.core_facts import resolve


class CoreFactsTests(unittest.TestCase):
    def test_total_experience_uses_dated_full_time_roles(self):
        for question in ("How many years of experience do you have?", "how much yoe do you have in total"):
            text, documents = resolve(question, date(2026, 10, 16))
            self.assertIn("2 years and 8 months", text)
            self.assertIn("Wiz Freight and Holiday Channel", text)
            self.assertTrue(documents)

    def test_technology_duration_is_not_invented(self):
        for question in ("How many years of Python experience do you have?", "How long have you used Python?"):
            text, _ = resolve(question)
            self.assertIn("not sure of an exact start date", text)

    def test_employer_tenure_is_not_total_experience(self):
        wiz, _ = resolve("How long did you work at Wiz Freight?", date(2026, 10, 16))
        holiday, _ = resolve("How long have you been at Holiday Channel?", date(2026, 10, 16))
        self.assertIn("2 years and 4 months", wiz)
        self.assertIn("4 months", holiday)
        internship, _ = resolve("How long was your Holiday Channel internship?", date(2026, 10, 16))
        self.assertIn("3 months", internship)
        cognizant, _ = resolve("How long were you at Cognizant?", date(2026, 10, 16))
        self.assertIn("not sure of the exact duration", cognizant)

    def test_introduction_and_degree_are_current(self):
        intro, _ = resolve("introduce yourself", date(2026, 10, 16))
        self.assertIn("Holiday Channel", intro)
        self.assertIn("earned my MS", intro)
        self.assertNotIn("pursuing", intro)
        degree, _ = resolve("Have you graduated with your master's?")
        self.assertIn("February 2026", degree)
        self.assertNotIn("pursuing", degree)
        bachelor, _ = resolve("Did you graduate from SRM University?")
        self.assertIn("B.Tech", bachelor)

    def test_basic_answers_skip_retrieval_and_model(self):
        with patch("app.langgraph.graph.retrieve", side_effect=AssertionError("retrieval should not run")):
            with patch("app.langgraph.graph.openai_client", side_effect=AssertionError("model should not run")):
                self.assertIn("2 years and", answer("How much yoe do you have in total?")["answer"])
                self.assertIn("earned my MS", answer("Introduce yourself")["answer"])

    def test_old_profile_readme_is_not_indexed_as_biography(self):
        chunks = build_chunks()
        self.assertFalse(any(doc["title"] == "n-saji README" for doc in chunks))
        self.assertTrue(any(doc["entity"] == "education" and "February 2026" in doc["text"] for doc in chunks))

    def test_old_assistant_claims_are_not_fed_back_to_model(self):
        with patch("app.langgraph.graph.openai_client") as client:
            client.return_value.responses.create.return_value.output_text = "I built SyncBeat."
            answer("Tell me about SyncBeat", [
                {"role": "user", "content": "What did you build?"},
                {"role": "assistant", "content": "I am currently pursuing a master's degree."},
            ])
            prompt = client.return_value.responses.create.call_args.kwargs["input"]
            self.assertNotIn("currently pursuing", prompt)
            self.assertIn("Earlier question: What did you build?", prompt)


if __name__ == "__main__":
    unittest.main()
