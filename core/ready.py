import asyncio
import contextlib
import logging
from typing import Any

import discord
from discord.ext import commands
from typing_extensions import override

from bot import bot
from constants import ACCEPTED_EMOJI_ID, APPLICATION_LOG_CHANNEL_ID, BOT_CONSOLE_CHANNEL_ID
from core.state.application_state import ACTIVE_APPLICATIONS, load_active_applications
from core.state.automod_state import load_automod_strikes, save_automod_strikes
from events.systems.applications import DecisionView

log = logging.getLogger("Utility Bot")

class DiscordLogHandler(logging.Handler):
    def __init__(self, queue: asyncio.Queue[Any]) -> None:
        super().__init__()
        self.queue = queue

    @override
    def emit(self, record: logging.LogRecord) -> None:
        with contextlib.suppress(asyncio.QueueFull):
            self.queue.put_nowait(self.format(record))

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# On Ready Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Ready(commands.Cog):
    def __init__(self, bot : commands.Bot) -> None:
        self.bot                                 = bot
        self._ran                                = False
        self._console_queue : asyncio.Queue[Any] = asyncio.Queue(maxsize=500)
        self._console_task  : asyncio.Task[Any] | None = None

    async def console_worker(self) -> None:
        await self.bot.wait_until_ready()
        try:
            channel = await self.bot.fetch_channel(BOT_CONSOLE_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return
        if not isinstance(channel, discord.TextChannel):
            return

        while True:
            msg: str = await self._console_queue.get()
            buffer: list[str] = [msg]

            deadline = asyncio.get_event_loop().time() + 1.5
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    extra: str = await asyncio.wait_for(
                        self._console_queue.get(), timeout = remaining,
                    )
                    buffer.append(extra)
                except TimeoutError:
                    break

            text = "\n".join(buffer)
            chunks: list[str] = []
            while text:
                n_1900 = 1900
                if len(text) <= n_1900:
                    chunks.append(text)
                    break
                split_at = text.rfind("\n", 0, 1900)
                if split_at == -1:
                    split_at = 1900
                chunks.append(text[:split_at])
                text = text[split_at:].lstrip("\n")

            for chunk in chunks:
                if not chunk.strip():
                    continue
                try:
                    _ = await channel.send(f"```\n{chunk}\n```")
                except discord.HTTPException as e:
                    log.warning("Console channel send failed: %s", e)
                await asyncio.sleep(1.0)

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
            _ = await dm.send(
                f"**{ACCEPTED_EMOJI_ID} Successfully resumed application after restart.**\n"
                f"{question}",
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
                self.bot.add_view(DecisionView(), message_id = msg.id)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._ran:
            return
        self._ran = True
        _ = await bot.tree.sync()

        loop = asyncio.get_running_loop()
        loop.set_exception_handler(
            lambda _loop, context: self.bot.dispatch("asyncio_error", context),
        )
        handler = DiscordLogHandler(self._console_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logging.getLogger().addHandler(handler)
        self._console_task = asyncio.create_task(self.console_worker())
        load_active_applications()
        load_automod_strikes()
        save_automod_strikes()
        await self.restore_application_views()
        await self.resume_incomplete_applications()

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(Ready(bot))
