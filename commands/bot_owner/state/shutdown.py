import contextlib

import discord
from discord.ext import commands

import core.responses as cr
from constants import BOT_OWNER_ID
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# .shutdown Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def run_shutdown(
    bot : commands.Bot,
    ctx : commands.Context[commands.Bot],
) -> None:
    if ctx.author.id != BOT_OWNER_ID:
        _ = await send_custom_message(
            ctx,
            msg_type = cr.error,
            title    = "run command",
            subtitle = "You are not authorized to run this command.",
            footer   = "No permissions.",
        )
        return

    with contextlib.suppress(discord.HTTPException, discord.Forbidden):
        await ctx.message.delete()

    _ = await send_custom_message(
        ctx,
        msg_type = cr.information,
        title    = "Shutting down bot",
        subtitle = "Shutting down bot...",
    )

    await bot.close()
