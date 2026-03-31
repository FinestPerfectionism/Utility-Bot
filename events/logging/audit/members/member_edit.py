from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_BLURPLE

from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Member Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MemberEditCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.nick != after.nick:
            log_channel = await self.get_log_channel(after.guild)
            if not log_channel:
                return

            executor = await self.get_executor(after.guild, discord.AuditLogAction.member_update, after.id)

            embed = discord.Embed(
                title = "Nickname Changed",
                color = COLOR_BLURPLE,
                timestamp = datetime.now(UTC),
            )

            _ = embed.add_field(
                name = "Member",
                value = f"`{after}`\n`{after.id}`",
                inline = False,
            )
            _ = embed.add_field(
                name = "Nickname Changed",
                value = f"**Before:** `{before.nick or 'None'}`\n**After:** `{after.nick or 'None'}`",
                inline = False,
            )

            if executor:
                _ = embed.add_field(
                    name = "Changed By",
                    value = f"`{executor}`\n`{executor.id}`",
                    inline = False,
                )

            await self._enqueue(log_channel, embed)

        if before.roles != after.roles:
            log_channel = await self.get_log_channel(after.guild)
            if not log_channel:
                return

            executor = await self.get_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)

            before_role_ids = {role.id for role in before.roles}
            after_role_ids = {role.id for role in after.roles}

            added_roles = [role for role in after.roles if role.id not in before_role_ids and role.name != "@everyone"]
            removed_roles = [role for role in before.roles if role.id not in after_role_ids and role.name != "@everyone"]

            if not added_roles and not removed_roles:
                return

            embed = discord.Embed(
                title = "Member Roles Changed",
                color = COLOR_BLURPLE,
                timestamp = datetime.now(UTC),
            )

            _ = embed.add_field(
                name = "Member",
                value = f"`{after}`\n`{after.id}`",
                inline = False,
            )

            if added_roles:
                role_list = "\n".join([f"`{role.name}`\n`{role.id}`" for role in added_roles])
                _ = embed.add_field(name = "Roles Added", value = role_list, inline = False)

            if removed_roles:
                role_list = "\n".join([f"`{role.name}`\n`{role.id}`" for role in removed_roles])
                _ = embed.add_field(name = "Roles Removed", value = role_list, inline = False)

            if executor:
                _ = embed.add_field(
                    name = "Changed By",
                    value = f"`{executor}`\n`{executor.id}`",
                    inline = False,
                )

            await self._enqueue(log_channel, embed)
