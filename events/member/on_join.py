import discord
from discord.ext import commands

from datetime import datetime
from typing import cast

from events.member.verification import VerificationHandler

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# On Join Event
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberJoinHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        verification_cog = cast(VerificationHandler, self.bot.get_cog("VerificationHandler"))
        if not verification_cog:
            return

        goobers_role = member.guild.get_role(verification_cog.GOOBERS_ROLE_ID)
        if goobers_role and goobers_role in member.roles:
            return

        verification_cog.data["unverified"][str(member.id)] = {
            "joined_at": datetime.now().isoformat(),
            "warned": False,
            "warning_message_id": None
        }
        verification_cog.save_data()

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberJoinHandler(bot))