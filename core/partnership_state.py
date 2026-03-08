from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import (
    Any,
    TypedDict,
    cast
)

log = logging.getLogger("Utility Bot")

IMAGE_DIR: Path = Path("data/partnership_images")
_DATA_FILE: Path = Path("data/partnerships.json")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Partnership State Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class PartnershipEntry(TypedDict):
    server_name: str
    server_description: str
    server_owner_id: int
    server_link: str
    image_filename: str


class PartnershipData(TypedDict):
    partnerships: list[PartnershipEntry]
    message_ids: list[int]
    header_message_id: int | None
    timestamp: int


def _default() -> PartnershipData:
    return {
        "partnerships": [],
        "message_ids": [],
        "header_message_id": None,
        "timestamp": 0,
    }


def load_partnership_data() -> PartnershipData:
    if not _DATA_FILE.exists():
        return _default()
    try:
        with open(_DATA_FILE) as f:
            raw: Any = json.load(f)
        if not isinstance(raw, dict):
            return _default()
        data = cast("dict[str, Any]", raw)
        return {
            "partnerships": data.get("partnerships", []),
            "message_ids": data.get("message_ids", []),
            "header_message_id": data.get("header_message_id"),
            "timestamp": data.get("timestamp", 0),
        }
    except (json.JSONDecodeError, OSError) as e:
        log.exception("Failed to load partnership data: %s", e)
        return _default()


def save_partnership_data(data: PartnershipData) -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        log.exception("Failed to save partnership data: %s", e)