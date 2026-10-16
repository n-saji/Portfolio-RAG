import json

from app.knowledge import APPROVED, build_chunks


def main() -> None:
    chunks = build_chunks()
    path = APPROVED / "chunks.json"
    path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(chunks)} stable chunks to {path}")


if __name__ == "__main__":
    main()
