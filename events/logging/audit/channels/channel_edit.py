import discord
from discord.ext import commands
from datetime import datetime, UTC

from constants import COLOR_BLURPLE
from .._base import AuditCog, AuditQueue

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Channel Edit Audit
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ChannelEditCog(AuditCog):
    def __init__(self, bot: commands.Bot, queue: AuditQueue) -> None:
        super().__init__(bot, queue)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after) -> None:
        if self.is_directorship_channel(after):
            return

        log_channel = await self.get_log_channel(after.guild)
        if not log_channel:
            return

        changes = []

        if before.name != after.name:
            changes.append(("Name", before.name, after.name))

        if hasattr(before, 'position') and before.position != after.position:
            changes.append(("Position", str(before.position), str(after.position)))

        if hasattr(before, 'category'):
            before_cat = before.category.name if before.category else "None"
            after_cat = after.category.name if after.category else "None"
            if before_cat != after_cat:
                changes.append(("Category", before_cat, after_cat))

        if hasattr(before, 'topic'):
            before_topic = before.topic or "None"
            after_topic = after.topic or "None"
            if before_topic != after_topic:
                changes.append(("Topic", before_topic, after_topic))

        if hasattr(before, 'nsfw') and before.nsfw != after.nsfw:
            changes.append(("NSFW", str(before.nsfw), str(after.nsfw)))

        if hasattr(before, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            changes.append(("Slowmode Delay", f"{before.slowmode_delay}s", f"{after.slowmode_delay}s"))

        if hasattr(before, 'bitrate') and before.bitrate != after.bitrate:
            changes.append(("Bitrate", f"{before.bitrate}bps", f"{after.bitrate}bps"))

        if hasattr(before, 'user_limit') and before.user_limit != after.user_limit:
            before_limit = "Unlimited" if before.user_limit == 0 else str(before.user_limit)
            after_limit = "Unlimited" if after.user_limit == 0 else str(after.user_limit)
            changes.append(("User Limit", before_limit, after_limit))

        if hasattr(before, 'rtc_region'):
            before_region = before.rtc_region or "Automatic"
            after_region = after.rtc_region or "Automatic"
            if before_region != after_region:
                changes.append(("Voice Region", before_region, after_region))

        if hasattr(before, 'video_quality_mode') and before.video_quality_mode != after.video_quality_mode:
            changes.append(("Video Quality", str(before.video_quality_mode), str(after.video_quality_mode)))

        if hasattr(before, 'default_auto_archive_duration'):
            if before.default_auto_archive_duration != after.default_auto_archive_duration:
                changes.append((
                    "Auto Archive Duration",
                    f"{before.default_auto_archive_duration} min",
                    f"{after.default_auto_archive_duration} min"
                ))

        overwrite_changes = []
        if hasattr(before, 'overwrites') and before.overwrites != after.overwrites:
            overwrite_changes = self.get_overwrite_changes(before.overwrites, after.overwrites)

        if not changes and not overwrite_changes:
            return

        executor = await self.get_executor(after.guild, discord.AuditLogAction.channel_update, after.id)

        embed = discord.Embed(
            title="Channel Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Channel",
            value=f"`{after.name}`\n`{after.id}`",
            inline=False
        )

        for change_name, before_val, after_val in changes:
            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** `{before_val}`\n**After:** `{after_val}`",
                inline=False
            )

        if overwrite_changes:
            for i, change in enumerate(overwrite_changes):
                if len(change) > 1024:
                    change = change[:1021] + "..."
                embed.add_field(
                    name="Permission Overwrite Changed" if i == 0 else "\u200b",
                    value=change,
                    inline=False
                )

        if executor:
            embed.add_field(
                name="Changed By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)
