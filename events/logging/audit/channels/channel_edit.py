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
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel) -> None:
        if self.is_directorship_channel(after):
            return

        log_channel: discord.TextChannel | None = await self.get_log_channel(after.guild)
        if not log_channel:
            return

        changes: list[tuple[str, str, str]] = []

        if before.name != after.name:
            changes.append(("Name", str(before.name), str(after.name)))

        before_pos = getattr(before, 'position', None)
        after_pos = getattr(after, 'position', None)
        if before_pos is not None and before_pos != after_pos:
            changes.append(("Position", str(before_pos), str(after_pos)))

        before_cat = getattr(before, 'category', None)
        after_cat = getattr(after, 'category', None)
        before_cat_name = before_cat.name if before_cat else "None"
        after_cat_name = after_cat.name if after_cat else "None"
        if before_cat_name != after_cat_name:
            changes.append(("Category", before_cat_name, after_cat_name))

        before_topic = getattr(before, 'topic', "None") or "None"
        after_topic = getattr(after, 'topic', "None") or "None"
        if before_topic != after_topic:
            changes.append(("Topic", str(before_topic), str(after_topic)))

        before_nsfw = getattr(before, 'nsfw', None)
        after_nsfw = getattr(after, 'nsfw', None)
        if before_nsfw is not None and before_nsfw != after_nsfw:
            changes.append(("NSFW", str(before_nsfw), str(after_nsfw)))

        before_slow = getattr(before, 'slowmode_delay', None)
        after_slow = getattr(after, 'slowmode_delay', None)
        if before_slow is not None and before_slow != after_slow:
            changes.append(("Slowmode Delay", f"{before_slow}s", f"{after_slow}s"))

        before_br = getattr(before, 'bitrate', None)
        after_br = getattr(after, 'bitrate', None)
        if before_br is not None and before_br != after_br:
            changes.append(("Bitrate", f"{before_br}bps", f"{after_br}bps"))

        before_ul = getattr(before, 'user_limit', None)
        after_ul = getattr(after, 'user_limit', None)
        if before_ul is not None and before_ul != after_ul:
            before_limit = "Unlimited" if before_ul == 0 else str(before_ul)
            after_limit = "Unlimited" if after_ul == 0 else str(after_ul)
            changes.append(("User Limit", before_limit, after_limit))

        before_region = getattr(before, 'rtc_region', "Automatic") or "Automatic"
        after_region = getattr(after, 'rtc_region', "Automatic") or "Automatic"
        if before_region != after_region:
            changes.append(("Voice Region", str(before_region), str(after_region)))

        before_vq = getattr(before, 'video_quality_mode', None)
        after_vq = getattr(after, 'video_quality_mode', None)
        if before_vq is not None and before_vq != after_vq:
            changes.append(("Video Quality", str(before_vq), str(after_vq)))

        before_arch = getattr(before, 'default_auto_archive_duration', None)
        after_arch = getattr(after, 'default_auto_archive_duration', None)
        if before_arch is not None and before_arch != after_arch:
            changes.append(("Auto Archive Duration", f"{before_arch} min", f"{after_arch} min"))

        overwrite_changes: list[str] = []
        before_ow = getattr(before, 'overwrites', None)
        after_ow = getattr(after, 'overwrites', None)
        if before_ow is not None and after_ow is not None and before_ow != after_ow:
            overwrite_changes = self.get_overwrite_changes(before_ow, after_ow)

        if not changes and not overwrite_changes:
            return

        executor: discord.Member | None = await self.get_executor(after.guild, discord.AuditLogAction.channel_update, after.id)

        embed: discord.Embed = discord.Embed(
            title="Channel Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Channel",
            value=f"`{after.name}`\n`{after.id}`",
            inline=False
        )

        for change_name, b_val, a_val in changes:
            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** `{b_val}`\n**After:** `{a_val}`",
                inline=False
            )

        for i, change_text in enumerate(overwrite_changes):
            field_value = change_text if len(change_text) <= 1024 else f"{change_text[:1021]}..."
            embed.add_field(
                name="Permission Overwrite Changed" if i == 0 else "\u200b",
                value=field_value,
                inline=False
            )

        if executor:
            embed.add_field(
                name="Changed By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await self._enqueue(log_channel, embed)