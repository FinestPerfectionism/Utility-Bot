import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Auto-Moderation Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

AUTOMOD_DELETIONS:    set[int]                = set()
AUTOMOD_STRIKES_FILE: Path                    = Path("data/automod_strikes.json")
AUTOMOD_STRIKES:      dict[int, list[datetime]] = defaultdict(list)

def save_automod_strikes() -> None:
    AUTOMOD_STRIKES_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {str(k): [t.isoformat() for t in v] for k, v in AUTOMOD_STRIKES.items()}
    _ = AUTOMOD_STRIKES_FILE.write_text(json.dumps(data, indent=4))

def load_automod_strikes() -> None:
    if not AUTOMOD_STRIKES_FILE.exists():
        return
    try:
        raw = json.loads(AUTOMOD_STRIKES_FILE.read_text())
        for user_id, times in raw.items():
            AUTOMOD_STRIKES[int(user_id)] = [datetime.fromisoformat(t) for t in times]
    except Exception:
        return
