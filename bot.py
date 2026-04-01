import logging
from typing import Any

import discord
from discord.ext import commands
from typing_extensions import override

from core.cases import CasesManager

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class UtilityBot(commands.Bot):
    cases_manager : CasesManager
    mod_data      : dict[str, Any]
    notes_manager : Any

    def __init__(self) -> None:
        intents : discord.Intents = discord.Intents.default()
        intents.guilds            = True
        intents.members           = True
        intents.message_content   = True

        super().__init__(
            command_prefix   = ".",
            intents          = intents,
            case_insensitive = True,
        )
        self.cases_manager : CasesManager = CasesManager(self)
        self.mod_data      : dict[str, Any] = {}
        self.notes_manager : Any = None

    @override
    async def setup_hook(self) -> None:
        from core.cog_loader import discover_cogs

        _ = self.remove_command("help")

        log: logging.Logger = logging.getLogger("Utility Bot")

        priority_load : list[str] = [
            "events.systems.antinuke",
            "events.systems.verification",
            "core.startup",
        ]

        cogs : list[str] = discover_cogs(
            "commands",
            "events",
            "core",
            priority = priority_load,
        )

        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog: %s", cog)
            except Exception:
                log.exception("Failed to load cog: %s", cog)

bot: UtilityBot = UtilityBot()
