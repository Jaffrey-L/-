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
SOURCES_FILE = ROOT / "sources.json"

CORE_CATEGORY = "\u6838\u5fc3AI\u516c\u53f8\u65b0\u95fb"
CREATOR_CATEGORY = "\u6838\u5fc3AI\u535a\u4e3b"
SOLO_CATEGORY = "AI\u4e2a\u4eba\u516c\u53f8\u5927\u795e"
PRACTICE_CATEGORY = "Vibe/Prompt/Agent\u5b9e\u6218"
LOOKBACK_DAYS = 30
MAX_ITEMS = 90
MIN_QUALITY_SCORE = 30

RSS_SOURCES = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml", "category": CORE_CATEGORY, "tags": ["OpenAI", "official"], "importance": 5},
    {"name": "NVIDIA", "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/", "category": CORE_CATEGORY, "tags": ["NVIDIA", "official"], "importance": 4},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": PRACTICE_CATEGORY, "tags": ["Hugging Face", "open-source", "practice"], "importance": 4},
    {"name": "Microsoft AI", "url": "https://blogs.microsoft.com/ai/feed/", "category": CORE_CATEGORY, "tags": ["Microsoft AI", "official"], "importance": 4},
    {"name": "Andrej Karpathy", "url": "https://karpathy.bearblog.dev/feed/", "category": CREATOR_CATEGORY, "tags": ["Andrej Karpathy", "vibecoding", "agent", "creator"], "importance": 5},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "category": CREATOR_CATEGORY, "tags": ["Simon Willison", "llm-engineering", "creator"], "importance": 5},
    {"name": "One Useful Thing", "url": "https://www.oneusefulthing.org/feed", "category": CREATOR_CATEGORY, "tags": ["Ethan Mollick", "enterprise", "creator"], "importance": 5},
    {"name": "Latent.Space", "url": "https://www.latent.space/feed", "category": CREATOR_CATEGORY, "tags": ["swyx", "agent", "creator"], "importance": 5},
    {"name": "Interconnects", "url": "https://www.interconnects.ai/feed", "category": CREATOR_CATEGORY, "tags": ["Nathan Lambert", "research", "creator"], "importance": 5},
    {"name": "The Batch", "url": "https://www.deeplearning.ai/the-batch/feed/", "category": CREATOR_CATEGORY, "tags": ["deeplearning.ai", "newsletter", "creator"], "importance": 4},
    {"name": "Chip Huyen", "url": "https://huyenchip.com/feed.xml", "category": CREATOR_CATEGORY, "tags": ["Chip Huyen", "ml-systems", "creator"], "importance": 4},
    {"name": "Lilian Weng", "url": "https://lilianweng.github.io/index.xml", "category": CREATOR_CATEGORY, "tags": ["Lilian Weng", "agent", "research"], "importance": 4},
]

EXTRA_QUERIES = [
    ("Cursor", "Cursor AI coding agent", PRACTICE_CATEGORY, ["Cursor", "coding", "agent"], 4),
    ("Claude Code", "Claude Code agent coding workflow", PRACTICE_CATEGORY, ["Claude Code", "coding", "agent"], 4),
    ("Vibe Coding", "vibe coding agent prompt engineering", PRACTICE_CATEGORY, ["vibecoding", "prompt", "agent"], 5),
    ("Enterprise Agents", "enterprise AI agent workflow deployment", PRACTICE_CATEGORY, ["enterprise", "agent", "workflow"], 5),
]

BLOCKED_TITLE_KEYWORDS = ["lawsuit", "shoot", "celebrity", "stock price prediction", "price target"]
LOW_VALUE_SIGNALS = [
    "award", "awards", "conference", "event", "webinar", "podcast", "interview", "quote", "quoting",
    "workforce reduction", "hiring", "appointed", "joins", "stock", "shares", "funding", "raises",
    "partnership announced", "press release", "opinion", "policy statement",
]
LOW_VALUE_TITLE_SIGNALS = [
    "quoting ", "quote ", "workforce reduction", "breaking my brain", "chemical hygiene",
    "animals vs ghosts", "podcast", "interview", "event recap", "conference recap",
]
QUALITY_SIGNALS = {
    "technical_update": [
        "api", "sdk", "model", "benchmark", "architecture", "inference", "training", "eval", "evaluation",
        "embedding", "embeddings", "reasoning", "context window", "multimodal", "tool use", "function calling",
        "open weights", "fine-tuning", "dataset", "latency", "throughput", "memory", "token", "rlhf",
        "distillation", "rag", "retrieval", "vector", "agent", "agents", "computer use", "code", "coding",
    ],
    "feature_update": [
        "launch", "launches", "released", "release", "introduces", "announces", "adds", "available",
        "rollout", "beta", "general availability", "ga", "upgrade", "new feature", "connector",
        "integration", "enterprise", "workspace", "assistant", "copilot", "deep research", "operator",
    ],
    "application_method": [
        "how to", "guide", "tutorial", "workflow", "playbook", "case study", "best practice", "lessons",
        "implementation", "build", "building", "deploy", "deployment", "prompt", "prompting",
        "vibe coding", "agent workflow", "automation", "use case", "practical", "hands-on",
    ],
}
QUALITY_LABELS_ZH = {
    "technical_update": "\u6280\u672f\u66f4\u65b0",
    "feature_update": "\u91cd\u8981\u529f\u80fd\u66f4\u65b0",
    "application_method": "AI\u5e94\u7528\u65b9\u6cd5",
    "general": "\u4e00\u822c\u52a8\u6001",
}
ZH_TERMS = {
    "ai": "AI", "agent": "\u667a\u80fd\u4f53", "agents": "\u667a\u80fd\u4f53", "model": "\u6a21\u578b", "models": "\u6a21\u578b",
    "enterprise": "\u4f01\u4e1a\u5e94\u7528", "workflow": "\u5de5\u4f5c\u6d41", "deployment": "\u90e8\u7f72", "coding": "\u7f16\u7a0b",
    "prompt": "\u63d0\u793a\u8bcd", "open-source": "\u5f00\u6e90", "research": "\u7814\u7a76", "inference": "\u63a8\u7406",
    "training": "\u8bad\u7ec3", "voice": "\u8bed\u97f3", "video": "\u89c6\u9891", "search": "\u641c\u7d22", "official": "\u5b98\u65b9\u52a8\u6001",
    "creator": "\u535a\u4e3b\u89c2\u70b9", "practice": "\u5b9e\u6218\u65b9\u6cd5", "newsletter": "\u901a\u8baf", "vibecoding": "Vibe Coding",
}


def load_source_pool():
    data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {
        CORE_CATEGORY: list(data.get("companies", [])),
        CREATOR_CATEGORY: list(data.get("creators", [])),
        SOLO_CATEGORY: list(data.get("soloBuilders", [])),
    }


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
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', value or "", flags=re.IGNORECASE)
    return match.group(1) if match else ""


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


def count_signals(text, signals):
    lowered = text.lower()
    return sum(1 for signal in signals if signal in lowered)


def quality_profile(title, summary, body, tags, category, grade):
    text = " ".join([title or "", summary or "", strip_html(body)])
    title_text = (title or "").lower()
    signal_counts = {name: count_signals(text, signals) for name, signals in QUALITY_SIGNALS.items()}
    best_type = max(signal_counts, key=signal_counts.get)
    positive_hits = sum(signal_counts.values())
    low_hits = count_signals(text, LOW_VALUE_SIGNALS)
    title_low_hit = any(signal in title_text for signal in LOW_VALUE_TITLE_SIGNALS)

    score = positive_hits * 18 - low_hits * 18
    if category == PRACTICE_CATEGORY:
        score += 24
    if category == CREATOR_CATEGORY and best_type in ("technical_update", "application_method"):
        score += 16
    if grade == "A":
        score += 8
    if len(strip_html(body)) > 700:
        score += 8
    if title_low_hit:
        score -= 45
    if positive_hits == 0:
        best_type = "general"
    return {
        "qualityScore": max(0, min(score, 100)),
        "qualityType": best_type,
        "qualityLabelZh": QUALITY_LABELS_ZH.get(best_type, QUALITY_LABELS_ZH["general"]),
        "qualitySignals": signal_counts,
        "lowValueSignals": low_hits,
        "titleLowValue": title_low_hit,
    }


def summarize_text(title, body, source_name):
    text = strip_html(body)
    if not text:
        return "{} from {}. Included for AI tracking; open the original article to verify details.".format(title, source_name)
    sentences = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", text)
    useful = [s.strip() for s in sentences if len(s.strip()) > 40]
    summary = " ".join(useful[:2]) or text[:260]
    if len(summary) < 80:
        summary = "{} from {}. Useful for deciding whether the original article deserves a deeper read.".format(title, source_name)
    return summary[:420]


def localize_text(text):
    result = text or ""
    phrase_map = {
        "Focus:": "\u5173\u6ce8\u65b9\u5411\uff1a",
        "Worth reading for practical context and source details.": "\u503c\u5f97\u9605\u8bfb\uff0c\u53ef\u5e2e\u52a9\u7406\u89e3\u5b9e\u6218\u80cc\u666f\u4e0e\u4fe1\u606f\u6765\u6e90\u3002",
        "Open the original article for full evidence and nuance.": "\u5efa\u8bae\u6253\u5f00\u539f\u6587\u67e5\u770b\u5b8c\u6574\u8bc1\u636e\u548c\u7ec6\u8282\u3002",
        "Included for AI tracking; open the original article to verify details.": "\u5df2\u7eb3\u5165 AI \u60c5\u62a5\u8ddf\u8e2a\uff0c\u5efa\u8bae\u6253\u5f00\u539f\u6587\u6838\u9a8c\u7ec6\u8282\u3002",
        "Useful for deciding whether the original article deserves a deeper read.": "\u9002\u5408\u7528\u4e8e\u5feb\u901f\u5224\u65ad\u8fd9\u7bc7\u5185\u5bb9\u662f\u5426\u503c\u5f97\u6df1\u8bfb\u3002",
        "from": "\u6765\u81ea", "for": "\u9762\u5411", "with": "\u7ed3\u5408", "and": "\u4ee5\u53ca",
    }
    for en, zh in phrase_map.items():
        result = re.sub(r"\b{}\b".format(re.escape(en)), zh, result, flags=re.IGNORECASE)
    for en, zh in sorted(ZH_TERMS.items(), key=lambda item: len(item[0]), reverse=True):
        result = re.sub(r"\b{}\b".format(re.escape(en)), zh, result, flags=re.IGNORECASE)
    return result


def readable_tags(tags):
    return [ZH_TERMS.get(str(tag).lower(), str(tag)) for tag in tags[:4]]


def chinese_headline(title, source_name, tags):
    if re.search(r"[\u4e00-\u9fff]", title):
        return title
    tag_text = "\u3001".join(readable_tags(tags)[:3]) or "AI"
    return "\u3010{}\u3011{}\u76f8\u5173\u524d\u6cbf\u52a8\u6001".format(source_name, tag_text)


def chinese_summary(source_name, summary, tags):
    tag_text = "\u3001".join(readable_tags(tags)) or "AI"
    localized = localize_text(summary[:220])
    if len(re.findall(r"[\u4e00-\u9fff]", localized)) < 12:
        localized = "\u7cfb\u7edf\u5df2\u4ece\u539f\u6587\u6807\u9898\u548c\u6458\u8981\u8bc6\u522b\u51fa\u76f8\u5173\u4e3b\u9898\uff0c\u5e76\u7eb3\u5165\u8fd1 30 \u5929 AI \u60c5\u62a5\u6d41\u3002"
    return "\u8fd9\u7bc7\u5185\u5bb9\u6765\u81ea{}\uff0c\u805a\u7126{}\u3002{}\u5efa\u8bae\u91cd\u70b9\u5173\u6ce8\u5b83\u5bf9\u4ea7\u54c1\u3001\u4f01\u4e1a\u843d\u5730\u6216\u4e2a\u4eba\u5de5\u4f5c\u6d41\u7684\u542f\u53d1\u3002".format(source_name, tag_text, localized)


def key_points_from_text(body, tags):
    text = strip_html(body)
    candidates = []
    for sentence in re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", text):
        s = sentence.strip()
        lowered = s.lower()
        if 35 <= len(s) <= 180 and any(k in lowered for k in ("ai", "agent", "model", "enterprise", "llm", "open-source", "prompt", "coding")):
            candidates.append(s)
    if not candidates:
        tag_text = ", ".join(tags[:3])
        candidates = ["Focus: {}".format(tag_text or "AI"), "Worth reading for practical context and source details.", "Open the original article for full evidence and nuance."]
    return candidates[:3]


def chinese_points(points, tags):
    result = []
    defaults = [
        "\u4fe1\u606f\u6765\u6e90\u5df2\u7eb3\u5165\u6838\u5fc3\u8ffd\u8e2a\u6e05\u5355\uff0c\u9002\u5408\u4f5c\u4e3a\u8fd1\u671f AI \u52a8\u6001\u89c2\u5bdf\u3002",
        "\u53ef\u4f18\u5148\u5173\u6ce8\u5176\u5bf9\u4f01\u4e1a\u5e94\u7528\u3001Agent \u5de5\u4f5c\u6d41\u6216\u5b9e\u6218\u65b9\u6cd5\u7684\u542f\u53d1\u3002",
        "\u82e5\u8981\u505a\u51b3\u7b56\u6216\u6df1\u5ea6\u5b66\u4e60\uff0c\u5efa\u8bae\u70b9\u51fb\u539f\u6587\u6838\u9a8c\u5b8c\u6574\u8bed\u5883\u3002",
    ]
    for index, point in enumerate(points[:3]):
        text = localize_text(point)
        if not re.search(r"[\u4e00-\u9fff]", text):
            text = defaults[index]
        result.append(text[:180])
    return result


def reading_score(grade, importance, category, body, quality_score):
    score = importance * 12
    if grade == "A":
        score += 20
    if category in (CREATOR_CATEGORY, PRACTICE_CATEGORY, SOLO_CATEGORY):
        score += 15
    if len(strip_html(body)) > 600:
        score += 10
    score += int(quality_score * 0.35)
    return min(score, 100)


def make_item(title, date, source_name, link, grade, category, tags, importance, body="", image_url="", publisher=""):
    summary = summarize_text(title, body, source_name)
    points = key_points_from_text(body, tags)
    quality = quality_profile(title, summary, body, tags, category, grade)
    return {
        "title": title,
        "titleZh": chinese_headline(title, source_name, tags),
        "summary": summary,
        "summaryZh": chinese_summary(source_name, summary, tags),
        "keyPoints": points,
        "keyPointsZh": chinese_points(points, tags),
        "imageUrl": image_url,
        "date": date,
        "sourceName": source_name,
        "publisher": publisher,
        "sourceUrl": link,
        "sourceGrade": grade,
        "category": category,
        "contentType": "article" if category in (CREATOR_CATEGORY, SOLO_CATEGORY) else "news",
        "readingScore": reading_score(grade, importance, category, body, quality["qualityScore"]),
        "tags": tags,
        "importance": importance,
        **quality,
    }


def keep_item(item):
    return bool(
        item["title"]
        and item["sourceUrl"]
        and is_recent(item["date"])
        and is_relevant(item["title"])
        and item.get("qualityScore", 0) >= MIN_QUALITY_SCORE
        and item.get("qualityType") != "general"
        and not item.get("titleLowValue")
    )


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
        date = normalize_date(node.findtext("atom:updated", default="", namespaces=ns) or node.findtext("atom:published", default="", namespaces=ns))
        body = node.findtext("atom:summary", default="", namespaces=ns) or node.findtext("atom:content", default="", namespaces=ns) or ""
        items.append(make_item(title, date, source_name, link, grade, category, tags, importance, body, extract_image(body)))
    return items


def parse_google_news(feed_text, tracked_source, category, tags, importance, limit):
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
        publisher = source_node.text.strip() if source_node is not None and source_node.text else "Google News"
        description = node.findtext("description") or ""
        items.append(make_item(title, date, tracked_source, link, "B", category, tags, importance, description, extract_image(description), publisher))
    return items


def collect_rss():
    items, coverage = [], {}
    for source in RSS_SOURCES:
        coverage[source["name"]] = {"rss": source["url"], "rssItems": 0, "googleItems": 0, "status": "pending"}
        try:
            parsed = parse_feed_items(fetch_text(source["url"]), source["name"], source["category"], "A", source["tags"], source["importance"], limit=8)
            parsed = [item for item in parsed if keep_item(item)]
            coverage[source["name"]]["rssItems"] = len(parsed)
            coverage[source["name"]]["status"] = "ok"
            items.extend(parsed)
        except Exception as exc:
            coverage[source["name"]]["status"] = "failed: {}".format(exc)
            print("RSS source failed: {} ({})".format(source["name"], exc))
    return items, coverage


def source_query(name, category):
    if category == CORE_CATEGORY:
        return '"{}" AI model agent enterprise API release feature update'.format(name)
    if category == CREATOR_CATEGORY:
        return '"{}" AI LLM agent prompt coding workflow guide'.format(name)
    return '"{}" AI startup product workflow automation case study'.format(name)


def collect_google_news(source_pool, coverage):
    items = []
    query_specs = []
    for category, names in source_pool.items():
        for name in names:
            tags = [name, "enterprise" if category == CORE_CATEGORY else "creator"]
            importance = 5 if category != SOLO_CATEGORY else 4
            query_specs.append((name, source_query(name, category), category, tags, importance))
    query_specs.extend(EXTRA_QUERIES)

    seen_specs = set()
    for name, query, category, tags, importance in query_specs:
        key = (name, query)
        if key in seen_specs:
            continue
        seen_specs.add(key)
        coverage.setdefault(name, {"rss": "", "rssItems": 0, "googleItems": 0, "status": "pending"})
        try:
            parsed = parse_google_news(fetch_text(google_news_rss(query)), name, category, tags, importance, limit=3)
            parsed = [item for item in parsed if keep_item(item)]
            coverage[name]["googleItems"] = coverage[name].get("googleItems", 0) + len(parsed)
            if coverage[name].get("status") in ("pending", ""):
                coverage[name]["status"] = "ok"
            items.extend(parsed)
        except Exception as exc:
            if coverage[name].get("status") in ("pending", ""):
                coverage[name]["status"] = "failed: {}".format(exc)
            print("Google News query failed: {} ({})".format(name, exc))
    return items


def dedupe(items):
    seen_titles = set()
    result = []
    for item in sorted(items, key=lambda x: (x["sourceGrade"] != "A", x["date"], x["importance"]), reverse=False):
        title_key = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", item["title"].lower()).strip()
        source_key = item.get("sourceName", "").lower()
        key = (source_key, title_key)
        if key in seen_titles:
            continue
        seen_titles.add(key)
        result.append(item)
    return result


def main():
    source_pool = load_source_pool()
    items, coverage = collect_rss()
    items.extend(collect_google_news(source_pool, coverage))
    items = dedupe(items)
    items.sort(key=lambda x: (x["date"], x["qualityScore"], x["readingScore"], x["sourceGrade"] == "A", x["importance"]), reverse=True)

    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "lookbackDays": LOOKBACK_DAYS,
        "qualityPolicy": {
            "minQualityScore": MIN_QUALITY_SCORE,
            "preferredTypes": QUALITY_LABELS_ZH,
            "blockedLowValueSignals": LOW_VALUE_SIGNALS,
        },
        "policy": {
            "A": "Official RSS, official blog, or first-party source.",
            "B": "Google News query for a tracked source or reputable media/newsletter source.",
            "C": "Secondary commentary; not included in the default daily feed yet.",
        },
        "sourceCoverage": coverage,
        "items": items[:MAX_ITEMS],
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print("Updated {} with {} items from {} tracked sources.".format(OUT_FILE, len(payload["items"]), len(coverage)))


if __name__ == "__main__":
    main()
