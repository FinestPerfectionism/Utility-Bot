import discord
from discord.ext import commands

from typing import Any

from core.cases import CasesManager

import logging

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class UtilityBot(commands.Bot):
    cases_manager: CasesManager
    mod_data: dict[str, Any]
    notes_manager: Any

    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.guilds          = True
        intents.members         = True
        intents.message_content = True

        super().__init__(
            command_prefix   = ".",
            intents          = intents,
            case_insensitive = True
        )
        self.cases_manager: CasesManager = CasesManager(self)
        self.mod_data: dict[str, Any] = {}
        self.notes_manager: Any = None

    async def setup_hook(self) -> None:
        from constants import GUILD_ID
        from core.cog_loader import discover_cogs

        self.remove_command('help')

        log: logging.Logger = logging.getLogger("Utility Bot")

        priority_load: list[str] = [
            "events.systems.antinuke",
            "events.member.verification",
            "core.startup"
        ]

        COGS: list[str] = discover_cogs(
            "commands",
            "events",
            "core",
            priority = priority_load
        )

        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog: %s", cog)
            except Exception:
                log.exception("Failed to load cog: %s", cog)

        guild: discord.Object = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot: UtilityBot = UtilityBot()