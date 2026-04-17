import contextlib
from typing import TYPE_CHECKING, cast

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from commands.moderation.primary._group_cog import ModerationCommands

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# On Join Event
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberJoinHandler(commands.Cog):
    def __init__(self, bot : commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member) -> None:
        quarantine_cog = cast(
            "ModerationCommands",
            self.bot.get_cog("QuarantineCommands"),
        )

        if quarantine_cog and str(member.id) in quarantine_cog.data["quarantined"]:
            quarantine_role = member.guild.get_role(
                quarantine_cog.QUARANTINE_ROLE_ID,
            )
            if quarantine_role:
                with contextlib.suppress(discord.Forbidden):
                    await member.add_roles(
                        quarantine_role,
                        reason = "UB Quarantine: rejoined while quarantined",
                    )

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(MemberJoinHandler(bot))
