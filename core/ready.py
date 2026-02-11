import discord
from discord.ext import commands

import asyncio
import logging

from core.state import (
    load_active_applications,
    ACTIVE_APPLICATIONS,
    load_automod_strikes,
    save_automod_strikes,
)

from events.systems.applications import (
    DecisionView,
)

from constants import (
    ACCEPTED_EMOJI_ID,
    APPLICATION_LOG_CHANNEL_ID,
)

log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# On Ready Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Ready(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ran = False

    async def resume_incomplete_applications(self) -> None:
        for user_id, data in ACTIVE_APPLICATIONS.items():
            if data.get("log_message_id") or not data.get("channel_id") or data.get("index") is None:
                continue

            user = self.bot.get_user(user_id)
            if not user:
                continue

            try:
                dm = await user.create_dm()
            except discord.Forbidden:
                continue

            question = data["questions"][data["index"]]
            await dm.send(
                f"**{ACCEPTED_EMOJI_ID} Successfully resumed application after restart.**\n{question}"
            )

    async def restore_application_views(self) -> None:
        channel = self.bot.get_channel(APPLICATION_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        for data in ACTIVE_APPLICATIONS.values():
            msg_id = data.get("log_message_id")
            if not msg_id:
                continue

            try:
                msg = await channel.fetch_message(msg_id)
            except discord.NotFound:
                continue

            if msg.components:
                self.bot.add_view(DecisionView(), message_id=msg.id)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._ran:
            return
        self._ran = True

        loop = asyncio.get_running_loop()
        loop.set_exception_handler(
            lambda loop, context: self.bot.dispatch("asyncio_error", context)
        )

        load_active_applications()
        load_automod_strikes()
        save_automod_strikes()

        await self.restore_application_views()
        await self.resume_incomplete_applications()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ready(bot))