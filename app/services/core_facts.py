"""Answer stable identity and career questions from reviewed structured facts."""

import re
from datetime import date

from app.knowledge import load_sources, source_is_stale
from app.services.retrieval import corpus


def _docs(*entities: str) -> list[dict]:
    wanted = set(entities)
    return [doc for doc in corpus()[0] if doc["entity"] in wanted and doc["kind"] in {"career", "profile"}][:5]


def _career(facts: dict, entity: str) -> dict:
    return next(item for item in facts["career"] if item["id"] == entity)


def _profile(facts: dict, entity: str) -> dict:
    return next(item for item in facts["profile"] if item["id"] == entity)


def _full_time_months(facts: dict, today: date) -> int:
    """Count non-overlapping calendar months; month-only source dates are approximate."""
    months = set()
    for role in facts["career"]:
        if "intern" in role["title"].lower() or not re.fullmatch(r"\d{4}-\d{2}", role["start"]):
            continue
        start_year, start_month = map(int, role["start"].split("-"))
        end_year, end_month = map(int, (role["end"] or today.strftime("%Y-%m")).split("-"))
        first = start_year * 12 + start_month
        last = end_year * 12 + end_month
        months.update(range(first, max(first, last)))
    return len(months)


def _duration(months: int) -> str:
    years, extra = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if extra or not parts:
        parts.append(f"{extra} month{'s' if extra != 1 else ''}")
    return " and ".join(parts)


def _role_months(role: dict, today: date) -> int | None:
    if not re.fullmatch(r"\d{4}-\d{2}", role["start"]):
        return None
    start_year, start_month = map(int, role["start"].split("-"))
    end_year, end_month = map(int, (role["end"] or today.strftime("%Y-%m")).split("-"))
    return max(0, (end_year - start_year) * 12 + end_month - start_month)


def _experience_answer(facts: dict, today: date) -> str:
    months = _full_time_months(facts, today)
    return (
        f"I have about {_duration(months)} of full-time software engineering experience as of "
        f"{today.strftime('%B %Y')}, across Wiz Freight and Holiday Channel. "
        "I've also completed software engineering internships."
    )


def _current_answer(facts: dict) -> str:
    role = _career(facts, "holiday-channel-current")
    answer = role["text"]
    if source_is_stale(role.get("source_date")):
        answer += f" That's the latest role information I have, dated {role['source_date']}."
    return answer


def resolve(question: str, today: date | None = None) -> tuple[str, list[dict]] | None:
    """Return a grounded answer for a core question, or defer to RAG."""
    q = question.lower().strip()
    today = today or date.today()
    if re.search(r"\b(confidential|non-public|secret|password|api key|internal (?:code|data|information|detail|work))\b", q):
        return "I can't share confidential or internal details.", []
    if re.search(r"\b(favou?rite|hobb(?:y|ies)|salary|partner|family|age)\b", q):
        return "I'm not sure about that personal detail.", []

    facts, _ = load_sources()
    duration_question = bool(
        re.search(r"\byoe\b|\b(?:how (?:many|much) years?|how long|years?)\b.{0,60}\b(?:experience|worked|working|used|using|been|at|internship|role)\b|\b(?:total|overall) experience\b", q)
    )
    if duration_question:
        if re.search(r"\b(?:python|golang|go|java|javascript|typescript|aws|react|postgresql|redis|docker|kubernetes)\b", q):
            technology = next(word for word in ("Python", "Go", "Java", "JavaScript", "TypeScript", "AWS", "React", "PostgreSQL", "Redis", "Docker", "Kubernetes") if re.search(rf"\b{word.lower()}\b", q) or (word == "Go" and "golang" in q))
            return f"I use {technology} in my work and projects, but I'm not sure of an exact start date to calculate years of experience with it.", _docs("skills")
        if "wiz freight" in q:
            role = _career(facts, "wiz-freight")
            months = _role_months(role, today)
            if months is not None:
                return f"I worked at Wiz Freight from March 2022 to July 2024, about {_duration(months)}.", _docs("wiz-freight")
        if "holiday channel" in q and "intern" in q:
            role = _career(facts, "holiday-channel-intern")
            months = _role_months(role, today)
            if months is not None:
                return f"I interned at Holiday Channel from May to August 2025, about {_duration(months)}.", _docs("holiday-channel-intern")
        if "holiday channel" in q or "holiday world" in q:
            role = _career(facts, "holiday-channel-current")
            months = _role_months(role, today)
            if months is not None:
                return f"I've been a Software Engineer at Holiday Channel since June 2026, about {_duration(months)} as of {today.strftime('%B %Y')}. I also interned there from May to August 2025.", _docs("holiday-channel-current", "holiday-channel-intern")
        for role in facts["career"]:
            if role["id"] in {"holiday-channel-current", "holiday-channel-intern", "wiz-freight"}:
                continue
            if any(alias.lower() in q for alias in role.get("aliases", [])):
                return f"I worked at {role['title'].split(' at ')[-1]} in {role['start']}, but I'm not sure of the exact duration because I only have the year.", _docs(role["id"])
        return _experience_answer(facts, today), _docs("wiz-freight", "holiday-channel-current", "summary")

    if re.search(r"\b(?:introduce yourself|tell me about yourself|who are you|give me an introduction|short bio|tell me about your background)\b", q):
        intro = (
            "Hi, I'm Nikhil Saji, a software engineer based in Virginia. "
            + _experience_answer(facts, today).split(" I've also")[0]
            + " I currently work at Holiday Channel, and I build backend systems, AI agents, and full-stack products. "
            + "I earned my MS in Computer Science from the University at Buffalo in February 2026."
        )
        return intro, _docs("summary", "education", "holiday-channel-current", "wiz-freight")

    if re.search(r"\b(?:master'?s?|graduat(?:e|ed|ion)|degree|education|university|college|studied|study|studying|student|pursuing)\b", q):
        if re.search(r"\b(?:srm|b\.?tech|bachelor'?s?)\b", q):
            return "I earned my B.Tech in Computer Science from SRM University in May 2022.", _docs("education")
        if re.search(r"\b(?:graduat(?:e|ed)|pursuing|finished|completed|done)\b", q):
            prefix = "No, " if "pursuing" in q else "Yes, "
            return prefix + "I graduated with an MS in Computer Science from the University at Buffalo in February 2026.", _docs("education")
        return _profile(facts, "education")["text"], _docs("education")

    if re.search(r"\b(?:where (?:are|do) you (?:based|live)|your location)\b", q):
        return "I'm based in Virginia, USA.", _docs("summary")

    if re.search(r"\b(?:tech stack|technologies|programming languages|what tools|what skills)\b", q):
        return _profile(facts, "skills")["text"], _docs("skills")

    if re.search(r"\b(?:contact you|reach you|your email|your github|your linkedin)\b", q):
        return _profile(facts, "contact")["text"], _docs("contact")

    if re.search(r"\b(?:current (?:job|role|employer|work)|where do you work|what do you do (?:for work|now)|who do you work for)\b", q):
        return _current_answer(facts), _docs("holiday-channel-current")

    if re.search(r"\b(?:work experience|your experience|career history|work history|where have you worked|previous roles|past roles)\b", q):
        answer = (
            "I currently work as a Software Engineer at Holiday Channel, where I was also an intern in 2025. "
            "Before that, I was a Software Development Engineer at Wiz Freight from March 2022 to July 2024. "
            "I also held internships at Cognizant, Prograd, and HighRadius."
        )
        return answer, _docs("holiday-channel-current", "holiday-channel-intern", "wiz-freight", "cognizant", "prograd", "highradius")

    return None
