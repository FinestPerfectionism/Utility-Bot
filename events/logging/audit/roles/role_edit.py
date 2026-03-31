from datetime import UTC, datetime

import discord
from discord.ext import commands

from constants import COLOR_BLURPLE

from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class RoleEditCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        log_channel = await self.get_log_channel(after.guild)
        if not log_channel:
            return

        changes: list[tuple[str, str, str | None]] = []

        if before.name != after.name:
            changes.append(("Name", before.name, after.name))

        if before.color != after.color:
            changes.append(("Color", str(before.color), str(after.color)))

        if before.hoist != after.hoist:
            changes.append(("Hoisted", str(before.hoist), str(after.hoist)))

        if before.mentionable != after.mentionable:
            changes.append(("Mentionable", str(before.mentionable), str(after.mentionable)))

        if before.position != after.position:
            changes.append(("Position", str(before.position), str(after.position)))

        if before.permissions != after.permissions:
            before_perms = dict(before.permissions)
            after_perms = dict(after.permissions)

            perm_changes: list[str] = []
            for perm in set(before_perms.keys()) | set(after_perms.keys()):
                if before_perms.get(perm) != after_perms.get(perm):
                    perm_name = perm.replace("_", " ").title()
                    before_status = "Enabled" if before_perms.get(perm) else "Disabled"
                    after_status = "Enabled" if after_perms.get(perm) else "Disabled"
                    perm_changes.append(f"{perm_name}: {before_status} → {after_status}")

            if perm_changes:
                perm_text = "\n".join(perm_changes)
                if len(perm_text) > 1024:
                    perm_text = perm_text[:1021] + "..."
                changes.append(("Permissions", perm_text, None))

        if not changes:
            return

        executor = await self.get_executor(after.guild, discord.AuditLogAction.role_update, after.id)

        embed = discord.Embed(
            title = "Role Updated",
            color = COLOR_BLURPLE,
            timestamp = datetime.now(UTC),
        )

        _ = embed.add_field(
            name = "Role",
            value = f"`{after.name}`\n`{after.id}`",
            inline = False,
        )

        change_name: str
        before_val: str
        after_val: str | None
        for change_name, before_val, after_val in changes:
            if after_val is None:
                _ = embed.add_field(
                    name = f"{change_name} Changed",
                    value = before_val,
                    inline = False,
                )
            else:
                _ = embed.add_field(
                    name = f"{change_name} Changed",
                    value = f"**Before:** `{before_val}`\n**After:** `{after_val}`",
                    inline = False,
                )

        if executor:
            _ = embed.add_field(
                name = "Changed By",
                value = f"`{executor}`\n`{executor.id}`",
                inline = False,
            )

        await self._enqueue(log_channel, embed)
