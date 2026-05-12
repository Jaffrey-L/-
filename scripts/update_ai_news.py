import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "news.json"

CORE_CATEGORY = "核心AI公司新闻"
PRACTICE_CATEGORY = "Vibe/Prompt/Agent实战"
LOOKBACK_DAYS = 7
MAX_ITEMS = 80

COMPANY_QUERIES = [
    ("OpenAI", "OpenAI enterprise AI"),
    ("Anthropic", "Anthropic Claude enterprise"),
    ("Google DeepMind", "Google DeepMind AI product"),
    ("Meta AI", "Meta AI Llama enterprise"),
    ("xAI", "xAI Grok enterprise"),
    ("DeepSeek", "DeepSeek enterprise deployment"),
    ("阿里云通义", "Alibaba Tongyi Qwen enterprise"),
    ("小米AI", "Xiaomi AI model"),
]

PRACTICE_QUERIES = [
    ("vibe coding prompt agent workflow", ["vibecoding", "prompt", "agent"]),
    ("enterprise ai agent architecture", ["enterprise", "agent", "workflow"]),
]

BLOCKED_TITLE_KEYWORDS = [
    "lawsuit", "crime", "shoot", "gossip", "celebrity",
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


def is_recent(date_str: str) -> bool:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return d >= datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)


def is_relevant_title(title: str) -> bool:
    t = title.lower()
    for bad in BLOCKED_TITLE_KEYWORDS:
        if bad in t:
            return False
    return True


def parse_rss_items(rss_text: str, category: str, grade: str, limit: int):
    root = ET.fromstring(rss_text)
    channel = root.find("channel")
    if channel is None:
        return []
    items = []
    for item in channel.findall("item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = normalize_date(item.findtext("pubDate") or "")
        source_node = item.find("source")
        source_name = source_node.text.strip() if source_node is not None and source_node.text else "Google News"
        clean_title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()

        if not is_recent(pub_date):
            continue
        if not is_relevant_title(clean_title):
            continue

        items.append(
            {
                "title": clean_title,
                "summary": f"来自 {source_name} 的最新动态，建议打开原文核验细节。",
                "date": pub_date,
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


def collect():
    items = []
    for company, query in COMPANY_QUERIES:
        try:
            rss = fetch_text(google_news_rss(query))
            parsed = parse_rss_items(rss, CORE_CATEGORY, "B", limit=6)
            for it in parsed:
                it["tags"] = [company, "enterprise"]
                it["importance"] = 4
            items.extend(parsed)
        except Exception:
            continue

    for query, tags in PRACTICE_QUERIES:
        try:
            rss = fetch_text(google_news_rss(query))
            parsed = parse_rss_items(rss, PRACTICE_CATEGORY, "B", limit=8)
            for it in parsed:
                it["tags"] = tags
                it["importance"] = 5
            items.extend(parsed)
        except Exception:
            continue
    return items


def main():
    items = dedupe(collect())
    items.sort(key=lambda x: (x["date"], x["importance"]), reverse=True)
    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "items": items[:MAX_ITEMS],
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {OUT_FILE} with {len(payload['items'])} items.")


if __name__ == "__main__":
    main()
