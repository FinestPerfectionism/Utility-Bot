import discord
from discord import app_commands

from core.cog_loader import discover_cogs

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Owner Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def get_cogs() -> list[str]:
    return discover_cogs("commands", "events", "core")

async def cog_autocomplete(
    _interaction : discord.Interaction,
    current      : str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(
            name = cog,
            value = cog,
        )
        for cog in get_cogs()
        if current.lower() in cog.lower()
    ][:25]
