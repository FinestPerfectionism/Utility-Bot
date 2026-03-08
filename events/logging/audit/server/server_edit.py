import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_BLURPLE
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Server Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ServerEditCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        log_channel = await self.get_log_channel(after)
        if not log_channel:
            return

        changes: list[tuple[str, str | int | None, str | int | None]] = []

        if before.name != after.name:
            changes.append(("Name", before.name, after.name))

        if before.icon != after.icon:
            changes.append(("Icon", "Set" if before.icon else "None", "Set" if after.icon else "None"))

        if before.banner != after.banner:
            changes.append(("Banner", "Set" if before.banner else "None", "Set" if after.banner else "None"))

        if before.splash != after.splash:
            changes.append(("Splash", "Set" if before.splash else "None", "Set" if after.splash else "None"))

        if before.discovery_splash != after.discovery_splash:
            changes.append((
                "Discovery Splash",
                "Set" if before.discovery_splash else "None",
                "Set" if after.discovery_splash else "None"
            ))

        if before.description != after.description:
            changes.append(("Description", before.description or "None", after.description or "None"))

        if before.verification_level != after.verification_level:
            changes.append(("Verification Level", str(before.verification_level), str(after.verification_level)))

        if before.default_notifications != after.default_notifications:
            changes.append(("Default Notifications", str(before.default_notifications), str(after.default_notifications)))

        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append(("Explicit Content Filter", str(before.explicit_content_filter), str(after.explicit_content_filter)))

        if before.afk_channel != after.afk_channel:
            changes.append((
                "AFK Channel",
                before.afk_channel.name if before.afk_channel else "None",
                after.afk_channel.name if after.afk_channel else "None"
            ))

        if before.afk_timeout != after.afk_timeout:
            changes.append(("AFK Timeout", f"{before.afk_timeout}s", f"{after.afk_timeout}s"))

        if before.system_channel != after.system_channel:
            changes.append((
                "System Channel",
                before.system_channel.name if before.system_channel else "None",
                after.system_channel.name if after.system_channel else "None"
            ))

        if before.rules_channel != after.rules_channel:
            changes.append((
                "Rules Channel",
                before.rules_channel.name if before.rules_channel else "None",
                after.rules_channel.name if after.rules_channel else "None"
            ))

        if before.public_updates_channel != after.public_updates_channel:
            changes.append((
                "Public Updates Channel",
                before.public_updates_channel.name if before.public_updates_channel else "None",
                after.public_updates_channel.name if after.public_updates_channel else "None"
            ))

        if before.preferred_locale != after.preferred_locale:
            changes.append(("Preferred Locale", str(before.preferred_locale), str(after.preferred_locale)))

        if before.premium_progress_bar_enabled != after.premium_progress_bar_enabled:
            changes.append((
                "Boost Progress Bar",
                str(before.premium_progress_bar_enabled),
                str(after.premium_progress_bar_enabled)
            ))

        if not changes:
            return

        executor = await self.get_executor(after, discord.AuditLogAction.guild_update)

        embed = discord.Embed(
            title="Server Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Server",
            value=f"`{after.name}`\n`{after.id}`",
            inline=False
        )

        change_name: str
        before_val: str | int | None
        after_val: str | int | None
        for change_name, before_val, after_val in changes:
            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** `{before_val}`\n**After:** `{after_val}`",
                inline=False
            )

        if executor:
            embed.add_field(
                name="Changed By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)
