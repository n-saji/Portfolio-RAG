"""Prepare a reviewable snapshot of public resume and original GitHub repos.

The scheduled workflow writes this to data/approved/sources.json on a branch.
It has no effect on the active index until that branch is reviewed and merged.
"""

import argparse
import hashlib
import io
import json
import re
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pypdf import PdfReader

GITHUB_USER = "n-saji"
RESUME_URL = "https://www.nikhilsaji.dev/Nikhil_Saji_Resume.pdf"
HEADERS = {"User-Agent": "portfolio-rag-refresh", "Accept": "application/vnd.github+json"}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def project_id(name: str) -> str:
    lower = name.lower()
    for prefix, group in [
        ("syncbeat-", "syncbeat"),
        ("expensely", "expensely"),
        ("job-tracker", "job-tracker"),
        ("talky-space", "talky-space"),
        ("gatekeeper-", "gatekeeper"),
        ("collegeportal", "college-portal"),
    ]:
        if lower.startswith(prefix):
            return group
    return re.sub(r"[^a-z0-9]+", "-", lower).strip("-")


def repository_evidence(repo: dict) -> dict:
    name = repo["name"]
    result = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{GITHUB_USER}/{name}.git", "HEAD"],
        capture_output=True, text=True, timeout=20, check=True,
    )
    sha = result.stdout.split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError(f"Could not resolve HEAD for {name}")
    repo["commit_sha"] = sha
    repo["readme_url"] = ""
    repo["readme_excerpt"] = ""
    for filename in ("README.md", "README.MD", "readme.md", "README.rst"):
        url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{name}/{sha}/{filename}"
        try:
            raw = fetch(url).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                continue
            raise
        # Keep public narrative evidence, not install commands or embedded images.
        raw = re.sub(r"```.*?```", "", raw, flags=re.DOTALL)
        raw = re.sub(r"!\[[^]]*\]\([^)]*\)", "", raw)
        raw = re.sub(r"<[^>]+>", "", raw)
        raw = "\n".join(line for line in raw.splitlines() if not line.lstrip().startswith("[!["))
        repo["readme_url"] = f"https://github.com/{GITHUB_USER}/{name}/blob/{sha}/{filename}"
        repo["readme_excerpt"] = raw.strip()[:6000]
        break
    return repo


def github_repositories() -> list[dict]:
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}&sort=updated"
        batch = json.loads(fetch(url))
        for repo in batch:
            if repo["fork"]:
                continue
            repos.append({
                "name": repo["name"],
                "project_id": project_id(repo["name"]),
                "description": repo.get("description") or "",
                "language": repo.get("language") or "",
                "url": repo["html_url"],
                "default_branch": repo["default_branch"],
                "pushed_at": repo.get("pushed_at"),
                "updated_at": repo.get("updated_at"),
                "archived": repo["archived"],
            })
        if len(batch) < 100:
            break
        page += 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        repos = list(pool.map(repository_evidence, repos))
    return sorted(repos, key=lambda item: item["name"].lower())


def resume_snapshot() -> dict:
    pdf = fetch(RESUME_URL)
    reader = PdfReader(io.BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    # Contact data is already public, but is unnecessary for career retrieval.
    text = re.sub(r"^Virginia, USA\|.*(?:\n|$)", "", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text).strip()
    created = reader.metadata.creation_date if reader.metadata else None
    return {
        "url": RESUME_URL,
        "sha256": hashlib.sha256(pdf).hexdigest(),
        "source_date": created.astimezone(ZoneInfo("America/New_York")).date().isoformat() if created else None,
        "text": text,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/approved/sources.json")
    args = parser.parse_args()
    snapshot = {
        "checked_at": datetime.now(timezone.utc).date().isoformat(),
        "resume": resume_snapshot(),
        "repositories": github_repositories(),
    }
    path = Path(args.output)
    if path.exists():
        previous = json.loads(path.read_text())
        if previous.get("resume") == snapshot["resume"] and previous.get("repositories") == snapshot["repositories"]:
            print("No source changes")
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {path}: {len(snapshot['repositories'])} original public repositories")


if __name__ == "__main__":
    main()
