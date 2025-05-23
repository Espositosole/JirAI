import json
from pathlib import Path

TRACKER_FILE = Path("selected_scenarios.json")


def _load_data():
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_data(data):
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_selection(issue_key: str, indexes: list[int] | str):
    data = _load_data()
    data[issue_key] = data.get(issue_key, {})
    data[issue_key]["selection"] = indexes
    _save_data(data)


def get_selection(issue_key: str):
    data = _load_data()
    return data.get(issue_key, {}).get("selection")


def mark_suggestions_posted(issue_key: str):
    data = _load_data()
    data[issue_key] = data.get(issue_key, {})
    data[issue_key]["suggestions_posted"] = True
    _save_data(data)


def has_suggestions_been_posted(issue_key: str) -> bool:
    data = _load_data()
    return data.get(issue_key, {}).get("suggestions_posted", False)
