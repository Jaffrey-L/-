import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "news.json"

CORE_CATEGORY = "\u6838\u5fc3AI\u516c\u53f8\u65b0\u95fb"
PRACTICE_CATEGORY = "Vibe/Prompt/Agent\u5b9e\u6218"
LOOKBACK_DAYS = 10
MAX_ITEMS = 80

OFFICIAL_RSS_SOURCES = [
    {
        "name": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
        "category": CORE_CATEGORY,
        "tags": ["OpenAI", "official"],
        "importance": 5,
    },
    {
        "name": "NVIDIA AI",
        "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
        "category": CORE_CATEGORY,
        "tags": ["NVIDIA", "official"],
        "importance": 4,
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": PRACTICE_CATEGORY,
        "tags": ["Hugging Face", "open-source", "practice"],
        "importance": 4,
    },
]

GOOGLE_NEWS_QUERIES = [
    ("Anthropic", "site:anthropic.com/news Anthropic Claude enterprise", CORE_CATEGORY, ["Anthropic", "enterprise"], 4),
    ("Google DeepMind", "site:deepmind.google/discover/blog Google DeepMind AI", CORE_CATEGORY, ["Google DeepMind", "research"], 4),
    ("Meta AI", "site:ai.meta.com/blog Meta AI Llama", CORE_CATEGORY, ["Meta AI", "model"], 4),
    ("xAI", "site:x.ai xAI Grok", CORE_CATEGORY, ["xAI", "model"], 4),
    ("DeepSeek", "DeepSeek AI enterprise model", CORE_CATEGORY, ["DeepSeek", "enterprise"], 4),
    ("Alibaba Qwen", "Alibaba Qwen Tongyi enterprise AI", CORE_CATEGORY, ["Alibaba Qwen", "enterprise"], 4),
    ("Xiaomi AI", "Xiaomi AI model agent", CORE_CATEGORY, ["Xiaomi AI", "model"], 3),
    ("Vibe Coding", "vibe coding agent prompt engineering", PRACTICE_CATEGORY, ["vibecoding", "prompt", "agent"], 5),
    ("Enterprise Agents", "enterprise AI agent workflow deployment", PRACTICE_CATEGORY, ["enterprise", "agent", "workflow"], 5),
]

BLOCKED_TITLE_KEYWORDS = [
    "lawsuit",
    "shoot",
    "celebrity",
    "stock price prediction",
    "price target",
]


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="replace")


def google_news_rss(query):
    encoded = urllib.parse.quote_plus(query)
    return "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en".format(encoded)


def clean_title(title):
    title = re.sub(r"\s+", " ", title or "").strip()
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip()


def normalize_date(raw):
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[: len(fmt)], fmt).replace(tzinfo=timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def is_recent(date_str):
    try:
        published = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return published >= datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)


def is_relevant(title):
    lowered = title.lower()
    return not any(keyword in lowered for keyword in BLOCKED_TITLE_KEYWORDS)


def parse_feed_items(feed_text, source_name, category, grade, tags, importance, limit):
    root = ET.fromstring(feed_text)
    items = []

    rss_items = root.findall("./channel/item")
    if rss_items:
        for node in rss_items[:limit]:
            title = clean_title(node.findtext("title"))
            date = normalize_date(node.findtext("pubDate") or node.findtext("dc:date") or "")
            link = node.findtext("link") or ""
            items.append(make_item(title, date, source_name, link, grade, category, tags, importance))
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for node in root.findall("atom:entry", ns)[:limit]:
        link_node = node.find("atom:link", ns)
        link = link_node.attrib.get("href", "") if link_node is not None else ""
        title = clean_title(node.findtext("atom:title", default="", namespaces=ns))
        date = normalize_date(
            node.findtext("atom:updated", default="", namespaces=ns)
            or node.findtext("atom:published", default="", namespaces=ns)
        )
        items.append(make_item(title, date, source_name, link, grade, category, tags, importance))
    return items


def parse_google_news(feed_text, query_name, category, tags, importance, limit):
    root = ET.fromstring(feed_text)
    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for node in channel.findall("item")[:limit]:
        title = clean_title(node.findtext("title"))
        date = normalize_date(node.findtext("pubDate") or "")
        link = node.findtext("link") or ""
        source_node = node.find("source")
        source_name = source_node.text.strip() if source_node is not None and source_node.text else query_name
        items.append(make_item(title, date, source_name, link, "B", category, tags, importance))
    return items


def make_item(title, date, source_name, link, grade, category, tags, importance):
    return {
        "title": title,
        "summary": "\u6765\u81ea {} \u7684\u6700\u65b0\u52a8\u6001\uff0c\u5efa\u8bae\u6253\u5f00\u539f\u6587\u6838\u9a8c\u7ec6\u8282\u3002".format(source_name),
        "date": date,
        "sourceName": source_name,
        "sourceUrl": link,
        "sourceGrade": grade,
        "category": category,
        "tags": tags,
        "importance": importance,
    }


def keep_item(item):
    return bool(item["title"] and item["sourceUrl"] and is_recent(item["date"]) and is_relevant(item["title"]))


def collect_official():
    items = []
    for source in OFFICIAL_RSS_SOURCES:
        try:
            feed = fetch_text(source["url"])
            parsed = parse_feed_items(
                feed,
                source["name"],
                source["category"],
                "A",
                source["tags"],
                source["importance"],
                limit=8,
            )
            items.extend([item for item in parsed if keep_item(item)])
        except Exception as exc:
            print("Official source failed: {} ({})".format(source["name"], exc))
    return items


def collect_google_news():
    items = []
    for name, query, category, tags, importance in GOOGLE_NEWS_QUERIES:
        try:
            feed = fetch_text(google_news_rss(query))
            parsed = parse_google_news(feed, name, category, tags, importance, limit=6)
            items.extend([item for item in parsed if keep_item(item)])
        except Exception as exc:
            print("Google News query failed: {} ({})".format(name, exc))
    return items


def dedupe(items):
    seen_titles = set()
    result = []
    for item in sorted(items, key=lambda x: (x["sourceGrade"] != "A", x["date"], x["importance"]), reverse=False):
        title_key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        result.append(item)
    return result


def main():
    items = collect_official() + collect_google_news()
    items = dedupe(items)
    items.sort(key=lambda x: (x["date"], x["sourceGrade"] == "A", x["importance"]), reverse=True)

    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "A": "Official RSS, official blog, or first-party source.",
            "B": "Official-domain Google News query or reputable media/newsletter source.",
            "C": "Secondary commentary; not included in the default daily feed yet.",
        },
        "items": items[:MAX_ITEMS],
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print("Updated {} with {} items.".format(OUT_FILE, len(payload["items"])))


if __name__ == "__main__":
    main()
