import re
from typing import Optional

_title_re = re.compile(r"<title[^>]*>(.*?)</title>", re.I|re.S)

def extract_title(html: str) -> Optional[str]:
    m = _title_re.search(html or "")
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    return None

URL_RE = re.compile(r'\b(?:(?:https?://)[^\s"\'>]+|(?:[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,}))\b')

def extract_targets_from_text(text: str) -> list[str]:
    items = URL_RE.findall(text or "")
    seen = set(); out = []
    for it in items:
        if it not in seen:
            seen.add(it); out.append(it)
    return out
