import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from core.state import (
    load_application_state,
    load_blacklist
)

from bot import bot

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Main Script
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

load_dotenv()
load_application_state()
load_blacklist()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

log = logging.getLogger("Utility Bot")

TOKEN = os.getenv("TOKEN")

async def main() -> None:
    if not TOKEN:
        raise RuntimeError("TOKEN environment variable not set.")

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