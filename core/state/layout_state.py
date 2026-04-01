import json
from pathlib import Path
from typing import Any

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Layout Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

LAYOUT_FILE = Path("data/layout_message_ids.json")

def load_layout_message_ids() -> dict[str, Any]:
    if not LAYOUT_FILE.exists():
        return {"tickets": None, "applications": None, "leave": None}
    try:
        with LAYOUT_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"tickets": None, "applications": None, "leave": None}

def save_layout_message_ids(layout_ids: dict[str, Any]) -> None:
    LAYOUT_FILE.parent.mkdir(exist_ok=True, parents=True)
    with LAYOUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(layout_ids, f)
