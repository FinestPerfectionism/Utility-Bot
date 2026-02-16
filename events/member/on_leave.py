import discord
from discord.ext import commands

from typing import cast

from commands.moderation.quarantine import QuarantineCommands

from events.member.verification import VerificationHandler

from core.state import (
    ACTIVE_APPLICATIONS,
    save_active_applications
)

from constants import (
    APPLICATION_LOG_CHANNEL_ID,
    COLOR_RED
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# On Leave Event
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberLeaveHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        verification_cog = cast(VerificationHandler, self.bot.get_cog("VerificationHandler"))
        if verification_cog:
            verification_cog.data["unverified"].pop(str(member.id), None)
            verification_cog.save_data()

        quarantine_cog = cast(
            QuarantineCommands,
            self.bot.get_cog("QuarantineCommands")
        )

        if quarantine_cog:
            quarantine_cog.data["quarantined"].pop(str(member.id), None)
            quarantine_cog.save_data()
            
        data = ACTIVE_APPLICATIONS.get(member.id)
        if not data:
            return

        log_channel = self.bot.get_channel(APPLICATION_LOG_CHANNEL_ID)
        if not isinstance(log_channel, discord.TextChannel):
            return

        message_id = data.get("log_message_id")
        if not message_id:
            return

        try:
            msg = await log_channel.fetch_message(message_id)
        except discord.NotFound:
            return

        embed = discord.Embed(
            title=msg.embeds[0].title if msg.embeds else "Application Decision",
            color=COLOR_RED,
        )

        embed.add_field(name="Decision", value="Denied", inline=True)
        embed.add_field(name="Handled By", value="*Automatic*", inline=True)
        embed.add_field(
            name="Decision Notes",
            value="*Applicant left the server.*",
            inline=False,
        )

        embed.set_footer(text="Decision Made")
        embed.timestamp = discord.utils.utcnow()

        await msg.edit(embed=embed, view=None)

        thread_id = data.get("thread_id")
        if thread_id:
            try:
                channel = await self.bot.fetch_channel(thread_id)
                if isinstance(channel, discord.Thread):
                    await channel.edit(locked=True, archived=True)
            except discord.NotFound:
                pass

        ACTIVE_APPLICATIONS.pop(member.id, None)
        save_active_applications()

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberLeaveHandler(bot))