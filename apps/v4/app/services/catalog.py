from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def topic_catalog() -> list[dict]:
    path = ROOT / "config" / "topic_templates.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("templates", [])


@lru_cache(maxsize=1)
def region_catalog() -> list[dict]:
    path = ROOT / "config" / "regions.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("regions", [])


def topic_by_id(topic_id: str) -> dict | None:
    return next((x for x in topic_catalog() if x.get("id") == topic_id), None)


def detect_regions(text: str, selected_regions: list[str] | None = None) -> list[str]:
    selected = set(selected_regions or [])
    matches: list[str] = []
    for item in region_catalog():
        rid = item.get("id", "")
        name = item.get("name", "")
        if rid == "nationwide" or rid == "custom":
            continue
        if selected and "nationwide" not in selected and rid not in selected and name not in selected:
            continue
        aliases = [name, *item.get("aliases", [])]
        if any(alias and alias in text for alias in aliases):
            matches.append(name)
    if not matches and ("nationwide" in selected or "全国" in selected):
        return ["全国"]
    return sorted(set(matches))
