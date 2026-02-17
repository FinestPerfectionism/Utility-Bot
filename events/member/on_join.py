import discord
from discord.ext import commands

from datetime import datetime
from typing import cast

from events.member.verification import VerificationHandler

from commands.moderation.quarantine import QuarantineCommands

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

        quarantine_cog = cast(
            QuarantineCommands,
            self.bot.get_cog("QuarantineCommands")
        )

        if quarantine_cog and str(member.id) in quarantine_cog.data["quarantined"]:
            quarantine_role = member.guild.get_role(
                quarantine_cog.QUARANTINE_ROLE_ID
            )
            if quarantine_role:
                try:
                    await member.add_roles(
                        quarantine_role,
                        reason="UB Quarantine: rejoined while quarantined"
                    )
                except discord.Forbidden:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(MemberJoinHandler(bot))