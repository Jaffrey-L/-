import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "news.json"

CORE_CATEGORY = "\u6838\u5fc3AI\u516c\u53f8\u65b0\u95fb"
CREATOR_CATEGORY = "\u6838\u5fc3AI\u535a\u4e3b"
PRACTICE_CATEGORY = "Vibe/Prompt/Agent\u5b9e\u6218"
LOOKBACK_DAYS = 30
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

CREATOR_RSS_SOURCES = [
    {
        "name": "Simon Willison",
        "url": "https://simonwillison.net/atom/everything/",
        "category": CREATOR_CATEGORY,
        "tags": ["Simon Willison", "llm-engineering", "creator"],
        "importance": 5,
    },
    {
        "name": "One Useful Thing",
        "url": "https://www.oneusefulthing.org/feed",
        "category": CREATOR_CATEGORY,
        "tags": ["Ethan Mollick", "enterprise", "creator"],
        "importance": 5,
    },
    {
        "name": "Latent.Space",
        "url": "https://www.latent.space/feed",
        "category": CREATOR_CATEGORY,
        "tags": ["swyx", "agent", "creator"],
        "importance": 5,
    },
    {
        "name": "Interconnects",
        "url": "https://www.interconnects.ai/feed",
        "category": CREATOR_CATEGORY,
        "tags": ["Nathan Lambert", "research", "creator"],
        "importance": 5,
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


def strip_html(value):
    text = re.sub(r"<(script|style).*?</\1>", " ", value or "", flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_image(value):
    if not value:
        return ""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', value, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def summarize_text(title, body, source_name):
    text = strip_html(body)
    if not text:
        return "{} \u6765\u81ea {} \uff0c\u5df2\u7eb3\u5165\u4eca\u65e5 AI \u60c5\u62a5\u6458\u8981\uff0c\u5efa\u8bae\u7ed3\u5408\u539f\u6587\u6838\u9a8c\u7ec6\u8282\u4e0e\u5e94\u7528\u4ef7\u503c\u3002".format(title, source_name)
    sentences = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", text)
    useful = [s.strip() for s in sentences if len(s.strip()) > 40]
    summary = " ".join(useful[:2]) or text[:260]
    if len(summary) < 80:
        summary = "{} \u6765\u81ea {} \uff0c\u9002\u5408\u7528\u4e8e\u5feb\u901f\u5224\u65ad\u8fd9\u7bc7\u6587\u7ae0\u662f\u5426\u503c\u5f97\u6df1\u8bfb\u3002".format(title, source_name)
    return summary[:420]


def key_points_from_text(title, body, tags):
    text = strip_html(body)
    candidates = []
    for sentence in re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", text):
        s = sentence.strip()
        lowered = s.lower()
        if 35 <= len(s) <= 180 and any(k in lowered for k in ("ai", "agent", "model", "enterprise", "llm", "open-source", "prompt", "coding")):
            candidates.append(s)
    if not candidates:
        tag_text = ", ".join(tags[:3])
        return [
            "Focus: {}".format(tag_text or "AI"),
            "Worth reading for practical context and source details.",
            "Open the original article for full evidence and nuance.",
        ]
    return candidates[:3]


def reading_score(grade, importance, category, body):
    score = importance * 12
    if grade == "A":
        score += 20
    if category in (CREATOR_CATEGORY, PRACTICE_CATEGORY):
        score += 15
    if len(strip_html(body)) > 600:
        score += 10
    return min(score, 100)


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
            body = node.findtext("description") or node.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
            image = extract_image(body)
            enclosure = node.find("enclosure")
            if not image and enclosure is not None and enclosure.attrib.get("type", "").startswith("image/"):
                image = enclosure.attrib.get("url", "")
            items.append(make_item(title, date, source_name, link, grade, category, tags, importance, body, image))
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
        body = (
            node.findtext("atom:summary", default="", namespaces=ns)
            or node.findtext("atom:content", default="", namespaces=ns)
            or ""
        )
        items.append(make_item(title, date, source_name, link, grade, category, tags, importance, body, extract_image(body)))
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
        description = node.findtext("description") or ""
        items.append(make_item(title, date, source_name, link, "B", category, tags, importance, description, extract_image(description)))
    return items


def make_item(title, date, source_name, link, grade, category, tags, importance, body="", image_url=""):
    return {
        "title": title,
        "summary": summarize_text(title, body, source_name),
        "keyPoints": key_points_from_text(title, body, tags),
        "imageUrl": image_url,
        "date": date,
        "sourceName": source_name,
        "sourceUrl": link,
        "sourceGrade": grade,
        "category": category,
        "contentType": "article" if category == CREATOR_CATEGORY else "news",
        "readingScore": reading_score(grade, importance, category, body),
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


def collect_creators():
    items = []
    for source in CREATOR_RSS_SOURCES:
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
            print("Creator source failed: {} ({})".format(source["name"], exc))
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
    items = collect_official() + collect_creators() + collect_google_news()
    items = dedupe(items)
    items.sort(key=lambda x: (x["date"], x["readingScore"], x["sourceGrade"] == "A", x["importance"]), reverse=True)

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
