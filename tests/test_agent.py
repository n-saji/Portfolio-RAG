import json
import unittest

import tiktoken
from langchain_core.documents import Document

from app.langgraph.edges import route_from_classifier, route_from_retriever
from app.langgraph.nodes.classifier import _standalone_project_question
from app.langgraph.nodes.generator import generate_node
from app.langgraph.nodes.retriever import _rerank
from app.services import memory_service
from scripts.refresh_index import split_record
from scripts.refresh_sources import project_name


class FakeRedis:
    def __init__(self, messages):
        self.messages = messages

    def lrange(self, _key, _start, _end):
        return self.messages


class AgentTests(unittest.TestCase):
    def test_follow_up_enters_rewriter_then_retriever(self):
        self.assertEqual(route_from_classifier({"classification": "resume", "is_follow_up": True}), "rewriter")
        self.assertEqual(route_from_classifier({"classification": "unknown", "is_follow_up": True}), "fallback")
        self.assertEqual(route_from_retriever({"documents": [Document(page_content="fact")]}), "generator")
        self.assertEqual(route_from_retriever({"documents": []}), "fallback")
        self.assertTrue(_standalone_project_question("What about your latest project?"))
        self.assertFalse(_standalone_project_question("What is your latest project at Holiday Channel?"))

    def test_history_reads_structured_and_legacy_messages(self):
        previous = memory_service.redis_client
        memory_service.redis_client = FakeRedis([
            "User: Old question",
            "AI: Old answer",
            json.dumps({"role": "user", "content": "New question"}),
            json.dumps({"role": "assistant", "content": "New answer"}),
        ])
        try:
            session = memory_service.create_session_id()
            self.assertEqual([m["content"] for m in memory_service.get_chat_messages(session)],
                             ["Old question", "Old answer", "New question", "New answer"])
            self.assertEqual(memory_service.get_chat_messages("untrusted-key"), [])
        finally:
            memory_service.redis_client = previous

    def test_skill_duration_has_no_invented_years(self):
        skills = Document(
            page_content="Sources do not establish exact years of experience for Python.",
            metadata={"record_id": "profile-skills"},
        )
        result = generate_node({"question": "How many years have you used Python?", "documents": [skills], "session_id": ""})
        self.assertIn("can't put a verified number of years", result["answer"])
        self.assertNotIn("five", result["answer"].lower())

    def test_conflicting_role_attribution_is_not_presented_as_certain(self):
        conflict = Document(
            page_content="My LinkedIn profile places this caching achievement under my later Software Engineer role, so the exact role attribution differs between sources.",
            metadata={"record_id": "profile-holiday-intern"},
        )
        result = generate_node({
            "question": "Did you do Redis caching during your Holiday Channel internship or later role?",
            "documents": [conflict], "session_id": "",
        })
        self.assertIn("not sure which role", result["answer"])
        self.assertIn("resume", result["answer"])
        self.assertIn("LinkedIn", result["answer"])

    def test_project_grouping_and_heading_chunks(self):
        self.assertEqual(project_name("syncbeat-analytics"), "SyncBeat")
        self.assertEqual(project_name("Job-tracker-FE"), "Job Tracker")
        record = {
            "id": "github-example", "type": "project", "section": "details",
            "name": "Example", "text": "# Architecture\nA service.\n## Data\nPostgreSQL stores records.",
            "source_url": "https://example.com", "source_date": "2026-10-16",
        }
        chunks = split_record(record, tiktoken.get_encoding("cl100k_base"))
        self.assertEqual(len(chunks), 2)
        self.assertIn("Architecture", chunks[0]["text"])
        self.assertIn("Data", chunks[1]["text"])

    def test_exact_project_and_core_facts_are_ranked(self):
        results = [
            (Document(page_content="Generic project text", metadata={"record_id": "a", "name": "Other"}), 0.9),
            (Document(page_content="SyncBeat playback", metadata={"record_id": "b", "name": "SyncBeat"}), 0.75),
        ]
        self.assertEqual(_rerank("Tell me about SyncBeat", results)[0][0].metadata["name"], "SyncBeat")


if __name__ == "__main__":
    unittest.main()
