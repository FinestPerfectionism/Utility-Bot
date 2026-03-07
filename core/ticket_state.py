import json
import os
from typing import Any

ACTIVE_TICKETS: dict[int, int] = {}
THREAD_OPENERS: dict[int, int] = {}
TICKET_CLAIMS: dict[int, int] = {}
TICKET_TYPES: dict[int, str] = {}
RESOLUTION_STOPPED: set[int] = set()
RESOLUTION_STATE: dict[int, dict[str, Any]] = {}

_STATE_PATH = "data/tickets.json"

def save_ticket_state() -> None:
    os.makedirs("data", exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "active_tickets": {str(k): v for k, v in ACTIVE_TICKETS.items()},
                "thread_openers": {str(k): v for k, v in THREAD_OPENERS.items()},
                "ticket_claims": {str(k): v for k, v in TICKET_CLAIMS.items()},
                "ticket_types": {str(k): v for k, v in TICKET_TYPES.items()},
                "resolution_stopped": list(RESOLUTION_STOPPED),
                "resolution_state": {str(k): v for k, v in RESOLUTION_STATE.items()},
            },
            f,
            indent=2,
        )

def load_ticket_state() -> None:
    if not os.path.exists(_STATE_PATH):
        return
    with open(_STATE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    ACTIVE_TICKETS.update({int(k): int(v) for k, v in data.get("active_tickets", {}).items()})
    THREAD_OPENERS.update({int(k): int(v) for k, v in data.get("thread_openers", {}).items()})
    TICKET_CLAIMS.update({int(k): int(v) for k, v in data.get("ticket_claims", {}).items()})
    TICKET_TYPES.update({int(k): str(v) for k, v in data.get("ticket_types", {}).items()})
    RESOLUTION_STOPPED.update(int(x) for x in data.get("resolution_stopped", []))
    RESOLUTION_STATE.update({int(k): v for k, v in data.get("resolution_state", {}).items()})

def register_ticket(user_id: int, thread_id: int, ticket_type: str) -> None:
    ACTIVE_TICKETS[user_id] = thread_id
    THREAD_OPENERS[thread_id] = user_id
    TICKET_TYPES[thread_id] = ticket_type
    save_ticket_state()

def unregister_ticket(thread_id: int) -> None:
    user_id = THREAD_OPENERS.pop(thread_id, None)
    if user_id is not None:
        ACTIVE_TICKETS.pop(user_id, None)
    TICKET_CLAIMS.pop(thread_id, None)
    TICKET_TYPES.pop(thread_id, None)
    RESOLUTION_STATE.pop(thread_id, None)
    save_ticket_state()