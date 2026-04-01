import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from bot import bot
from core.state.application_state import load_application_state
from core.state.blacklist_state import load_blacklist

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Main Script
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_ = load_dotenv()
load_application_state()
load_blacklist()

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger("Utility Bot")

TOKEN = os.getenv("TOKEN")

async def main() -> None:
    if not TOKEN:
        string = "TOKEN environment variable not set."
        raise RuntimeError(string)

    log.info("Starting Discord connection")
    try:
        await bot.start(TOKEN.strip())
    except Exception:
        log.exception("Bot crashed during runtime")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Received shutdown signal —— KeyboardInterrupt")
    except Exception:
        log.exception("Fatal error during startup")
        sys.exit(1)
