import discord
from discord.ext import commands

import logging

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class UtilityBot(commands.Bot):
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
    
        log = logging.getLogger("utilitybot")
    
        COGS = discover_cogs(
            "commands",
            "events",
            "core",
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