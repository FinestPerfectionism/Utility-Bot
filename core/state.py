import json
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict
from datetime import datetime

OWNER_PRIVILEGE_ENABLED = True

AUTOMOD_DELETIONS: set[int] = set()

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# State Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Layout Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

LAYOUT_FILE = Path("data/layout_message_ids.json")

def load_layout_message_ids() -> dict:
    if not LAYOUT_FILE.exists():
        return {"tickets": None, "applications": None, "leave": None}
    try:
        with LAYOUT_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"tickets": None, "applications": None, "leave": None}

def save_layout_message_ids(layout_ids: dict) -> None:
    LAYOUT_FILE.parent.mkdir(exist_ok=True, parents=True)
    with LAYOUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(layout_ids, f)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Auto-Moderation Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def save_automod_strikes():
    AUTOMOD_STRIKES_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {str(k): [t.isoformat() for t in v] for k, v in AUTOMOD_STRIKES.items()}
    AUTOMOD_STRIKES_FILE.write_text(json.dumps(data, indent=4))

def load_automod_strikes():
    if not AUTOMOD_STRIKES_FILE.exists():
        return
    try:
        raw = json.loads(AUTOMOD_STRIKES_FILE.read_text())
        for user_id, times in raw.items():
            AUTOMOD_STRIKES[int(user_id)] = [datetime.fromisoformat(t) for t in times]
    except Exception:
        return

AUTOMOD_STRIKES_FILE = Path("data/automod_strikes.json")

AUTOMOD_STRIKES: dict[int, list[datetime]] = defaultdict(list)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Applications Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

APPLICATION_STATE_FILE = Path("application_state.json")
ACTIVE_APPLICATIONS_FILE = Path("active_applications.json")
BLACKLIST_FILE = Path("blacklist.json")

APPLICATIONS_OPEN: Dict[str, bool] = {
    "mod": True,
    "admin": True
}

ACTIVE_APPLICATIONS: Dict[int, Dict[str, Any]] = {}

BLACKLIST: Dict[str, list[int]] = {
    "applications": [],
    "tickets": []
}

def load_application_state() -> None:
    if not APPLICATION_STATE_FILE.exists():
        save_application_state()
        return

    try:
        data = json.loads(APPLICATION_STATE_FILE.read_text())
    except Exception:
        return

    APPLICATIONS_OPEN["mod"] = bool(data.get("mod", True))
    APPLICATIONS_OPEN["admin"] = bool(data.get("admin", True))

def save_application_state() -> None:
    APPLICATION_STATE_FILE.write_text(
        json.dumps(APPLICATIONS_OPEN, indent=4)
    )

def load_active_applications() -> None:
    if not ACTIVE_APPLICATIONS_FILE.exists():
        return

    try:
        raw = json.loads(ACTIVE_APPLICATIONS_FILE.read_text())
    except Exception:
        return

    ACTIVE_APPLICATIONS.clear()

    for user_id, data in raw.items():
        ACTIVE_APPLICATIONS[int(user_id)] = {
            "type": data.get("type"),
            "questions": data.get("questions", []),
            "answers": data.get("answers", []),
            "index": data.get("index", 0),
            "editing": data.get("editing", False),
            "reviewing": data.get("reviewing", False),
            "channel_id": data.get("channel_id"),
            "messages": data.get("messages", []),
            "review_message_id": data.get("review_message_id"),
            "log_message_id": data.get("log_message_id")
        }

def save_active_applications() -> None:
    serializable: Dict[str, Dict[str, Any]] = {}

    for user_id, data in ACTIVE_APPLICATIONS.items():
        serializable[str(user_id)] = {
            "type": data.get("type"),
            "questions": data.get("questions", []),
            "answers": data.get("answers", []),
            "index": data.get("index", 0),
            "editing": data.get("editing", False),
            "reviewing": data.get("reviewing", False),
            "channel_id": data.get("channel_id"),
            "messages": data.get("messages", []),
            "review_message_id": data.get("review_message_id"),
            "log_message_id": data.get("log_message_id")
        }

    ACTIVE_APPLICATIONS_FILE.write_text(
        json.dumps(serializable, indent=4)
    )

def load_blacklist() -> None:
    if not BLACKLIST_FILE.exists():
        save_blacklist()
        return

    try:
        data = json.loads(BLACKLIST_FILE.read_text())
    except Exception:
        return

    BLACKLIST["applications"] = list(map(int, data.get("applications", [])))
    BLACKLIST["tickets"] = list(map(int, data.get("tickets", [])))

def save_blacklist() -> None:
    BLACKLIST_FILE.write_text(
        json.dumps(BLACKLIST, indent=4)
    )