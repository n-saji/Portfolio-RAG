"""Offline retrieval gate; optional live answer sample for human factual review."""

import argparse
import json
from pathlib import Path

from app.knowledge import ROOT, load_sources
from app.services.retrieval import retrieve


def cases() -> list[dict]:
    checks = json.loads((ROOT / "data/evals/retrieval.json").read_text())
    _, sources = load_sources()
    checks += [{"question": f"Tell me about your {repo['name']} repository", "entity": repo["project_id"]} for repo in sources["repositories"]]
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", action="store_true", help="also call the model and write answers for human review")
    args = parser.parse_args()
    checks = cases()
    failures = []
    for case in checks:
        docs, _ = retrieve(case["question"])
        if case["entity"] not in {doc["entity"] for doc in docs[:5]}:
            failures.append(case)
    recall = (len(checks) - len(failures)) / len(checks)
    print(f"Recall@5: {recall:.1%} ({len(checks) - len(failures)}/{len(checks)})")
    for failure in failures:
        print(f"MISS: {failure['question']} → {failure['entity']}")
    if args.answers:
        from app.services.chat_service import answer

        sample = checks[:17]
        output = [{"question": case["question"], "expected_entity": case["entity"], "answer": answer(case["question"])["answer"]} for case in sample]
        path = ROOT / "data/candidates/answer_review.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        print(f"Review factual claims in {path}")
    if recall < 0.9:
        raise SystemExit("Retrieval gate failed: recall@5 is below 90%")


if __name__ == "__main__":
    main()
