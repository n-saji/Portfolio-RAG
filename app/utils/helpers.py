import re

COMPANY_ALIASES = {
	"holiday channel": ["holiday channel", "holiday channel, llc"],
	"wiz freight": ["wiz freight"],
	"highradius": ["highradius", "high radius"],
	"cognizant": ["cognizant"],
	"prograd": ["prograd"],
}

_FOLLOW_UP_PATTERNS = [
	r"^(in|for)\s+(years|months|weeks|days)$",
	r"^how\s+long$",
	r"^for\s+how\s+long$",
	r"^how\s+many\s+(years|months|weeks|days)$",
	r"^duration$",
	r"^length$",
]


def _normalize(text: str) -> str:
	return re.sub(r"\s+", " ", text.strip().lower())


def contains_company_name(text: str) -> bool:
	normalized = _normalize(text)
	for aliases in COMPANY_ALIASES.values():
		for alias in aliases:
			if alias in normalized:
				return True
	return False


def is_follow_up_question(question: str) -> bool:
	normalized = _normalize(question)
	for pattern in _FOLLOW_UP_PATTERNS:
		if re.match(pattern, normalized):
			return True
	return False


def extract_last_user_message(history: str) -> str:
	if not history or history.strip() == "No previous history.":
		return ""

	lines = [line.strip() for line in history.split("\n") if line.strip()]
	for line in reversed(lines):
		if line.startswith("User:"):
			return line.replace("User:", "", 1).strip()
	return ""
