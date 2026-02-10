import discord
from discord.ext import (
    commands,
    tasks
)

import logging

from core.state import (
    load_layout_message_ids,
    save_layout_message_ids
)
from core.utils import MESSAGE_LOG_QUEUE

from events.systems.applications import ApplicationComponents
from events.systems.tickets import TicketComponents
from events.systems.leave import LeaveComponents

from constants import (
    TICKET_CHANNEL_ID,
    APPLICATION_CHANNEL_ID,
    STAFF_LEAVE_CHANNEL_ID,
    MESSAGE_SEND_LOG_CHANNEL_ID,
)

log = logging.getLogger("utilitybot")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Startup Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class Startup(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process_message_logs.start()
        self.layout_message_ids = load_layout_message_ids()

    async def restore_or_send_layouts(self):
        view_mapping = {
            "tickets": (TICKET_CHANNEL_ID, TicketComponents),
            "applications": (APPLICATION_CHANNEL_ID, ApplicationComponents),
            "leave": (STAFF_LEAVE_CHANNEL_ID, LeaveComponents)
        }

        for key, (channel_id, view_cls) in view_mapping.items():
            channel = self.bot.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue

            msg_id = self.layout_message_ids.get(key)
            if msg_id:
                try:
                    await channel.fetch_message(msg_id)
                    self.bot.add_view(view_cls(), message_id=msg_id)
                    continue
                except discord.NotFound:
                    pass

            msg = await channel.send(view=view_cls())
            self.layout_message_ids[key] = msg.id
            self.bot.add_view(view_cls(), message_id=msg.id)
            save_layout_message_ids(self.layout_message_ids)

    async def cog_unload(self):
        self.process_message_logs.cancel()

    @tasks.loop(seconds=1)
    async def process_message_logs(self):
        while not MESSAGE_LOG_QUEUE.empty():
            embed = await MESSAGE_LOG_QUEUE.get()
            channel = self.bot.get_channel(MESSAGE_SEND_LOG_CHANNEL_ID)

            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

    @process_message_logs.before_loop
    async def before_logs(self):
        await self.bot.wait_until_ready()
        await self.restore_or_send_layouts()

async def setup(bot: commands.Bot):
    await bot.add_cog(Startup(bot))