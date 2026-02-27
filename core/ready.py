import discord
from discord.ext import commands
import asyncio
import logging
import sys
import io
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
    BOT_CONSOLE_CHANNEL_ID,
)
log = logging.getLogger("Utility Bot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Console Mirror
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class DiscordStream(io.TextIOBase):
    def __init__(self, queue: asyncio.Queue, original_stream):
        self.queue = queue
        self.original = original_stream
        self.buffer = ""

    def write(self, message: str):
        self.original.write(message)
        self.original.flush()
        if message.strip():
            self.buffer += message
            if "\n" in self.buffer:
                lines = self.buffer.split("\n")
                self.buffer = lines[-1]
                to_send = "\n".join(lines[:-1])
                if to_send.strip():
                    try:
                        self.queue.put_nowait(to_send)
                    except asyncio.QueueFull:
                        pass
        return len(message)

async def console_sender(bot: commands.Bot, queue: asyncio.Queue) -> None:
    await bot.wait_until_ready()
    channel = bot.get_channel(BOT_CONSOLE_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return
    pending = []
    while True:
        try:
            line = await asyncio.wait_for(queue.get(), timeout=2.0)
            pending.append(line)
            while not queue.empty():
                pending.append(queue.get_nowait())
        except asyncio.TimeoutError:
            pass
        if pending:
            combined = "\n".join(pending)
            chunks = [combined[i:i+1990] for i in range(0, len(combined), 1990)]
            for chunk in chunks:
                try:
                    await channel.send(f"```\n{chunk}\n```")
                except discord.HTTPException:
                    pass
            pending.clear()
            await asyncio.sleep(1.5)
            
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# On Ready Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Ready(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ran = False
        self._console_queue: asyncio.Queue = asyncio.Queue(maxsize=500)

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
        sys.stdout = DiscordStream(self._console_queue, sys.__stdout__)
        sys.stderr = DiscordStream(self._console_queue, sys.__stderr__)
        asyncio.create_task(console_sender(self.bot, self._console_queue))
        load_active_applications()
        load_automod_strikes()
        save_automod_strikes()
        await self.restore_application_views()
        await self.resume_incomplete_applications()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ready(bot))