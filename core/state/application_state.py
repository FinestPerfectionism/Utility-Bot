import json
from pathlib import Path
from typing import Any

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Applications Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

APPLICATION_STATE_FILE:   Path = Path("application_state.json")
ACTIVE_APPLICATIONS_FILE: Path = Path("active_applications.json")

APPLICATIONS_OPEN: dict[str, bool] = {
    "mod":   True,
    "admin": True,
}

ACTIVE_APPLICATIONS: dict[int, dict[str, Any]] = {}

def load_application_state() -> None:
    if not APPLICATION_STATE_FILE.exists():
        save_application_state()
        return

    try:
        data = json.loads(APPLICATION_STATE_FILE.read_text())
    except Exception:
        return

    APPLICATIONS_OPEN["mod"]   = bool(data.get("mod", True))
    APPLICATIONS_OPEN["admin"] = bool(data.get("admin", True))

def save_application_state() -> None:
    _ = APPLICATION_STATE_FILE.write_text(
        json.dumps(APPLICATIONS_OPEN, indent=4),
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
            "type":              data.get("type"),
            "questions":         data.get("questions", []),
            "answers":           data.get("answers", []),
            "index":             data.get("index", 0),
            "editing":           data.get("editing", False),
            "reviewing":         data.get("reviewing", False),
            "channel_id":        data.get("channel_id"),
            "messages":          data.get("messages", []),
            "review_message_id": data.get("review_message_id"),
            "log_message_id":    data.get("log_message_id"),
        }

def save_active_applications() -> None:
    serializable: dict[str, dict[str, Any]] = {}

    for user_id, data in ACTIVE_APPLICATIONS.items():
        serializable[str(user_id)] = {
            "type":              data.get("type"),
            "questions":         data.get("questions", []),
            "answers":           data.get("answers", []),
            "index":             data.get("index", 0),
            "editing":           data.get("editing", False),
            "reviewing":         data.get("reviewing", False),
            "channel_id":        data.get("channel_id"),
            "messages":          data.get("messages", []),
            "review_message_id": data.get("review_message_id"),
            "log_message_id":    data.get("log_message_id"),
        }

    _ = ACTIVE_APPLICATIONS_FILE.write_text(
        json.dumps(serializable, indent=4),
    )
