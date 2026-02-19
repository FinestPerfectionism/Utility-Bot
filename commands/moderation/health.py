import discord
from discord.ext import commands
from discord import app_commands

import json
import os
from datetime import datetime
from typing import cast, List, Dict, Optional

from constants import (
    ACCEPTED_EMOJI_ID,
    STANDSTILL_EMOJI_ID,

    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_BLACK,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    SUPPORTING_DIRECTOR_ROLE_ID,
    QUARANTINE_ROLE_ID,
    DIRECTORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
)

from core.bot import UtilityBot
from core.utils import send_major_error

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Health Check
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

DANGEROUS_PERMISSIONS: List[str] = [
    "administrator",
    "manage_channels",
    "manage_roles",
    "manage_expressions",
    "view_audit_log",
    "manage_webhooks",
    "manage_guild",
    "kick_members",
    "ban_members",
    "moderate_members",
    "mention_everyone",
    "manage_messages",
    "manage_threads",
]

QUARANTINE_DENY_PERMS: List[str] = [
    "view_channel",
    "create_instant_invite",
    "send_messages",
    "send_messages_in_threads",
    "create_public_threads",
    "create_private_threads",
]

NATIVE_MOD_PERMS: List[str] = [
    "kick_members",
    "ban_members",
    "moderate_members",
]

def _perm_value(perms: discord.Permissions, name: str) -> bool:
    return bool(getattr(perms, name, False))

def _overwrite_value(overwrite: discord.PermissionOverwrite, name: str) -> Optional[bool]:
    return getattr(overwrite, name, None)

def _get_health_color(score: float) -> discord.Color:
    if score == 100:
        return COLOR_GREEN
    if score > 85:
        return COLOR_YELLOW
    if score > 70:
        return COLOR_ORANGE
    if score > 55:
        return COLOR_RED
    return COLOR_BLACK

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Fix View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class HealthFixView(discord.ui.View):
    def __init__(self, guild: discord.Guild, fixable: List[str], cog: "HealthCommands"):
        super().__init__(timeout=300)
        self.guild = guild
        self.fixable = fixable
        self.cog = cog
        
        if not fixable:
            for child in self.children:
                if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                    child.disabled = True
                
    @discord.ui.button(label="Fix Issues", style=discord.ButtonStyle.danger, emoji=f"{STANDSTILL_EMOJI_ID}")
    async def fix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member):
            return

        await interaction.response.defer(ephemeral=True)

        fixed: List[str] = []
        failed: List[str] = []
        guild = self.guild

        if "EVERYONE_ROLE_PERMS" in self.fixable:
            try:
                everyone = guild.default_role
                new_perms = everyone.permissions
                for perm in DANGEROUS_PERMISSIONS:
                    if _perm_value(new_perms, perm):
                        setattr(new_perms, perm, False)
                await everyone.edit(
                    permissions=new_perms,
                    reason=f"Health fix by {interaction.user}: removing dangerous @everyone permissions"
                )
                fixed.append("Removed dangerous permissions from @everyone role")
            except discord.Forbidden:
                failed.append("Cannot edit @everyone role — missing permissions")

        if "EVERYONE_CHANNEL_PERMS" in self.fixable:
            everyone = guild.default_role
            channel_errors = 0
            for channel in guild.channels:
                if isinstance(channel, discord.CategoryChannel):
                    continue
                overwrite = channel.overwrites_for(everyone)
                changed = False
                for perm in DANGEROUS_PERMISSIONS:
                    if _overwrite_value(overwrite, perm) is True:
                        setattr(overwrite, perm, None)
                        changed = True
                if changed:
                    try:
                        await channel.set_permissions(
                            everyone,
                            overwrite=overwrite,
                            reason=f"Health fix by {interaction.user}: clearing dangerous @everyone overrides"
                        )
                    except discord.Forbidden:
                        channel_errors += 1
            if channel_errors:
                failed.append(f"Could not fix @everyone overrides in {channel_errors} channel(s) — missing permissions")
            else:
                fixed.append("Cleared dangerous @everyone channel overrides")

        if "NATIVE_MOD_PERMS" in self.fixable:
            role_errors: List[str] = []
            for role in guild.roles:
                if role.id in (guild.default_role.id, DIRECTORS_ROLE_ID):
                    continue
                if role.managed:
                    continue
                if any(_perm_value(role.permissions, p) for p in NATIVE_MOD_PERMS):
                    try:
                        new_perms = role.permissions
                        for perm in NATIVE_MOD_PERMS:
                            setattr(new_perms, perm, False)
                        await role.edit(
                            permissions=new_perms,
                            reason=f"Health fix by {interaction.user}: removing native mod permissions"
                        )
                    except discord.Forbidden:
                        role_errors.append(role.name)
            if role_errors:
                failed.append(f"Could not edit role(s): {', '.join(role_errors)} — missing permissions or role is above bot")
            else:
                fixed.append("Removed native kick/ban/timeout permissions from non-director roles")

        if "VERIFICATION_LEVEL" in self.fixable:
            try:
                await guild.edit(
                    verification_level=discord.VerificationLevel.medium,
                    reason=f"Health fix by {interaction.user}: setting verification level to Medium"
                )
                fixed.append("Set server verification level to Medium")
            except discord.Forbidden:
                failed.append("Cannot set verification level — missing permissions")

        if "CONTENT_FILTER" in self.fixable:
            try:
                await guild.edit(
                    explicit_content_filter=discord.ContentFilter.all_members,
                    reason=f"Health fix by {interaction.user}: enabling content filter for all members"
                )
                fixed.append("Enabled explicit content filter for all members")
            except discord.Forbidden:
                failed.append("Cannot set content filter — missing permissions")

        if "QUARANTINE_ROLE_CLEAN" in self.fixable:
            quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
            if quarantine_role:
                try:
                    await quarantine_role.edit(
                        permissions=discord.Permissions.none(),
                        reason=f"Health fix by {interaction.user}: clearing quarantine role permissions"
                    )
                    fixed.append("Cleared all permissions from the quarantine role")
                except discord.Forbidden:
                    failed.append("Cannot edit quarantine role — missing permissions")

        if "QUARANTINE_CHANNEL_DENY" in self.fixable:
            quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
            if quarantine_role:
                channel_errors = 0
                for channel in guild.channels:
                    if isinstance(channel, discord.CategoryChannel):
                        continue
                    overwrite = channel.overwrites_for(quarantine_role)
                    for perm in QUARANTINE_DENY_PERMS:
                        setattr(overwrite, perm, False)
                    try:
                        await channel.set_permissions(
                            quarantine_role,
                            overwrite=overwrite,
                            reason=f"Health fix by {interaction.user}: setting quarantine deny overrides"
                        )
                    except discord.Forbidden:
                        channel_errors += 1
                if channel_errors:
                    failed.append(f"Could not set quarantine overrides in {channel_errors} channel(s) — missing permissions")
                else:
                    fixed.append("Set quarantine deny overrides in all channels")

        if "ANTINUKE_ENABLED" in self.fixable:
            config_file = "antinuke_config.json"
            try:
                config: Dict = {}
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                config["enabled"] = True
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                fixed.append("Enabled the anti-nuke system")
            except Exception:
                failed.append("Could not update anti-nuke config file")

        embed = discord.Embed(
            title="Health Fix Results",
            color=COLOR_GREEN if not failed else (COLOR_ORANGE if fixed else COLOR_RED),
            timestamp=datetime.now()
        )

        if fixed:
            embed.add_field(
                name="Fixed",
                value="\n".join(f"{ACCEPTED_EMOJI_ID} {item}" for item in fixed),
                inline=False
            )

        if failed:
            embed.add_field(
                name="Could Not Fix",
                value="\n".join(f"{DENIED_EMOJI_ID} {item}" for item in failed),
                inline=False
            )

        if not fixed and not failed:
            embed.description = "Nothing to fix."

        button.disabled = True
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Applying fixes...", ephemeral=True)

        checks = await self.cog._run_checks(self.guild)

        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)
        score = (passed / total) * 100
        color = _get_health_color(score)

        updated_embed = discord.Embed(
            title=f"Server Health — {score:.0f}%",
            color=color,
            timestamp=datetime.now()
        )

        categories = [
            ("Bot Configuration", ["BOT_ADMIN", "BOT_TOP"]),
            ("Permission Safety", ["EVERYONE_ROLE_PERMS", "EVERYONE_CHANNEL_PERMS", "NATIVE_MOD_PERMS"]),
            ("Quarantine Setup", ["QUARANTINE_EXISTS", "QUARANTINE_ROLE_CLEAN", "QUARANTINE_CHANNEL_DENY"]),
            ("Server Security", ["VERIFICATION_LEVEL", "CONTENT_FILTER"]),
            ("System Configuration", ["ANTINUKE_ENABLED", "ANTINUKE_LOG", "CASES_LOG"]),
        ]

        check_map = {c["id"]: c for c in checks}

        for category_name, check_ids in categories:
            lines = []
            for check_id in check_ids:
                check = check_map.get(check_id)
                if not check:
                    continue
                icon = f"{ACCEPTED_EMOJI_ID}" if check["passed"] else f"{DENIED_EMOJI_ID}"
                line = f"{icon} {check['label']}"
                if not check["passed"] and check.get("detail"):
                    line += f"\n-# ↳ {check['detail']}"
                lines.append(line)

            updated_embed.add_field(
                name=category_name,
                value="\n".join(lines),
                inline=False
            )

        updated_embed.set_footer(text=f"{passed}/{total} checks passed")

        remaining_fixable = [c["id"] for c in checks if not c["passed"] and c["fixable"]]
        if not remaining_fixable:
            self.clear_items()

        await interaction.edit_original_response(embed=updated_embed, view=self)
        await interaction.followup.send(embed=embed, ephemeral=True)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Health Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class HealthCommands(commands.Cog):
    def __init__(self, bot: "UtilityBot"):
        self.bot = bot

    def has_role(self, member: discord.Member, role_id: int) -> bool:
        return any(role.id == role_id for role in member.roles)

    def is_director(self, member: discord.Member) -> bool:
        return self.has_role(member, DIRECTORS_ROLE_ID)

    def is_senior_moderator(self, member: discord.Member) -> bool:
        return self.has_role(member, SENIOR_MODERATORS_ROLE_ID)

    def can_use(self, member: discord.Member) -> bool:
        return self.is_director(member) or self.is_senior_moderator(member)

    async def _run_checks(self, guild: discord.Guild) -> List[Dict]:
        checks: List[Dict] = []
        bot_member = guild.get_member(self.bot.user.id) if self.bot.user else None

        bot_has_admin = bool(bot_member and bot_member.guild_permissions.administrator)
        checks.append({
            "id": "BOT_ADMIN",
            "label": "Bot has Administrator permission",
            "passed": bot_has_admin,
            "fixable": False,
            "manual_note": "Have the owner grant the bot Administrator in Server Settings → Roles.",
        })

        if bot_member:
            all_non_everyone = [r for r in guild.roles if r.id != guild.default_role.id]
            max_position = max((r.position for r in all_non_everyone), default=0)
            bot_at_top = bot_member.top_role.position >= max_position
        else:
            bot_at_top = False
        checks.append({
            "id": "BOT_TOP",
            "label": "Bot role is at the very top of the role list",
            "passed": bot_at_top,
            "fixable": False,
            "manual_note": "Have the owner drag the bot's role to the top in Server Settings → Roles.",
        })

        everyone = guild.default_role
        everyone_bad_role_perms = [
            p.replace("_", " ").title()
            for p in DANGEROUS_PERMISSIONS
            if _perm_value(everyone.permissions, p)
        ]
        checks.append({
            "id": "EVERYONE_ROLE_PERMS",
            "label": "@everyone has no dangerous role permissions",
            "passed": len(everyone_bad_role_perms) == 0,
            "fixable": True,
            "detail": f"Active: {', '.join(everyone_bad_role_perms)}" if everyone_bad_role_perms else "",
        })

        channel_violations: List[str] = []
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                continue
            overwrite = channel.overwrites_for(everyone)
            for perm in DANGEROUS_PERMISSIONS:
                if _overwrite_value(overwrite, perm) is True:
                    channel_violations.append(channel.name)
                    break
        checks.append({
            "id": "EVERYONE_CHANNEL_PERMS",
            "label": "@everyone has no dangerous channel overrides",
            "passed": len(channel_violations) == 0,
            "fixable": True,
            "detail": (
                f"{len(channel_violations)} channel(s) affected: "
                f"{', '.join(channel_violations[:4])}{'...' if len(channel_violations) > 4 else ''}"
            ) if channel_violations else "",
        })

        bad_roles: List[str] = []
        for role in guild.roles:
            if role.id in (guild.default_role.id, SUPPORTING_DIRECTOR_ROLE_ID):
                continue
            if role.managed:
                continue
            if any(_perm_value(role.permissions, p) for p in NATIVE_MOD_PERMS):
                bad_roles.append(role.name)
        checks.append({
            "id": "NATIVE_MOD_PERMS",
            "label": "No role has native kick/ban/timeout permissions",
            "passed": len(bad_roles) == 0,
            "fixable": True,
            "detail": (
                f"{', '.join(bad_roles)} — Utility Bot's commands are safer; they enforce rate limits and proper logging."
            ) if bad_roles else "",
        })

        quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
        checks.append({
            "id": "QUARANTINE_EXISTS",
            "label": "Quarantine role exists",
            "passed": quarantine_role is not None,
            "fixable": False,
            "manual_note": "Create a quarantine role and update QUARANTINE_ROLE_ID in constants.",
        })

        qr_has_perms = quarantine_role is not None and quarantine_role.permissions.value != 0
        checks.append({
            "id": "QUARANTINE_ROLE_CLEAN",
            "label": "Quarantine role has no permissions enabled",
            "passed": not qr_has_perms,
            "fixable": quarantine_role is not None,
            "detail": "The quarantine role should have zero permissions." if qr_has_perms else "",
        })

        if quarantine_role:
            channels_missing_deny: List[str] = []
            for channel in guild.channels:
                if isinstance(channel, discord.CategoryChannel):
                    continue
                overwrite = channel.overwrites_for(quarantine_role)
                for perm in QUARANTINE_DENY_PERMS:
                    if _overwrite_value(overwrite, perm) is not False:
                        channels_missing_deny.append(channel.name)
                        break
            qr_channel_ok = len(channels_missing_deny) == 0
        else:
            channels_missing_deny = []
            qr_channel_ok = False

        checks.append({
            "id": "QUARANTINE_CHANNEL_DENY",
            "label": "Quarantine role has deny overrides set in all channels",
            "passed": qr_channel_ok,
            "fixable": quarantine_role is not None,
            "detail": f"{len(channels_missing_deny)} channel(s) missing deny overrides" if channels_missing_deny else "",
        })

        verification_ok = (
            guild.verification_level.value
            >= discord.VerificationLevel.medium.value
        )
        checks.append({
            "id": "VERIFICATION_LEVEL",
            "label": "Verification level is at least Medium (10-min Discord account age)",
            "passed": verification_ok,
            "fixable": True,
            "detail": f"Current: {guild.verification_level.name.replace('_', ' ').title()}" if not verification_ok else "",
        })

        content_filter_ok = guild.explicit_content_filter != discord.ContentFilter.disabled
        checks.append({
            "id": "CONTENT_FILTER",
            "label": "Explicit content filter is enabled",
            "passed": content_filter_ok,
            "fixable": True,
            "detail": "Currently disabled — images are not being scanned for NSFW content." if not content_filter_ok else "",
        })

        antinuke_config_file = "antinuke_config.json"
        antinuke_enabled = False
        antinuke_log = False
        if os.path.exists(antinuke_config_file):
            try:
                with open(antinuke_config_file, 'r') as f:
                    antinuke_config = json.load(f)
                antinuke_enabled = antinuke_config.get("enabled", True)
                antinuke_log = antinuke_config.get("log_channel_id") is not None
            except json.JSONDecodeError:
                pass

        checks.append({
            "id": "ANTINUKE_ENABLED",
            "label": "Anti-nuke system is enabled",
            "passed": antinuke_enabled,
            "fixable": True,
        })

        checks.append({
            "id": "ANTINUKE_LOG",
            "label": "Anti-nuke log channel is configured",
            "passed": antinuke_log,
            "fixable": False,
            "manual_note": "Set a log channel via the anti-nuke configuration command.",
        })

        cases_config_file = "cases_config.json"
        cases_log = False
        if os.path.exists(cases_config_file):
            try:
                with open(cases_config_file, 'r') as f:
                    cases_config = json.load(f)
                cases_log = cases_config.get("log_channel_id") is not None
            except json.JSONDecodeError:
                pass

        checks.append({
            "id": "CASES_LOG",
            "label": "Cases log channel is configured",
            "passed": cases_log,
            "fixable": False,
            "manual_note": "Run /cases config to set the log channel.",
        })

        return checks

    @app_commands.command(
        name="health",
        description="View server health and run automated fixes."
    )
    async def health(self, interaction: discord.Interaction):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_use(actor):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run a health check.",
                subtitle="Invalid permissions."
            )
            return

        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)

        checks = await self._run_checks(guild)

        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)
        score = (passed / total) * 100
        color = _get_health_color(score)

        embed = discord.Embed(
            title=f"Server Health — {score:.0f}%",
            color=color,
            timestamp=datetime.now()
        )

        categories = [
            ("Bot Configuration", ["BOT_ADMIN", "BOT_TOP"]),
            ("Permission Safety", ["EVERYONE_ROLE_PERMS", "EVERYONE_CHANNEL_PERMS", "NATIVE_MOD_PERMS"]),
            ("Quarantine Setup", ["QUARANTINE_EXISTS", "QUARANTINE_ROLE_CLEAN", "QUARANTINE_CHANNEL_DENY"]),
            ("Server Security", ["VERIFICATION_LEVEL", "CONTENT_FILTER"]),
            ("System Configuration", ["ANTINUKE_ENABLED", "ANTINUKE_LOG", "CASES_LOG"]),
        ]

        check_map = {c["id"]: c for c in checks}

        for category_name, check_ids in categories:
            lines: List[str] = []
            for check_id in check_ids:
                check = check_map.get(check_id)
                if not check:
                    continue
                icon = f"{ACCEPTED_EMOJI_ID}" if check["passed"] else f"{DENIED_EMOJI_ID}"
                line = f"{icon} {check['label']}"
                if not check["passed"] and check.get("detail"):
                    line += f"\n-# ↳ {check['detail']}"
                lines.append(line)
            embed.add_field(
                name=category_name,
                value="\n".join(lines),
                inline=False
            )

        manual_fixes = [
            c for c in checks
            if not c["passed"] and not c["fixable"] and c.get("manual_note")
        ]
        if manual_fixes:
            embed.add_field(
                name=f"{CONTESTED_EMOJI_ID}  Manual Action Required",
                value="\n".join(
                    f"**{c['label']}**\n-# ↳ {c['manual_note']}"
                    for c in manual_fixes
                ),
                inline=False
            )

        embed.set_footer(text=f"{passed}/{total} checks passed")

        fixable = [c["id"] for c in checks if not c["passed"] and c["fixable"]]
        view = HealthFixView(guild, fixable, self)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HealthCommands(cast(UtilityBot, bot)))