import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "news.json"


def main():
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    assert len(items) >= 20, f"expected at least 20 news items, got {len(items)}"
    assert any(item.get("sourceGrade") == "A" for item in items), "expected at least one A-grade source"
    assert any(item.get("sourceGrade") == "B" for item in items), "expected at least one B-grade source"
    assert any("enterprise" in [str(tag).lower() for tag in item.get("tags", [])] for item in items), "expected enterprise-tagged content"
    assert any(item.get("category") == "Vibe/Prompt/Agent实战" for item in items), "expected practice category content"
    assert any(item.get("category") == "核心AI博主" for item in items), "expected creator/blogger content"

    for item in items:
        date = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        assert date >= cutoff, f"item is older than 30 days: {item['title']} ({item['date']})"
        for field in ("title", "titleZh", "summary", "summaryZh", "date", "sourceName", "sourceUrl", "sourceGrade", "category", "readingScore"):
            assert item.get(field), f"missing field {field}: {item}"
        assert len(item["summary"]) >= 40, f"summary is too short: {item['title']}"
        assert len(item["summaryZh"]) >= 40, f"Chinese summary is too short: {item['title']}"
        assert isinstance(item.get("keyPoints"), list) and item["keyPoints"], f"missing key points: {item['title']}"
        assert isinstance(item.get("keyPointsZh"), list) and item["keyPointsZh"], f"missing Chinese key points: {item['title']}"

    print(
        "PASS news data validation: "
        f"{len(items)} items, "
        f"{sum(1 for i in items if i['sourceGrade'] == 'A')} A-grade, "
        f"{sum(1 for i in items if i['category'] == '核心AI博主')} creator items, "
        f"{sum(1 for i in items if i['category'] == 'Vibe/Prompt/Agent实战')} practice items."
    )


if __name__ == "__main__":
    main()
