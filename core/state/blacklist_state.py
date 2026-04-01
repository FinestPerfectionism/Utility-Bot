import json
from pathlib import Path

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Blacklist Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

BLACKLIST_FILE: Path = Path("blacklist.json")

BLACKLIST: dict[str, list[int]] = {
    "applications": [],
    "tickets":      [],
}

def load_blacklist() -> None:
    if not BLACKLIST_FILE.exists():
        save_blacklist()
        return

    try:
        data = json.loads(BLACKLIST_FILE.read_text())
    except Exception:
        return

    BLACKLIST["applications"] = list(map(int, data.get("applications", [])))
    BLACKLIST["tickets"]      = list(map(int, data.get("tickets", [])))

def save_blacklist() -> None:
    _ = BLACKLIST_FILE.write_text(
        json.dumps(BLACKLIST, indent=4),
    )
