import discord
from discord.ext import commands

from datetime import datetime, UTC
import asyncio

from constants import (
    CHANGE_LOG_CHANNEL_ID,

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

    async def get_executor(self, guild, action_type, target_id=None):
        try:
            await asyncio.sleep(0.5)
            async for entry in guild.audit_logs(limit=10, action=action_type):
                if target_id is None or entry.target.id == target_id:
                    return entry.user
        except():
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

    def format_overwrites(self, overwrites):
        if not overwrites:
            return "None"

        result = []
        for target, overwrite in overwrites.items():
            target_type = "Role" if isinstance(target, discord.Role) else "Member"
            target_name = target.name if hasattr(target, 'name') else str(target)

            perms = []
            for perm, value in overwrite:
                if value is not None:
                    status = "Allow" if value else "Deny"
                    perms.append(f"{perm.replace('_', ' ').title()}: {status}")

            if perms:
                result.append(f"{target_type} '{target_name}':\n  " + "\n  ".join(perms))

        return "\n".join(result) if result else "None"

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
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
        embed.add_field(name="Channel Name", value=channel.name, inline=True)
        embed.add_field(name="Channel Type", value=channel_type, inline=True)
        embed.add_field(name="Channel ID", value=channel.id, inline=True)

        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)

        if hasattr(channel, 'position'):
            embed.add_field(name="Position", value=channel.position, inline=True)

        if executor:
            embed.add_field(name="Created By", value=f"{executor.name} ({executor.id})", inline=False)

        if hasattr(channel, 'overwrites'):
            overwrites_text = self.format_overwrites(channel.overwrites)
            if len(overwrites_text) > 1024:
                overwrites_text = overwrites_text[:1021] + "..."
            embed.add_field(name="Permission Overwrites", value=overwrites_text, inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
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
        embed.add_field(name="Channel Name", value=channel.name, inline=True)
        embed.add_field(name="Channel Type", value=channel_type, inline=True)
        embed.add_field(name="Channel ID", value=channel.id, inline=True)

        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)

        if executor:
            embed.add_field(name="Deleted By", value=f"{executor.name} ({executor.id})", inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        
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

        if hasattr(before, 'overwrites') and before.overwrites != after.overwrites:
            before_overwrites = self.format_overwrites(before.overwrites)
            after_overwrites = self.format_overwrites(after.overwrites)
            if before_overwrites != after_overwrites:
                changes.append(("Permission Overwrites", before_overwrites, after_overwrites))

        if hasattr(before, 'default_auto_archive_duration'):
            if before.default_auto_archive_duration != after.default_auto_archive_duration:
                changes.append((
                    "Auto Archive Duration",
                    f"{before.default_auto_archive_duration} min",
                    f"{after.default_auto_archive_duration} min"
                ))

        if not changes:
            return

        executor = await self.get_executor(after.guild, discord.AuditLogAction.channel_update, after.id)

        embed = discord.Embed(
            title="Channel Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Channel", value=f"{after.name} ({after.id})", inline=False)

        for change_name, before_val, after_val in changes:
            if len(str(before_val)) > 500:
                before_val = str(before_val)[:497] + "..."
            if len(str(after_val)) > 500:
                after_val = str(after_val)[:497] + "..."

            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** {before_val}\n**After:** {after_val}",
                inline=False
            )

        if executor:
            embed.add_field(name="Changed By", value=f"{executor.name} ({executor.id})", inline=False)

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

        embed.add_field(name="Role Name", value=role.name, inline=True)
        embed.add_field(name="Role ID", value=role.id, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)

        perms = [perm[0].replace('_', ' ').title() for perm in role.permissions if perm[1]]
        perms_text = ", ".join(perms) if perms else "None"
        if len(perms_text) > 1024:
            perms_text = perms_text[:1021] + "..."
        embed.add_field(name="Permissions", value=perms_text, inline=False)

        if executor:
            embed.add_field(name="Created By", value=f"{executor.name} ({executor.id})", inline=False)

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

        embed.add_field(name="Role Name", value=role.name, inline=True)
        embed.add_field(name="Role ID", value=role.id, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)

        if executor:
            embed.add_field(name="Deleted By", value=f"{executor.name} ({executor.id})", inline=False)
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
        
        if before.position != after.position:
            changes.append(("Position", str(before.position), str(after.position)))

        if before.hoist != after.hoist:
            changes.append(("Hoisted", str(before.hoist), str(after.hoist)))
        
        if before.mentionable != after.mentionable:
            changes.append(("Mentionable", str(before.mentionable), str(after.mentionable)))
        
        if before.permissions != after.permissions:
            before_perms = [perm[0].replace('_', ' ').title() for perm in before.permissions if perm[1]]
            after_perms = [perm[0].replace('_', ' ').title() for perm in after.permissions if perm[1]]

            added_perms = set(after_perms) - set(before_perms)
            removed_perms = set(before_perms) - set(after_perms)

            if added_perms or removed_perms:
                perm_change = ""
                if added_perms:
                    perm_change += f"Added: {', '.join(added_perms)}"
                if removed_perms:
                    if perm_change:
                        perm_change += "\n"
                    perm_change += f"Removed: {', '.join(removed_perms)}"
                changes.append(("Permissions", "Changed", perm_change))
        
        if hasattr(before, 'icon') and before.icon != after.icon:
            before_icon = "Set" if before.icon else "None"
            after_icon = "Set" if after.icon else "None"
            changes.append(("Icon", before_icon, after_icon))
        
        if hasattr(before, 'unicode_emoji'):
            before_emoji = before.unicode_emoji or "None"
            after_emoji = after.unicode_emoji or "None"
            if before_emoji != after_emoji:
                changes.append(("Unicode Emoji", before_emoji, after_emoji))

        if not changes:
            return

        executor = await self.get_executor(after.guild, discord.AuditLogAction.role_update, after.id)

        embed = discord.Embed(
            title="Role Updated",
            color=COLOR_BLURPLE,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Role", value=f"{after.name} ({after.id})", inline=False)

        for change_name, before_val, after_val in changes:
            if len(str(before_val)) > 500:
                before_val = str(before_val)[:497] + "..."
            if len(str(after_val)) > 500:
                after_val = str(after_val)[:497] + "..."

            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** {before_val}\n**After:** {after_val}",
                inline=False
            )

        if executor:
            embed.add_field(name="Changed By", value=f"{executor.name} ({executor.id})", inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        
        log_channel = await self.get_log_channel(after)
        if not log_channel:
            return

        changes = []

        if before.name != after.name:
            changes.append(("Server Name", before.name, after.name))
        
        if before.icon != after.icon:
            before_icon = "Set" if before.icon else "None"
            after_icon = "Set" if after.icon else "None"
            changes.append(("Server Icon", before_icon, after_icon))
        
        if before.banner != after.banner:
            before_banner = "Set" if before.banner else "None"
            after_banner = "Set" if after.banner else "None"
            changes.append(("Server Banner", before_banner, after_banner))
        
        if before.splash != after.splash:
            before_splash = "Set" if before.splash else "None"
            after_splash = "Set" if after.splash else "None"
            changes.append(("Invite Splash", before_splash, after_splash))
        
        if before.discovery_splash != after.discovery_splash:
            before_disc = "Set" if before.discovery_splash else "None"
            after_disc = "Set" if after.discovery_splash else "None"
            changes.append(("Discovery Splash", before_disc, after_disc))
        
        if before.description != after.description:
            before_desc = before.description or "None"
            after_desc = after.description or "None"
            changes.append(("Description", before_desc, after_desc))

        if before.verification_level != after.verification_level:
            changes.append((
                "Verification Level",
                str(before.verification_level),
                str(after.verification_level)
            ))
            
        if before.default_notifications != after.default_notifications:
            changes.append((
                "Default Notifications",
                str(before.default_notifications),
                str(after.default_notifications)
            ))

        
        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append((
                "Explicit Content Filter",
                str(before.explicit_content_filter),
                str(after.explicit_content_filter)
            ))

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

        
        if before.system_channel_flags != after.system_channel_flags:
            changes.append((
                "System Channel Flags",
                str(before.system_channel_flags.value),
                str(after.system_channel_flags.value)
            ))

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

        if hasattr(before, 'premium_progress_bar_enabled'):
            if before.premium_progress_bar_enabled != after.premium_progress_bar_enabled:
                changes.append((
                    "Premium Progress Bar",
                    str(before.premium_progress_bar_enabled),
                    str(after.premium_progress_bar_enabled)
                ))
   
        if before.vanity_url_code != after.vanity_url_code:
            before_vanity = before.vanity_url_code or "None"
            after_vanity = after.vanity_url_code or "None"
            changes.append(("Vanity URL", before_vanity, after_vanity))

        
        if before.owner != after.owner:
            changes.append((
                "Server Owner",
                f"{before.owner.name} ({before.owner.id})",
                f"{after.owner.name} ({after.owner.id})"
            ))

        if before.mfa_level != after.mfa_level:
            changes.append(("MFA Level", str(before.mfa_level), str(after.mfa_level)))

        if not changes:
            return

        executor = await self.get_executor(after, discord.AuditLogAction.guild_update)

        embed = discord.Embed(
            title="Server Updated",
            color=COLOR_YELLOW,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Server", value=f"{after.name} ({after.id})", inline=False)

        for change_name, before_val, after_val in changes:
            if len(str(before_val)) > 500:
                before_val = str(before_val)[:497] + "..."
            if len(str(after_val)) > 500:
                after_val = str(after_val)[:497] + "..."

            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** {before_val}\n**After:** {after_val}",
                inline=False
            )

        if executor:
            embed.add_field(name="Changed By", value=f"{executor.name} ({executor.id})", inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        before_set = set(before)
        after_set = set(after)

        added = after_set - before_set
        removed = before_set - after_set
        
        before_dict = {e.id: e for e in before}
        after_dict = {e.id: e for e in after}

        updated = []
        for emoji_id in before_dict:
            if emoji_id in after_dict:
                before_emoji = before_dict[emoji_id]
                after_emoji = after_dict[emoji_id]
                if before_emoji.name != after_emoji.name or before_emoji.roles != after_emoji.roles:
                    updated.append((before_emoji, after_emoji))
        
        for emoji in added:
            executor = await self.get_executor(guild, discord.AuditLogAction.emoji_create, emoji.id)

            embed = discord.Embed(
                title="Emoji Added",
                color=COLOR_GREEN,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(name="Emoji Name", value=emoji.name, inline=True)
            embed.add_field(name="Emoji ID", value=emoji.id, inline=True)
            embed.add_field(name="Animated", value=str(emoji.animated), inline=True)

            if emoji.roles:
                role_names = ", ".join([r.name for r in emoji.roles])
                embed.add_field(name="Restricted to Roles", value=role_names, inline=False)

            if executor:
                embed.add_field(name="Added By", value=f"{executor.name} ({executor.id})", inline=False)

            if emoji.url:
                embed.set_thumbnail(url=emoji.url)

            await log_channel.send(embed=embed)
        
        for emoji in removed:
            executor = await self.get_executor(guild, discord.AuditLogAction.emoji_delete, emoji.id)

            embed = discord.Embed(
                title="Emoji Removed",
                color=COLOR_RED,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(name="Emoji Name", value=emoji.name, inline=True)
            embed.add_field(name="Emoji ID", value=emoji.id, inline=True)

            if executor:
                embed.add_field(name="Removed By", value=f"{executor.name} ({executor.id})", inline=False)

            await log_channel.send(embed=embed)
        
        for before_emoji, after_emoji in updated:
            executor = await self.get_executor(guild, discord.AuditLogAction.emoji_update, after_emoji.id)

            embed = discord.Embed(
                title="Emoji Updated",
                color=COLOR_BLURPLE,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(name="Emoji", value=f"{after_emoji.name} ({after_emoji.id})", inline=False)

            if before_emoji.name != after_emoji.name:
                embed.add_field(
                    name="Name Changed",
                    value=f"**Before:** {before_emoji.name}\n**After:** {after_emoji.name}",
                    inline=False
                )

            if before_emoji.roles != after_emoji.roles:
                before_roles = ", ".join([r.name for r in before_emoji.roles]) if before_emoji.roles else "None"
                after_roles = ", ".join([r.name for r in after_emoji.roles]) if after_emoji.roles else "None"
                embed.add_field(
                    name="Role Restrictions Changed",
                    value=f"**Before:** {before_roles}\n**After:** {after_roles}",
                    inline=False
                )

            if executor:
                embed.add_field(name="Updated By", value=f"{executor.name} ({executor.id})", inline=False)

            if after_emoji.url:
                embed.set_thumbnail(url=after_emoji.url)

            await log_channel.send(embed=embed)    

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):        
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return

        before_set = set(before)
        after_set = set(after)

        added = after_set - before_set
        removed = before_set - after_set

        before_dict = {s.id: s for s in before}
        after_dict = {s.id: s for s in after}

        updated = []
        for sticker_id in before_dict:
            if sticker_id in after_dict:
                before_sticker = before_dict[sticker_id]
                after_sticker = after_dict[sticker_id]
                if (before_sticker.name != after_sticker.name or 
                    before_sticker.description != after_sticker.description or
                    before_sticker.emoji != after_sticker.emoji):
                    updated.append((before_sticker, after_sticker))
                    
        for sticker in added:
            executor = await self.get_executor(guild, discord.AuditLogAction.sticker_create, sticker.id)

            embed = discord.Embed(
                title="Sticker Added",
                color=COLOR_GREEN,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(name="Sticker Name", value=sticker.name, inline=True)
            embed.add_field(name="Sticker ID", value=sticker.id, inline=True)
            embed.add_field(name="Related Emoji", value=sticker.emoji or "None", inline=True)

            if sticker.description:
                embed.add_field(name="Description", value=sticker.description, inline=False)

            if executor:
                embed.add_field(name="Added By", value=f"{executor.name} ({executor.id})", inline=False)

            await log_channel.send(embed=embed)
        
        for sticker in removed:
            executor = await self.get_executor(guild, discord.AuditLogAction.sticker_delete, sticker.id)

            embed = discord.Embed(
                title="Sticker Removed",
                color=COLOR_RED,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(name="Sticker Name", value=sticker.name, inline=True)
            embed.add_field(name="Sticker ID", value=sticker.id, inline=True)

            if executor:
                embed.add_field(name="Removed By", value=f"{executor.name} ({executor.id})", inline=False)

            await log_channel.send(embed=embed)
        
        for before_sticker, after_sticker in updated:
            executor = await self.get_executor(guild, discord.AuditLogAction.sticker_update, after_sticker.id)

            embed = discord.Embed(
                title="Sticker Updated",
                color=COLOR_BLURPLE,
                timestamp=datetime.now(UTC)
            )

            embed.add_field(name="Sticker", value=f"{after_sticker.name} ({after_sticker.id})", inline=False)

            if before_sticker.name != after_sticker.name:
                embed.add_field(
                    name="Name Changed",
                    value=f"**Before:** {before_sticker.name}\n**After:** {after_sticker.name}",
                    inline=False
                )

            if before_sticker.description != after_sticker.description:
                before_desc = before_sticker.description or "None"
                after_desc = after_sticker.description or "None"
                embed.add_field(
                    name="Description Changed",
                    value=f"**Before:** {before_desc}\n**After:** {after_desc}",
                    inline=False
                )

            if before_sticker.emoji != after_sticker.emoji:
                before_emoji = before_sticker.emoji or "None"
                after_emoji = after_sticker.emoji or "None"
                embed.add_field(
                    name="Related Emoji Changed",
                    value=f"**Before:** {before_emoji}\n**After:** {after_emoji}",
                    inline=False
                )

            if executor:
                embed.add_field(name="Updated By", value=f"{executor.name} ({executor.id})", inline=False)

            await log_channel.send(embed=embed)
            
    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return

        executor = None
        action_type = None

        try:
            await asyncio.sleep(0.5)
            async for entry in channel.guild.audit_logs(limit=5):
                if entry.action in [
                    discord.AuditLogAction.webhook_create, 
                    discord.AuditLogAction.webhook_update, 
                    discord.AuditLogAction.webhook_delete
                ]:
                    if hasattr(entry.target, 'channel_id') and entry.target.channel_id == channel.id:
                        executor = entry.user
                        action_type = entry.action
                        break
        except Exception as e:
            print(f"Error fetching webhook audit log: {e}")

        if action_type == discord.AuditLogAction.webhook_create:
            title = "Webhook Created"
            color = COLOR_GREEN
        elif action_type == discord.AuditLogAction.webhook_delete:
            title = "Webhook Deleted"
            color = COLOR_RED
        else:
            title = "Webhook Updated"
            color = COLOR_BLURPLE

        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(
            name="Channel",
            value=f"{channel.name} ({channel.id})",
            inline=False
        )

        if executor:
            embed.add_field(name="Action By", value=f"{executor.name} ({executor.id})", inline=False)

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

        embed.add_field(name="Invite Code", value=invite.code, inline=True)
        embed.add_field(name="Channel", value=invite.channel.name, inline=True)
        embed.add_field(name="Created By", value=f"{invite.inviter.name} ({invite.inviter.id})", inline=True)

        if invite.max_age:
            embed.add_field(name="Expires In", value=f"{invite.max_age}s", inline=True)
        else:
            embed.add_field(name="Expires In", value="Never", inline=True)

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

        embed.add_field(name="Invite Code", value=invite.code, inline=True)
        embed.add_field(name="Channel", value=invite.channel.name, inline=True)
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
            value=f"{guild.name} ({guild.id})",
            inline=False
        )

        if target_name:
            embed.add_field(name="Integration", value=target_name, inline=False)

        if executor:
            embed.add_field(name="Action By", value=f"{executor.name} ({executor.id})", inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        log_channel = await self.get_log_channel(thread.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Thread Created",
            color=COLOR_GREEN,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Thread Name", value=thread.name, inline=True)
        embed.add_field(name="Thread ID", value=thread.id, inline=True)
        embed.add_field(name="Parent Channel", value=thread.parent.name, inline=True)
        embed.add_field(name="Created By", value=f"{thread.owner.name} ({thread.owner.id})", inline=True)
        embed.add_field(name="Auto Archive Duration", value=f"{thread.auto_archive_duration} min", inline=True)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        
        log_channel = await self.get_log_channel(thread.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Thread Deleted",
            color=COLOR_RED,
            timestamp=datetime.now(UTC)
        )

        embed.add_field(name="Thread Name", value=thread.name, inline=True)
        embed.add_field(name="Thread ID", value=thread.id, inline=True)
        embed.add_field(name="Parent Channel", value=thread.parent.name, inline=True)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        
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

        embed.add_field(name="Thread", value=f"{after.name} ({after.id})", inline=False)

        for change_name, before_val, after_val in changes:
            embed.add_field(
                name=f"{change_name} Changed",
                value=f"**Before:** {before_val}\n**After:** {after_val}",
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

            embed.add_field(name="Member", value=f"{after.name} ({after.id})", inline=False)

            before_nick = before.nick or "None"
            after_nick = after.nick or "None"

            embed.add_field(
                name="Nickname Changed",
                value=f"**Before:** {before_nick}\n**After:** {after_nick}",
                inline=False
            )

            if executor:
                embed.add_field(name="Changed By", value=f"{executor.name} ({executor.id})", inline=False)

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

            embed.add_field(name="Member", value=f"{after.name} ({after.id})", inline=False)

            if added_roles:
                role_names = ", ".join([role.name for role in added_roles])
                embed.add_field(name="Roles Added", value=role_names, inline=False)

            if removed_roles:
                role_names = ", ".join([role.name for role in removed_roles])
                embed.add_field(name="Roles Removed", value=role_names, inline=False)

            if executor:
                embed.add_field(name="Changed By", value=f"{executor.name} ({executor.id})", inline=False)

            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AuditLogger(bot))