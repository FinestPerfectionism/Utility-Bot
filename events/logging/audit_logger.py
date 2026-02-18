import discord
from discord.ext import commands

from datetime import datetime, UTC
import asyncio

from constants import (
    DIRECTORSHIP_CATEGORY_ID,

    DIRECTOR_TOPICS_CHANNEL_ID,
    CHANGE_LOG_CHANNEL_ID,

    DIRECTORS_ROLE_ID,
    COLOR_RED,
    COLOR_YELLOW,
    COLOR_GREEN,
    COLOR_BLURPLE
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Changes Handling
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class AuditLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = CHANGE_LOG_CHANNEL_ID

    async def get_log_channel(self, guild):
        channel = guild.get_channel(self.log_channel_id)
        if not channel:
            print(f"Warning: Logging channel {self.log_channel_id} not found in {guild.name}")
        return channel

    def is_directorship_channel(self, channel):
        if hasattr(channel, 'category_id') and channel.category_id == DIRECTORSHIP_CATEGORY_ID:
            return True
        if hasattr(channel, 'category') and channel.category and channel.category.id == DIRECTORSHIP_CATEGORY_ID:
            return True
        return False

    async def get_executor(self, guild, action_type, target_id=None):
        try:
            await asyncio.sleep(0.5)
            async for entry in guild.audit_logs(limit=10, action=action_type):
                if target_id is None or entry.target.id == target_id:
                    return entry.user
        except Exception:
            pass
        return None

    def format_permissions(self, permissions):
        if not permissions:
            return "None"

        perms = []
        for perm, value in permissions:
            if value is not None:
                status = "Allow" if value else "Deny"
                perm_name = perm.replace('_', ' ').title()
                perms.append(f"{perm_name}: {status}")

        return "\n".join(perms) if perms else "None"

    def get_overwrite_changes(self, before_overwrites, after_overwrites):
        changes = []

        all_targets = set(before_overwrites.keys()) | set(after_overwrites.keys())

        for target in all_targets:
            before_ow = before_overwrites.get(target)
            after_ow = after_overwrites.get(target)

            target_type = "Role" if isinstance(target, discord.Role) else "Member"
            target_name = target.name if hasattr(target, 'name') else str(target)
            target_id = target.id if hasattr(target, 'id') else "Unknown"

            if before_ow is None:
                perms = []
                for perm, value in after_ow:
                    if value is not None:
                        status = "Allow" if value else "Deny"
                        perms.append(f"{perm.replace('_', ' ').title()}: {status}")
                if perms:
                    changes.append(f"**Added {target_type}** `{target_name}`\n`{target_id}`\n" + "\n".join(perms))

            elif after_ow is None:
                changes.append(f"**Removed {target_type}** `{target_name}`\n`{target_id}`")

            else:
                before_perms = {perm: value for perm, value in before_ow}
                after_perms = {perm: value for perm, value in after_ow}

                modified_perms = []
                for perm in set(before_perms.keys()) | set(after_perms.keys()):
                    before_val = before_perms.get(perm)
                    after_val = after_perms.get(perm)

                    if before_val != after_val:
                        perm_name = perm.replace('_', ' ').title()
                        before_status = "Allow" if before_val else ("Deny" if before_val is False else "Neutral")
                        after_status = "Allow" if after_val else ("Deny" if after_val is False else "Neutral")
                        modified_perms.append(f"{perm_name}: {before_status} → {after_status}")

                if modified_perms:
                    changes.append(f"**Modified {target_type}** `{target_name}`\n`{target_id}`\n" + "\n".join(modified_perms))

        return changes

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if self.is_directorship_channel(channel):
            return

        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return

        executor = await self.get_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)

        embed = discord.Embed(
            title="Channel Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        channel_type = str(channel.type).replace('_', ' ').title()
        embed.add_field(
            name="Channel",
            value=f"`{channel.name}`\n`{channel.id}`",
            inline=True
        )
        embed.add_field(name="Type", value=channel_type, inline=True)

        if hasattr(channel, 'category') and channel.category:
            embed.add_field(
                name="Category",
                value=f"`{channel.category.name}`\n`{channel.category.id}`",
                inline=True
            )

        if hasattr(channel, 'position'):
            embed.add_field(name="Position", value=str(channel.position), inline=True)

        if executor:
            embed.add_field(
                name="Created By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if self.is_directorship_channel(channel):
            return

        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return

        executor = await self.get_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)

        embed = discord.Embed(
            title="Channel Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        channel_type = str(channel.type).replace('_', ' ').title()
        embed.add_field(
            name="Channel",
            value=f"`{channel.name}`\n`{channel.id}`",
            inline=True
        )
        embed.add_field(name="Type", value=channel_type, inline=True)

        if hasattr(channel, 'category') and channel.category:
            embed.add_field(
                name="Category",
                value=f"`{channel.category.name}`\n`{channel.category.id}`",
                inline=True
            )

        if executor:
            embed.add_field(
                name="Deleted By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
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

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_channel = await self.get_log_channel(role.guild)
        if not log_channel:
            return

        executor = await self.get_executor(role.guild, discord.AuditLogAction.role_create, role.id)

        embed = discord.Embed(
            title="Role Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Role",
            value=f"`{role.name}`\n`{role.id}`",
            inline=True
        )
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)

        if executor:
            embed.add_field(
                name="Created By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        permissions_text = self.format_permissions(role.permissions)
        if len(permissions_text) > 1024:
            permissions_text = permissions_text[:1021] + "..."
        embed.add_field(name="Permissions", value=permissions_text, inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_channel = await self.get_log_channel(role.guild)
        if not log_channel:
            return

        executor = await self.get_executor(role.guild, discord.AuditLogAction.role_delete, role.id)

        embed = discord.Embed(
            title="Role Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Role",
            value=f"`{role.name}`\n`{role.id}`",
            inline=True
        )
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)

        if executor:
            embed.add_field(
                name="Deleted By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        log_channel = await self.get_log_channel(after.guild)
        if not log_channel:
            return

        changes = []

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

            perm_changes = []
            for perm in set(before_perms.keys()) | set(after_perms.keys()):
                if before_perms.get(perm) != after_perms.get(perm):
                    perm_name = perm.replace('_', ' ').title()
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
            title="Role Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Role",
            value=f"`{after.name}`\n`{after.id}`",
            inline=False
        )

        for change_name, before_val, after_val in changes:
            if after_val is None:
                embed.add_field(
                    name=f"{change_name} Changed",
                    value=before_val,
                    inline=False
                )
            else:
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

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Member Joined",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Member",
            value=f"`{member}`\n`{member.id}`",
            inline=True
        )
        embed.add_field(
            name="Account Created",
            value=discord.utils.format_dt(member.created_at, style='R'),
            inline=True
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return

        executor = None
        was_kicked = False
        was_banned = False

        try:
            await asyncio.sleep(0.5)
            async for entry in member.guild.audit_logs(limit=5):
                if entry.action == discord.AuditLogAction.kick and entry.target.id == member.id:
                    executor = entry.user
                    was_kicked = True
                    break
                elif entry.action == discord.AuditLogAction.ban and entry.target.id == member.id:
                    executor = entry.user
                    was_banned = True
                    break
        except Exception:
            pass

        if was_kicked:
            title = "Member Kicked"
            color = COLOR_YELLOW
        elif was_banned:
            title = "Member Banned"
            color = COLOR_RED
        else:
            title = "Member Left"
            color = COLOR_YELLOW

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Member",
            value=f"`{member}`\n`{member.id}`",
            inline=True
        )

        if member.joined_at:
            embed.add_field(
                name="Joined Server",
                value=discord.utils.format_dt(member.joined_at, style='R'),
                inline=True
            )

        if executor:
            action_name = "Kicked By" if was_kicked else "Banned By"
            embed.add_field(
                name=action_name,
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.ban, user.id)

        embed = discord.Embed(
            title="Member Banned",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="User",
            value=f"`{user}`\n`{user.id}`",
            inline=True
        )

        if executor:
            embed.add_field(
                name="Banned By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = await self.get_executor(guild, discord.AuditLogAction.unban, user.id)

        embed = discord.Embed(
            title="Member Unbanned",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="User",
            value=f"`{user}`\n`{user.id}`",
            inline=True
        )

        if executor:
            embed.add_field(
                name="Unbanned By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        log_channel = await self.get_log_channel(after)
        if not log_channel:
            return

        changes = []

        if before.name != after.name:
            changes.append(("Name", before.name, after.name))

        if before.icon != after.icon:
            before_icon = "Set" if before.icon else "None"
            after_icon = "Set" if after.icon else "None"
            changes.append(("Icon", before_icon, after_icon))

        if before.banner != after.banner:
            before_banner = "Set" if before.banner else "None"
            after_banner = "Set" if after.banner else "None"
            changes.append(("Banner", before_banner, after_banner))

        if before.splash != after.splash:
            before_splash = "Set" if before.splash else "None"
            after_splash = "Set" if after.splash else "None"
            changes.append(("Splash", before_splash, after_splash))

        if before.discovery_splash != after.discovery_splash:
            before_disc = "Set" if before.discovery_splash else "None"
            after_disc = "Set" if after.discovery_splash else "None"
            changes.append(("Discovery Splash", before_disc, after_disc))

        if before.description != after.description:
            before_desc = before.description or "None"
            after_desc = after.description or "None"
            changes.append(("Description", before_desc, after_desc))

        if before.verification_level != after.verification_level:
            changes.append(("Verification Level", str(before.verification_level), str(after.verification_level)))

        if before.default_notifications != after.default_notifications:
            changes.append(("Default Notifications", str(before.default_notifications), str(after.default_notifications)))

        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append(("Explicit Content Filter", str(before.explicit_content_filter), str(after.explicit_content_filter)))

        if before.afk_channel != after.afk_channel:
            before_afk = before.afk_channel.name if before.afk_channel else "None"
            after_afk = after.afk_channel.name if after.afk_channel else "None"
            changes.append(("AFK Channel", before_afk, after_afk))

        if before.afk_timeout != after.afk_timeout:
            changes.append(("AFK Timeout", f"{before.afk_timeout}s", f"{after.afk_timeout}s"))

        if before.system_channel != after.system_channel:
            before_sys = before.system_channel.name if before.system_channel else "None"
            after_sys = after.system_channel.name if after.system_channel else "None"
            changes.append(("System Channel", before_sys, after_sys))

        if before.rules_channel != after.rules_channel:
            before_rules = before.rules_channel.name if before.rules_channel else "None"
            after_rules = after.rules_channel.name if after.rules_channel else "None"
            changes.append(("Rules Channel", before_rules, after_rules))

        if before.public_updates_channel != after.public_updates_channel:
            before_pub = before.public_updates_channel.name if before.public_updates_channel else "None"
            after_pub = after.public_updates_channel.name if after.public_updates_channel else "None"
            changes.append(("Public Updates Channel", before_pub, after_pub))

        if before.preferred_locale != after.preferred_locale:
            changes.append(("Preferred Locale", str(before.preferred_locale), str(after.preferred_locale)))

        if before.premium_progress_bar_enabled != after.premium_progress_bar_enabled:
            changes.append(("Boost Progress Bar", str(before.premium_progress_bar_enabled), str(after.premium_progress_bar_enabled)))

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

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        before_ids = {emoji.id for emoji in before}
        after_ids = {emoji.id for emoji in after}

        added_emojis = [emoji for emoji in after if emoji.id not in before_ids]
        removed_emojis = [emoji for emoji in before if emoji.id not in after_ids]

        if not added_emojis and not removed_emojis:
            return

        if added_emojis:
            executor = await self.get_executor(guild, discord.AuditLogAction.emoji_create)

            embed = discord.Embed(
                title="Emoji Created",
                color=COLOR_GREEN,
                timestamp=datetime.now(UTC)
            )

            for emoji in added_emojis:
                embed.add_field(
                    name="Emoji",
                    value=f"`{emoji.name}`\n`{emoji.id}`\n{emoji}",
                    inline=True
                )

            if executor:
                embed.add_field(
                    name="Created By",
                    value=f"`{executor}`\n`{executor.id}`",
                    inline=False
                )

            await log_channel.send(embed=embed)

        if removed_emojis:
            executor = await self.get_executor(guild, discord.AuditLogAction.emoji_delete)

            embed = discord.Embed(
                title="Emoji Deleted",
                color=COLOR_RED,
                timestamp=datetime.now(UTC)
            )

            for emoji in removed_emojis:
                embed.add_field(
                    name="Emoji",
                    value=f"`{emoji.name}`\n`{emoji.id}`",
                    inline=True
                )

            if executor:
                embed.add_field(
                    name="Deleted By",
                    value=f"`{executor}`\n`{executor.id}`",
                    inline=False
                )

            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        before_ids = {sticker.id for sticker in before}
        after_ids = {sticker.id for sticker in after}

        added_stickers = [sticker for sticker in after if sticker.id not in before_ids]
        removed_stickers = [sticker for sticker in before if sticker.id not in after_ids]

        if not added_stickers and not removed_stickers:
            return

        if added_stickers:
            executor = await self.get_executor(guild, discord.AuditLogAction.sticker_create)

            embed = discord.Embed(
                title="Sticker Created",
                color=COLOR_GREEN,
                timestamp=datetime.now(UTC)
            )

            for sticker in added_stickers:
                embed.add_field(
                    name="Sticker",
                    value=f"`{sticker.name}`\n`{sticker.id}`",
                    inline=True
                )

            if executor:
                embed.add_field(
                    name="Created By",
                    value=f"`{executor}`\n`{executor.id}`",
                    inline=False
                )

            await log_channel.send(embed=embed)

        if removed_stickers:
            executor = await self.get_executor(guild, discord.AuditLogAction.sticker_delete)

            embed = discord.Embed(
                title="Sticker Deleted",
                color=COLOR_RED,
                timestamp=datetime.now(UTC)
            )

            for sticker in removed_stickers:
                embed.add_field(
                    name="Sticker",
                    value=f"`{sticker.name}`\n`{sticker.id}`",
                    inline=True
                )

            if executor:
                embed.add_field(
                    name="Deleted By",
                    value=f"`{executor}`\n`{executor.id}`",
                    inline=False
                )

            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        log_channel = await self.get_log_channel(invite.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Invite Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Code", value=f"`{invite.code}`", inline=True)
        embed.add_field(
            name="Channel",
            value=f"`{invite.channel.name}`\n`{invite.channel.id}`",
            inline=True
        )

        if invite.inviter:
            embed.add_field(
                name="Created By",
                value=f"`{invite.inviter}`\n`{invite.inviter.id}`",
                inline=False
            )

        if invite.max_age:
            embed.add_field(name="Expires In", value=f"{invite.max_age}s", inline=True)
        else:
            embed.add_field(name="Expires", value="Never", inline=True)

        if invite.max_uses:
            embed.add_field(name="Max Uses", value=str(invite.max_uses), inline=True)
        else:
            embed.add_field(name="Max Uses", value="Unlimited", inline=True)

        embed.add_field(name="Temporary", value=str(invite.temporary), inline=True)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        log_channel = await self.get_log_channel(invite.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Invite Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Code", value=f"`{invite.code}`", inline=True)
        embed.add_field(
            name="Channel",
            value=f"`{invite.channel.name}`\n`{invite.channel.id}`",
            inline=True
        )

        if invite.uses is not None:
            embed.add_field(name="Uses", value=str(invite.uses), inline=True)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        executor = None
        action_type = None
        target_name = None

        try:
            await asyncio.sleep(0.5)
            async for entry in guild.audit_logs(limit=5):
                if entry.action in [
                    discord.AuditLogAction.integration_create,
                    discord.AuditLogAction.integration_update,
                    discord.AuditLogAction.integration_delete
                ]:
                    executor = entry.user
                    action_type = entry.action
                    if hasattr(entry.target, 'name'):
                        target_name = entry.target.name
                    break
        except Exception as e:
            print(f"Error fetching integration audit log: {e}")

        if action_type == discord.AuditLogAction.integration_create:
            title = "Integration Added"
            color = COLOR_GREEN
        elif action_type == discord.AuditLogAction.integration_delete:
            title = "Integration Removed"
            color = COLOR_RED
        else:
            title = "Integration Updated"
            color = COLOR_BLURPLE

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Server",
            value=f"`{guild.name}`\n`{guild.id}`",
            inline=False
        )

        if target_name:
            embed.add_field(name="Integration", value=f"`{target_name}`", inline=False)

        if executor:
            embed.add_field(
                name="Action By",
                value=f"`{executor}`\n`{executor.id}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if self.is_directorship_channel(thread.parent):
            return

        if thread.parent and thread.parent.id == DIRECTOR_TOPICS_CHANNEL_ID:
            await thread.send(
                content=f"<@&{DIRECTORS_ROLE_ID}>",
                allowed_mentions=discord.AllowedMentions(roles=True)
            )

        log_channel = await self.get_log_channel(thread.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Thread Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Thread",
            value=f"`{thread.name}`\n`{thread.id}`",
            inline=True
        )

        parent = thread.parent
        if parent is None:
            return
        
        embed.add_field(
            name="Parent Channel",
            value=f"`{parent.name}`\n`{parent.id}`",
            inline=True
        )

        if thread.owner:
            embed.add_field(
                name="Created By",
                value=f"`{thread.owner}`\n`{thread.owner.id}`",
                inline=False
            )

        embed.add_field(
            name="Auto Archive Duration",
            value=f"{thread.auto_archive_duration} min",
            inline=True
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        if self.is_directorship_channel(thread.parent):
            return

        log_channel = await self.get_log_channel(thread.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Thread Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Thread",
            value=f"`{thread.name}`\n`{thread.id}`",
            inline=True
        )
        embed.add_field(
            name="Parent Channel",
            value=f"`{thread.parent.name}`\n`{thread.parent.id}`",
            inline=True
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        if self.is_directorship_channel(after.parent):
            return

        log_channel = await self.get_log_channel(after.guild)
        if not log_channel:
            return

        changes = []

        if before.name != after.name:
            changes.append(("Name", before.name, after.name))

        if before.archived != after.archived:
            changes.append(("Archived", str(before.archived), str(after.archived)))

        if before.locked != after.locked:
            changes.append(("Locked", str(before.locked), str(after.locked)))

        if before.auto_archive_duration != after.auto_archive_duration:
            changes.append((
                "Auto Archive Duration",
                f"{before.auto_archive_duration} min",
                f"{after.auto_archive_duration} min"
            ))

        if not changes:
            return

        embed = discord.Embed(
            title="Thread Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Thread",
            value=f"`{after.name}`\n`{after.id}`",
            inline=False
        )

        for change_name, before_val, after_val in changes:
            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** `{before_val}`\n**After:** `{after_val}`",
                inline=False
            )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            log_channel = await self.get_log_channel(after.guild)
            if not log_channel:
                return

            executor = await self.get_executor(after.guild, discord.AuditLogAction.member_update, after.id)

            embed = discord.Embed(
                title="Nickname Changed",
                color=COLOR_BLURPLE,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(
                name="Member",
                value=f"`{after}`\n`{after.id}`",
                inline=False
            )

            before_nick = before.nick or "None"
            after_nick = after.nick or "None"

            embed.add_field(
                name="Nickname Changed",
                value=f"**Before:** `{before_nick}`\n**After:** `{after_nick}`",
                inline=False
            )

            if executor:
                embed.add_field(
                    name="Changed By",
                    value=f"`{executor}`\n`{executor.id}`",
                    inline=False
                )

            await log_channel.send(embed=embed)

        if before.roles != after.roles:
            log_channel = await self.get_log_channel(after.guild)
            if not log_channel:
                return

            executor = await self.get_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)

            before_role_ids = set(role.id for role in before.roles)
            after_role_ids = set(role.id for role in after.roles)

            added_roles = [role for role in after.roles if role.id not in before_role_ids and role.name != "@everyone"]
            removed_roles = [role for role in before.roles if role.id not in after_role_ids and role.name != "@everyone"]

            if not added_roles and not removed_roles:
                return

            embed = discord.Embed(
                title="Member Roles Changed",
                color=COLOR_BLURPLE,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(
                name="Member",
                value=f"`{after}`\n`{after.id}`",
                inline=False
            )

            if added_roles:
                role_list = "\n".join([f"`{role.name}`\n`{role.id}`" for role in added_roles])
                embed.add_field(name="Roles Added", value=role_list, inline=False)

            if removed_roles:
                role_list = "\n".join([f"`{role.name}`\n`{role.id}`" for role in removed_roles])
                embed.add_field(name="Roles Removed", value=role_list, inline=False)

            if executor:
                embed.add_field(
                    name="Changed By",
                    value=f"`{executor}`\n`{executor.id}`",
                    inline=False
                )

            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AuditLogger(bot))