"""Extract limited, review-only career fields from a user's LinkedIn export.

Raw archives should be placed under data/private/ and never committed. This
script writes candidates outside the indexed data directory for manual review.
"""

import argparse
import csv
import io
import json
import zipfile
from pathlib import Path

ALLOWED = {"profile.csv", "positions.csv", "education.csv", "projects.csv"}
PUBLIC_COLUMNS = {
    "first name", "last name", "headline", "summary", "about", "industry", "position", "title",
    "company", "company name", "description", "location", "start date", "end date",
    "school", "school name", "degree", "field of study", "project name", "project description",
}


def read_export(path: Path) -> dict:
    if path.suffix.lower() != ".zip":
        raise ValueError("expected a LinkedIn ZIP export")
    output = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            leaf = Path(name).name.lower()
            if leaf not in ALLOWED:
                continue
            raw = archive.read(name).decode("utf-8-sig", errors="replace")
            rows = [
                {key: value for key, value in row.items() if key and key.strip().lower() in PUBLIC_COLUMNS}
                for row in csv.DictReader(io.StringIO(raw))
            ]
            # Only these files are read; messages, contacts, and account data stay out.
            output[leaf] = rows
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/candidates/linkedin.json"))
    args = parser.parse_args()
    data = read_export(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote review candidate {args.output}; nothing was indexed")


if __name__ == "__main__":
    main()
