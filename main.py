import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from core.bot import bot
from core.state import (
    load_application_state,
    load_blacklist
)

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
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set.")

async def main() -> None:
    log.info("Starting Discord connection")
    try:
        await bot.start(TOKEN.strip())
    except Exception:
        log.exception("Bot crashed during runtime")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Received shutdown signal -- KeyboardInterrupt")
    except Exception:
        log.exception("Fatal error during startup")
        sys.exit(1)