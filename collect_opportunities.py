import hashlib
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser

SEARCH_TERMS = [
    '"Assistant Librarian" India recruitment',
    '"Librarian" university recruitment India',
    '"Library Assistant" recruitment India',
    '"Professional Assistant" library vacancy India',
    '"Deputy Librarian" recruitment India',
    '"Library Attendant" vacancy India',
    '"Assistant Professor" "Library and Information Science" recruitment India',
    '"Library Science" JRF OR SRF OR "Project Associate" India',
    'library walk-in interview India recruitment',
    'library contractual recruitment India university',
]
BLOCK_TERMS = [
    "book fair", "library week", "library inauguration", "library opening hours",
    "library membership", "library rules", "library renovation", "library building"
]
LIS_TERMS = [
    "librarian", "library assistant", "assistant librarian", "deputy librarian",
    "professional assistant", "semi professional assistant", "library attendant",
    "library science", "library and information science", "information scientist",
    "library officer", "library professional", "documentation officer", "jrf", "srf",
    "project associate", "research assistant", "walk-in", "walk in"
]

def classify(text):
    t = text.lower()
    if any(x in t for x in ["walk-in", "walk in", "walkin"]):
        return "Walk-in Interview"
    if any(x in t for x in ["jrf", "srf", "project associate", "research assistant", "project fellow", "research fellow"]):
        return "Research & Project Posts"
    if "assistant professor" in t or "faculty" in t or "professor" in t:
        return "Academic Positions"
    if any(x in t for x in ["librarian", "library assistant", "professional assistant", "library attendant", "library officer", "information scientist", "documentation officer"]):
        return "Library Recruitment"
    return "Other LIS Opportunities"

def likely_lis(text):
    t = text.lower()
    return any(k in t for k in LIS_TERMS) and not any(b in t for b in BLOCK_TERMS)

def parsed_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return ""

def item_id(url, title):
    return hashlib.sha256((url or title).encode("utf-8")).hexdigest()[:24]

def main():
    now = datetime.now(timezone.utc).isoformat()
    items = {}
    for query in SEARCH_TERMS:
        feed_url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                title = (entry.get("title") or "").strip()
                summary = re.sub(r"<[^>]+>", " ", entry.get("summary", ""))
                url = entry.get("link", "")
                combined = f"{title} {summary}"
                if not title or not likely_lis(combined):
                    continue
                publisher = (entry.get("source") or {}).get("title") or "Google News RSS"
                uid = item_id(url, title)
                items[uid] = {
                    "id": uid,
                    "title": title,
                    "organization": publisher,
                    "category": classify(combined),
                    "state": "India",
                    "location": "India",
                    "published": parsed_date(entry),
                    "deadline": "",
                    "summary": re.sub(r"\s+", " ", summary).strip()[:650],
                    "url": url,
                    "source": publisher,
                    "first_seen": now,
                    "last_seen": now,
                    "is_new": True,
                }
        except Exception as exc:
            print(f"Feed failed for {query}: {exc}")

    output = {
        "opportunities": sorted(items.values(), key=lambda x: x.get("published") or "", reverse=True),
        "updated_at": now,
        "source_note": "Automated discovery leads; always verify details on the recruiting institution's official website."
    }
    with open("docs/opportunities.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(output['opportunities'])} matching entries.")

if __name__ == "__main__":
    main()
