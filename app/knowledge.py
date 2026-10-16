"""Build source-grounded, stable chunks for lexical and vector retrieval."""

import hashlib
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / "data" / "approved"


def load_sources() -> tuple[dict, dict]:
    return (json.loads((APPROVED / "facts.json").read_text()), json.loads((APPROVED / "sources.json").read_text()))


def _split_tokens(text: str, size: int = 350, overlap: int = 40) -> list[str]:
    import tiktoken

    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    if len(tokens) <= size:
        return [text.strip()] if text.strip() else []
    chunks = []
    step = size - overlap
    for start in range(0, len(tokens), step):
        piece = encoding.decode(tokens[start:start + size]).strip()
        if piece:
            chunks.append(piece)
        if start + size >= len(tokens):
            break
    return chunks


def _document(kind: str, entity: str, title: str, text: str, url: str, verified_at: str, source_date: str | None = None) -> list[dict]:
    output = []
    # Preserve README headings as retrieval boundaries before token splitting.
    sections = re.split(r"(?=^#{1,6}\s+\S)", text, flags=re.MULTILINE)
    pieces = [piece for section in sections if section.strip() for piece in _split_tokens(f"{title}\n{section}")]
    for i, piece in enumerate(pieces):
        digest = hashlib.sha256(f"{kind}:{entity}:{i}:{piece}".encode()).hexdigest()[:24]
        output.append({"id": digest, "kind": kind, "entity": entity, "title": title, "text": piece, "url": url, "verified_at": verified_at, "source_date": source_date})
    return output


def build_chunks() -> list[dict]:
    facts, sources = load_sources()
    verified_at = facts["verified_at"]
    resume = sources["resume"]
    output = []
    for item in facts["career"] + facts["profile"]:
        url = resume["url"] if item["source"] == "resume" else "https://www.nikhilsaji.dev/"
        source_date = item.get("source_date") or (resume["source_date"] if item["source"] == "resume" else verified_at)
        output += _document("career" if item in facts["career"] else "profile", item["id"], item["title"], item["text"], url, item.get("verified_at", verified_at), source_date)
    for item in facts["featured_projects"]:
        output += _document("project", item["id"], item["title"], item["text"], item["url"], verified_at)
    # Repository metadata gives breadth without inventing features absent from README.
    for repo in sources["repositories"]:
        text = f"Public GitHub repository {repo['name']}."
        if repo["description"]:
            text += f" GitHub description: {repo['description']}"
        if repo["language"]:
            text += f" Primary language: {repo['language']}."
        output += _document("repository", repo["project_id"], repo["name"], text, repo["url"], sources["checked_at"], repo["pushed_at"])
        # The personal GitHub profile README is an unreviewed biography and can
        # contradict the newer, reviewed resume (for example, graduation status).
        if repo["name"].lower() != "n-saji" and repo.get("readme_excerpt"):
            output += _document("repository", repo["project_id"], f"{repo['name']} README", repo["readme_excerpt"], repo["readme_url"], sources["checked_at"], repo["pushed_at"])
    # The resume itself fills gaps not covered by the concise reviewed fact cards.
    sections = re.split(r"(?m)^(Summary|Education|Experience|Projects|Skills)\s*$", resume["text"])
    for i in range(1, len(sections), 2):
        heading, body = sections[i], sections[i + 1]
        if heading == "Projects":
            # Project descriptions are maintained in the reviewed project cards
            # and repository snapshots; resume project copy may lag the code.
            continue
        output += _document("resume", heading.lower(), heading, body, resume["url"], verified_at, resume["source_date"])
    return output


def load_chunks() -> list[dict]:
    path = APPROVED / "chunks.json"
    if path.exists():
        return json.loads(path.read_text())
    return build_chunks()


def source_is_stale(source_date: str | None, days: int = 90) -> bool:
    if not source_date:
        return True
    return (date.today() - date.fromisoformat(source_date[:10])).days > days
