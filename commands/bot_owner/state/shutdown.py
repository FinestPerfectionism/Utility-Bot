import discord
from discord.ext import commands

import contextlib

from constants import (
    BOT_OWNER_ID,
    DENIED_EMOJI_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .shutdown Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_shutdown(
    bot: commands.Bot,
    ctx: commands.Context[commands.Bot],
) -> None:
    if ctx.author.id != BOT_OWNER_ID:
        await ctx.message.add_reaction(DENIED_EMOJI_ID)
        return

    with contextlib.suppress(discord.HTTPException, discord.Forbidden):
        await ctx.message.delete()

    _ = await ctx.send("Shutting down bot...", delete_after=1)
    await bot.close()
