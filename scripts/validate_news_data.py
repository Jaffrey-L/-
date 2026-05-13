import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "news.json"
SOURCES_FILE = ROOT / "sources.json"
CREATOR_CATEGORY = "\u6838\u5fc3AI\u535a\u4e3b"
PRACTICE_CATEGORY = "Vibe/Prompt/Agent\u5b9e\u6218"
SOLO_CATEGORY = "AI\u4e2a\u4eba\u516c\u53f8\u5927\u795e"
PREFERRED_QUALITY_TYPES = {"technical_update", "feature_update", "application_method"}


def main():
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    source_pool = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    coverage = payload.get("sourceCoverage", {})
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    expected_sources = set(source_pool.get("companies", [])) | set(source_pool.get("creators", [])) | set(source_pool.get("soloBuilders", []))

    assert len(items) >= 20, f"expected at least 20 news items, got {len(items)}"
    assert expected_sources.issubset(set(coverage)), "source coverage is missing: {}".format(sorted(expected_sources - set(coverage)))
    assert any(item.get("sourceGrade") == "A" for item in items), "expected at least one A-grade source"
    assert any(item.get("sourceGrade") == "B" for item in items), "expected at least one B-grade source"
    assert any("enterprise" in [str(tag).lower() for tag in item.get("tags", [])] for item in items), "expected enterprise-tagged content"
    assert any(item.get("category") == PRACTICE_CATEGORY for item in items), "expected practice category content"
    assert any(item.get("category") == CREATOR_CATEGORY for item in items), "expected creator/blogger content"
    assert any(item.get("sourceName") == "Andrej Karpathy" for item in items) or "Andrej Karpathy" in coverage, "expected Andrej Karpathy to be tracked"
    assert sum(1 for item in items if item.get("qualityType") in PREFERRED_QUALITY_TYPES) >= int(len(items) * 0.85), "expected most items to be high-value technical/feature/method content"
    assert any(item.get("qualityType") == "technical_update" for item in items), "expected technical update content"
    assert any(item.get("qualityType") == "feature_update" for item in items), "expected feature update content"
    assert any(item.get("qualityType") == "application_method" for item in items), "expected AI application method content"

    for item in items:
        date = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        assert date >= cutoff, f"item is older than 30 days: {item['title']} ({item['date']})"
        for field in ("title", "titleZh", "summary", "summaryZh", "date", "sourceName", "sourceUrl", "sourceGrade", "category", "readingScore", "qualityScore", "qualityType", "qualityLabelZh"):
            assert item.get(field), f"missing field {field}: {item}"
        assert item["qualityType"] in PREFERRED_QUALITY_TYPES, f"low-value item leaked into feed: {item['title']} ({item['qualityType']})"
        assert item["qualityScore"] >= 30, f"quality score too low: {item['title']} ({item['qualityScore']})"
        assert len(item["summary"]) >= 40, f"summary is too short: {item['title']}"
        assert len(item["summaryZh"]) >= 40, f"Chinese summary is too short: {item['title']}"
        assert isinstance(item.get("keyPoints"), list) and item["keyPoints"], f"missing key points: {item['title']}"
        assert isinstance(item.get("keyPointsZh"), list) and item["keyPointsZh"], f"missing Chinese key points: {item['title']}"
        assert not any("Worth reading for practical context" in point for point in item.get("keyPointsZh", [])), f"untranslated key point: {item['title']}"

    print(
        "PASS news data validation: "
        f"{len(items)} items, "
        f"{len(coverage)}/{len(expected_sources)} tracked sources covered, "
        f"{sum(1 for i in items if i['sourceGrade'] == 'A')} A-grade, "
        f"{sum(1 for i in items if i['category'] == CREATOR_CATEGORY)} creator items, "
        f"{sum(1 for i in items if i['category'] == PRACTICE_CATEGORY)} practice items, "
        f"{sum(1 for i in items if i['category'] == SOLO_CATEGORY)} solo-builder items, "
        f"{sum(1 for i in items if i['qualityType'] == 'technical_update')} technical, "
        f"{sum(1 for i in items if i['qualityType'] == 'feature_update')} feature, "
        f"{sum(1 for i in items if i['qualityType'] == 'application_method')} method."
    )


if __name__ == "__main__":
    main()
