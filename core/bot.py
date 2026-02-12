import discord
from discord.ext import commands

from commands.moderation.cases import CasesManager

import logging

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class UtilityBot(commands.Bot):
    cases_manager: CasesManager
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="~",
            intents=intents
        )

    async def setup_hook(self) -> None:
        from constants import GUILD_ID
        from core.cog_loader import discover_cogs

        self.cases_manager = CasesManager(self)
    
        log = logging.getLogger("Utility Bot")
    
        priority_load = [
            "events.member.verification",  
            "startup"
        ]

        COGS = discover_cogs(
            "commands",
            "events",
            "core",
            priority=priority_load
        )

        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog: %s", cog)
            except Exception:
                log.exception("FAILED to load cog: %s", cog)
    
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = UtilityBot()