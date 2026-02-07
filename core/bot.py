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
        log = logging.getLogger("utilitybot")

        COGS = [
            "commands.applications_tickets",
            "commands.automod",
            "commands.bot_owner",
            "commands.meme",
            "commands.misc",
            "commands.mod",
            "commands.proposal",
            "commands.roles",
            "events.applications",
            "events.automod",
            "events.commands",
            "events.errors",
            "events.leave",
            "events.messages",
            "events.on_leave",
            "events.on_message",
            "events.tickets",
            "core.startup",
        ]

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