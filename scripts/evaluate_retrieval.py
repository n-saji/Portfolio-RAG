"""Fail if the refreshed namespace misses reviewed facts in the top five."""

import json
from pathlib import Path

from app.langgraph.nodes.retriever import retrieve_node


def main() -> None:
    cases = json.loads((Path(__file__).resolve().parents[1] / "data/evals/retrieval.json").read_text())
    hits = 0
    for case in cases:
        result = retrieve_node({"question": case["question"], "classification": case["classification"]})
        ids = [doc.metadata.get("record_id") for doc in result["documents"][:5]]
        success = any(expected in ids for expected in case["expected"])
        hits += success
        print(json.dumps({"question": case["question"], "hit": success, "top5": ids}))
    recall = hits / len(cases)
    print(f"recall@5={recall:.3f} ({hits}/{len(cases)})")
    if recall < 0.9:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
