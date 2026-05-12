import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "news.json"
CORE_CATEGORY = "\u6838\u5fc3AI\u516c\u53f8\u65b0\u95fb"
PRACTICE_CATEGORY = "Vibe/Prompt/Agent\u5b9e\u6218"

COMPANY_QUERIES = [
    ("OpenAI", "OpenAI"),
    ("Anthropic", "Anthropic"),
    ("Google DeepMind", "Google DeepMind"),
    ("Meta AI", "Meta AI"),
    ("xAI", "xAI"),
    ("DeepSeek", "DeepSeek"),
    ("Alibaba Tongyi", "Alibaba Tongyi"),
    ("Xiaomi AI", "Xiaomi AI model"),
]

PRACTICE_QUERIES = [
    ("vibe coding agent prompt engineering", ["agent", "prompt", "vibecoding"]),
    ("enterprise ai agent workflow", ["enterprise", "agent", "workflow"]),
]


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def google_news_rss(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def normalize_date(raw: str) -> str:
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_rss_items(rss_text: str, category: str, grade: str, limit: int = 5):
    root = ET.fromstring(rss_text)
    channel = root.find("channel")
    if channel is None:
        return []
    items = []
    for item in channel.findall("item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source = item.find("source")
        source_name = source.text.strip() if source is not None and source.text else "Google News"
        clean_title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
        items.append(
            {
                "title": clean_title,
                "summary": f"来自 {source_name} 的最新动态，建议打开原文核验细节。",
                "date": normalize_date(pub_date),
                "sourceName": source_name,
                "sourceUrl": link,
                "sourceGrade": grade,
                "category": category,
                "tags": [],
                "importance": 3,
            }
        )
    return items


def dedupe(items):
    seen = set()
    result = []
    for it in items:
        key = (it["title"].lower(), it["sourceUrl"])
        if key in seen:
            continue
        seen.add(key)
        result.append(it)
    return result


def main():
    items = []
    for company, query in COMPANY_QUERIES:
        try:
            rss = fetch_text(google_news_rss(query))
            parsed = parse_rss_items(rss, CORE_CATEGORY, "B", limit=4)
            for it in parsed:
                it["tags"] = [company, "enterprise"]
                it["importance"] = 4
            items.extend(parsed)
        except Exception:
            continue

    for query, tags in PRACTICE_QUERIES:
        try:
            rss = fetch_text(google_news_rss(query))
            parsed = parse_rss_items(rss, PRACTICE_CATEGORY, "B", limit=4)
            for it in parsed:
                it["tags"] = tags
                it["importance"] = 5
            items.extend(parsed)
        except Exception:
            continue

    items = dedupe(items)
    items.sort(key=lambda x: (x["date"], x["importance"]), reverse=True)
    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "items": items[:60],
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {OUT_FILE} with {len(payload['items'])} items.")


if __name__ == "__main__":
    main()
