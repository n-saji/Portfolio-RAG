"""Collect approved profile facts and current public resume/GitHub evidence.

This script builds a reviewable record snapshot. It never updates Pinecone.
"""

import argparse
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RESUME_URL = "https://www.nikhilsaji.dev/Nikhil_Saji_Resume.pdf"
PORTFOLIO_FACTS_URL = "https://www.nikhilsaji.dev/portfolio-facts.json"
GITHUB_API = "https://api.github.com/users/n-saji/repos?per_page=100&type=owner"


def fetch(url: str, *, accept: str | None = None, limit: int = 2_000_000) -> bytes:
    headers = {"User-Agent": "Portfolio-RAG-source-refresh/1.0"}
    if accept:
        headers["Accept"] = accept
    token = os.getenv("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError(f"Source exceeds size limit: {url}")
    return content


def project_name(repo_name: str) -> str:
    lower = repo_name.lower()
    for prefix, name in (
        ("syncbeat-", "SyncBeat"),
        ("expensely", "Expensely"),
        ("job-tracker", "Job Tracker"),
        ("talky-space", "Talky Space"),
        ("gatekeeper", "Gatekeeper"),
        ("portfolio-rag", "Portfolio RAG Agent"),
    ):
        if lower.startswith(prefix):
            return name
    return repo_name.replace("-", " ").replace("_", " ").strip()


def resume_records(pdf_bytes: bytes, today: str) -> tuple[list[dict], str]:
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    if not pages or not any("Nikhil Saji" in page for page in pages):
        raise ValueError("Resume identity check failed; refusing to index")
    records = []
    for index, page in enumerate(pages, 1):
        text = re.sub(r"[ \t]+", " ", page).strip()
        records.append({
            "id": f"resume-page-{index}", "type": "resume", "section": "resume",
            "name": "Published resume", "text": text,
            "source_url": RESUME_URL, "source_date": today,
            "verified_at": today, "sha256": digest,
        })
    return records, digest


def github_records(today: str, readme_limit: int = 24) -> list[dict]:
    repos = json.loads(fetch(GITHUB_API, accept="application/vnd.github+json"))
    if not isinstance(repos, list):
        raise ValueError("GitHub did not return a repository list")
    repos = [repo for repo in repos if not repo.get("fork") and not repo.get("private")]
    repos.sort(key=lambda repo: repo.get("updated_at", ""), reverse=True)
    records = []
    for repo in repos:
        name = repo["name"]
        group = project_name(name)
        url = repo["html_url"]
        description = (repo.get("description") or "").strip()
        language = repo.get("language") or "not specified"
        records.append({
            "id": f"github-{name}-catalog", "type": "project", "section": "catalog",
            "name": group, "repo": name,
            "text": f"Repository: {name}. Project: {group}. {description} Main language: {language}. URL: {url}",
            "source_url": url, "source_date": repo.get("pushed_at") or today,
            "verified_at": today,
        })
    for repo in repos[:readme_limit]:
        name = repo["name"]
        branch = urllib.parse.quote(repo.get("default_branch") or "main", safe="")
        base = f"https://raw.githubusercontent.com/n-saji/{urllib.parse.quote(name, safe='')}/{branch}"
        readme = None
        for filename in ("README.md", "readme.md", "Readme.md"):
            try:
                readme = fetch(f"{base}/{filename}", limit=200_000).decode("utf-8", "replace")
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
        if not readme:
            continue
        # Readmes are evidence, not instructions. Keep an excerpt to bound embedding cost.
        excerpt = readme[:12_000]
        records.append({
            "id": f"github-{name}-readme", "type": "project", "section": "details",
            "name": project_name(name), "repo": name,
            "text": f"# {project_name(name)} / {name}\n{excerpt}",
            "source_url": repo["html_url"] + "/blob/" + branch + "/README.md",
            "source_date": repo.get("pushed_at") or today, "verified_at": today,
        })
    if not repos:
        raise ValueError("No public GitHub repositories found")
    return records


def curated_records(today: str, portfolio: dict) -> list[dict]:
    profile = json.loads((ROOT / "data/knowledge/profile.json").read_text())
    records = []
    for fact in profile["facts"]:
        record = dict(fact)
        record["id"] = "profile-" + fact["id"]
        record["source_url"] = profile["sources"][fact["source"].split(",")[0]]["url"]
        record["source_date"] = profile["verified_at"]
        record["verified_at"] = profile["verified_at"]
        record["record_type"] = "core"
        records.append(record)
    for project in portfolio["projects"]:
        records.append({
            "id": "portfolio-" + re.sub(r"[^a-z0-9]+", "-", project["name"].lower()).strip("-"),
            "type": "project", "section": "overview", "name": project["name"],
            "text": f"{project['name']}: {project['description']} Repository: {project['url']}",
            "source_url": portfolio["source_url"], "source_date": portfolio["reviewed_at"],
            "verified_at": today,
        })
    for experience in portfolio.get("experiences", []):
        records.append({
            "id": "portfolio-role-" + re.sub(r"[^a-z0-9]+", "-", (experience["company"] + "-" + experience["position"]).lower()).strip("-"),
            "type": "resume", "section": "experience", "name": experience["company"],
            "text": f"{experience['position']} at {experience['company']}, {experience['period']}. {experience['description']}",
            "source_url": portfolio["source_url"], "source_date": portfolio["reviewed_at"],
            "verified_at": today,
        })
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-file", type=Path, help="Use a local copy of the published PDF")
    parser.add_argument("--portfolio-file", type=Path, help="Use a local exported portfolio JSON")
    parser.add_argument("--output", type=Path, default=ROOT / "data/generated/records.json")
    parser.add_argument("--readme-limit", type=int, default=24)
    args = parser.parse_args()
    today = date.today().isoformat()
    pdf_bytes = args.resume_file.read_bytes() if args.resume_file else fetch(RESUME_URL)
    resume, resume_hash = resume_records(pdf_bytes, today)
    if args.portfolio_file:
        portfolio = json.loads(args.portfolio_file.read_text())
    else:
        try:
            portfolio = json.loads(fetch(PORTFOLIO_FACTS_URL, limit=200_000))
        except (urllib.error.URLError, ValueError):
            portfolio = json.loads((ROOT / "data/knowledge/portfolio.json").read_text())
    records = curated_records(today, portfolio) + resume + github_records(today, args.readme_limit)
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source record IDs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {"built_at": today, "resume_sha256": resume_hash, "records": records}
    args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "records": len(records), "resume_sha256": resume_hash}))


if __name__ == "__main__":
    main()
