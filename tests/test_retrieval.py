import json
import unittest

from app.knowledge import APPROVED, build_chunks, load_sources, source_is_stale
from app.services.retrieval import exact, lexical, retrieve


class SourceTests(unittest.TestCase):
    def test_public_repo_snapshot(self):
        facts, sources = load_sources()
        repos = sources["repositories"]
        self.assertEqual(56, len(repos))
        self.assertTrue(any(repo["project_id"] == "syncbeat" for repo in repos))
        self.assertTrue(all(repo["url"].startswith("https://github.com/n-saji/") for repo in repos))
        self.assertTrue(all(len(repo["commit_sha"]) == 40 for repo in repos))
        self.assertEqual(64, len(sources["resume"]["sha256"]))
        experience = sources["resume"]["text"].split("Experience\n", 1)[1].split("\nProjects", 1)[0]
        current = facts["career"][0]
        self.assertTrue(experience.startswith("Holiday Channel June 2026 – Present"))
        self.assertEqual("holiday-channel-current", current["id"])
        self.assertEqual("2026-06", current["start"])

    def test_chunks_are_stable_and_provenanced(self):
        first, second = build_chunks(), build_chunks()
        self.assertEqual(first, second)
        self.assertEqual(len(first), len({item["id"] for item in first}))
        self.assertTrue(all(item["url"] and item["verified_at"] for item in first))

    def test_source_age(self):
        self.assertTrue(source_is_stale("2020-01-01"))
        self.assertFalse(source_is_stale("2099-01-01"))


class RetrievalTests(unittest.TestCase):
    def test_current_job_is_exact(self):
        docs = exact("What am I doing at my current job?")
        self.assertEqual("holiday-channel-current", docs[0]["entity"])

    def test_known_role_does_not_mix_unrelated_projects(self):
        for question in ("What is your current job?", "What is your job?"):
            docs, _ = retrieve(question)
            self.assertEqual({"holiday-channel-current"}, {doc["entity"] for doc in docs})

    def test_syncbeat_group(self):
        docs = exact("How does SyncBeat work?")
        self.assertTrue(any(doc["entity"] == "syncbeat" and doc["kind"] == "project" for doc in docs))

    def test_lexical_education(self):
        docs = lexical("Where did Nikhil get his master's degree?")
        self.assertTrue(any(doc["entity"] == "education" for doc in docs[:5]))

    def test_followup_resolves_previous_topic(self):
        docs, _ = retrieve("How does it work?", [{"role": "user", "content": "Tell me about SyncBeat"}])
        self.assertTrue(any(doc["entity"] == "syncbeat" for doc in docs))


if __name__ == "__main__":
    unittest.main()
