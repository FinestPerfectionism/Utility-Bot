import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import discord
from discord import app_commands
from discord.ext import commands

from constants import (
    ACCEPTED_EMOJI_ID,
    COLOR_BLACK,
    COLOR_GREEN,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_YELLOW,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
    QUARANTINE_ROLE_ID,
    STANDSTILL_EMOJI_ID,
    SUPPORTING_DIRECTORS_ROLE_ID,
)

if TYPE_CHECKING:
    from bot import UtilityBot

from core.help import (
    RoleConfig,
    help_description,
)
from core.permissions import is_director
from core.utils import send_major_error

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Health Check
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

DANGEROUS_PERMISSIONS: list[str] = [
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

QUARANTINE_DENY_PERMS: list[str] = [
    "view_channel",
    "create_instant_invite",
    "send_messages",
    "send_messages_in_threads",
    "create_public_threads",
    "create_private_threads",
]

NATIVE_MOD_PERMS: list[str] = [
    "kick_members",
    "ban_members",
    "moderate_members",
]

def _perm_value(perms: discord.Permissions, name: str) -> bool:
    return bool(getattr(perms, name, False))

def _overwrite_value(overwrite: discord.PermissionOverwrite, name: str) -> bool | None:
    return getattr(overwrite, name, None)

def _get_health_color(score: float) -> discord.Color:
    n_100 = 100
    if score == n_100:
        return COLOR_GREEN
    n_85  = 85
    if score > n_85:
        return COLOR_YELLOW
    n_70  = 70
    if score > n_70:
        return COLOR_ORANGE
    n_55  = 55
    if score > n_55:
        return COLOR_RED
    return COLOR_BLACK

async def _load_json_file(path: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not Path(path).exists():
        return result
    with contextlib.suppress(json.JSONDecodeError):
        text = await discord.utils.maybe_coroutine(Path(path).read_text, encoding="utf-8")
        result = json.loads(text)
    return result

async def _save_json_file(path: str, data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=4)
    _ = await discord.utils.maybe_coroutine(Path(path).write_text, text, encoding="utf-8")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Fix View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class HealthFixView(discord.ui.View):
    def __init__(self, guild: discord.Guild, fixable: list[str], cog: "HealthCommands") -> None:
        super().__init__(timeout = 300)
        self.guild   = guild
        self.fixable = fixable
        self.cog     = cog

        if not fixable:
            for child in self.children:
                if isinstance(child, discord.ui.Button | discord.ui.Select):
                    child.disabled = True

    async def _apply_everyone_role(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        fixed: list[str],
        failed: list[str],
    ) -> None:
        try:
            everyone  = guild.default_role
            new_perms = everyone.permissions
            for perm in DANGEROUS_PERMISSIONS:
                if _perm_value(new_perms, perm):
                    setattr(new_perms, perm, False)
            _ = await everyone.edit(
                permissions = new_perms,
                reason      = f"Health fix by {actor}: removing dangerous @everyone permissions",
            )
            fixed.append("Removed dangerous permissions from @everyone role")
        except discord.Forbidden:
            failed.append("Cannot edit @everyone role — missing permissions")

    async def _apply_everyone_channel(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        fixed: list[str],
        failed: list[str],
    ) -> None:
        everyone      = guild.default_role
        channel_errors = 0
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                continue
            overwrite = channel.overwrites_for(everyone)
            changed   = False
            for perm in DANGEROUS_PERMISSIONS:
                if _overwrite_value(overwrite, perm) is True:
                    setattr(overwrite, perm, None)
                    changed = True
            if changed:
                try:
                    await channel.set_permissions(
                        everyone,
                        overwrite = overwrite,
                        reason    = f"Health fix by {actor}: clearing dangerous @everyone overrides",
                    )
                except discord.Forbidden:
                    channel_errors += 1
        if channel_errors:
            failed.append(f"Could not fix @everyone overrides in {channel_errors} channel(s) — missing permissions")
        else:
            fixed.append("Cleared dangerous @everyone channel overrides")

    async def _apply_native_mod(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        fixed: list[str],
        failed: list[str],
    ) -> None:
        role_errors: list[str] = []
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
                    _ = await role.edit(
                        permissions = new_perms,
                        reason      = f"Health fix by {actor}: removing native mod permissions",
                    )
                except discord.Forbidden:
                    role_errors.append(role.name)
        if role_errors:
            failed.append(f"Could not edit role(s): {', '.join(role_errors)} — missing permissions or role is above bot")
        else:
            fixed.append("Removed native kick/ban/timeout permissions from non-director roles")

    async def _apply_quarantine_role(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        fixed: list[str],
        failed: list[str],
    ) -> None:
        quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return
        try:
            _ = await quarantine_role.edit(
                permissions = discord.Permissions.none(),
                reason      = f"Health fix by {actor}: clearing quarantine role permissions",
            )
            fixed.append("Cleared all permissions from the quarantine role")
        except discord.Forbidden:
            failed.append("Cannot edit quarantine role — missing permissions")

    async def _apply_quarantine_channel(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        fixed: list[str],
        failed: list[str],
    ) -> None:
        quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
        if not quarantine_role:
            return
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
                    overwrite = overwrite,
                    reason    = f"Health fix by {actor}: setting quarantine deny overrides",
                )
            except discord.Forbidden:
                channel_errors += 1
        if channel_errors:
            failed.append(f"Could not set quarantine overrides in {channel_errors} channel(s) — missing permissions")
        else:
            fixed.append("Set quarantine deny overrides in all channels")

    async def _apply_fixes(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        fixed: list[str],
        failed: list[str],
    ) -> None:
        if "EVERYONE_ROLE_PERMS" in self.fixable:
            await self._apply_everyone_role(guild, actor, fixed, failed)

        if "EVERYONE_CHANNEL_PERMS" in self.fixable:
            await self._apply_everyone_channel(guild, actor, fixed, failed)

        if "NATIVE_MOD_PERMS" in self.fixable:
            await self._apply_native_mod(guild, actor, fixed, failed)

        if "VERIFICATION_LEVEL" in self.fixable:
            try:
                _ = await guild.edit(
                    verification_level = discord.VerificationLevel.medium,
                    reason             = f"Health fix by {actor}: setting verification level to Medium",
                )
                fixed.append("Set server verification level to Medium")
            except discord.Forbidden:
                failed.append("Cannot set verification level — missing permissions")

        if "CONTENT_FILTER" in self.fixable:
            try:
                _ = await guild.edit(
                    explicit_content_filter = discord.ContentFilter.all_members,
                    reason                  = f"Health fix by {actor}: enabling content filter for all members",
                )
                fixed.append("Enabled explicit content filter for all members")
            except discord.Forbidden:
                failed.append("Cannot set content filter — missing permissions")

        if "QUARANTINE_ROLE_CLEAN" in self.fixable:
            await self._apply_quarantine_role(guild, actor, fixed, failed)

        if "QUARANTINE_CHANNEL_DENY" in self.fixable:
            await self._apply_quarantine_channel(guild, actor, fixed, failed)

        if "ANTINUKE_ENABLED" in self.fixable:
            config_file = "antinuke_config.json"
            with contextlib.suppress(OSError, json.JSONDecodeError):
                config = await _load_json_file(config_file)
                config["enabled"] = True
                await _save_json_file(config_file, config)
                fixed.append("Enabled the anti-nuke system")

    @discord.ui.button(label="Fix Issues", style=discord.ButtonStyle.danger, emoji=f"{STANDSTILL_EMOJI_ID}")
    async def fix_button(self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        _ = await interaction.response.defer(ephemeral = True)

        fixed:  list[str] = []
        failed: list[str] = []
        guild = self.guild

        await self._apply_fixes(guild, interaction.user, fixed, failed)

        embed = discord.Embed(
            title     = "Health Fix Results",
            color     = COLOR_GREEN if not failed else (COLOR_ORANGE if fixed else COLOR_RED),
            timestamp = datetime.now(UTC),
        )

        if fixed:
            _ = embed.add_field(
                name   = "Successfully Fixed",
                value  = "\n".join(f"{ACCEPTED_EMOJI_ID} {item}" for item in fixed),
                inline = False,
            )

        if failed:
            _ = embed.add_field(
                name   = "Failed to Fix",
                value  = "\n".join(f"{DENIED_EMOJI_ID} {item}" for item in failed),
                inline = False,
            )

        if not fixed and not failed:
            _ = embed.description = "Nothing to fix."

        button.disabled = True
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        _ = await interaction.response.edit_message(view = self)
        await interaction.followup.send("Applying fixes...", ephemeral = True)

        checks = await self.cog.run_checks(self.guild)

        passed_count = sum(1 for c in checks if c["passed"])
        total        = len(checks)
        score        = (passed_count / total) * 100
        color        = _get_health_color(score)

        updated_embed = discord.Embed(
            title     = f"Server Health — {score:.0f}%",
            color     = color,
            timestamp = datetime.now(UTC),
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
            lines: list[str] = []
            for check_id in check_ids:
                check = check_map.get(check_id)
                if not check:
                    continue

                check_passed: bool       = bool(check.get("passed", False))
                label:        str        = str(check.get("label", ""))
                fail_label:   str        = str(check.get("fail_label", label))
                detail:       str | None = check.get("detail")

                icon = f"{ACCEPTED_EMOJI_ID}" if check_passed else f"{DENIED_EMOJI_ID}"
                text = label if check_passed else fail_label
                line = f"{icon} {text}"

                if not check_passed and detail:
                    line += f"\n-# ↳ {detail}"

                lines.append(line)

            _ = updated_embed.add_field(
                name   = category_name,
                value  = "\n".join(lines),
                inline = False,
            )

        _ = updated_embed.set_footer(text=f"{passed_count}/{total} checks passed")

        remaining_fixable = [c["id"] for c in checks if not c["passed"] and c["fixable"]]
        if not remaining_fixable:
            _ = self.clear_items()

        _ = await interaction.edit_original_response(embed=updated_embed, view = self)
        await interaction.followup.send(embed=embed, ephemeral = True)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Health Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class HealthCommands(commands.Cog):
    def __init__(self, bot: "UtilityBot") -> None:
        self.bot = bot

    def can_use(self, member: discord.Member) -> bool:
        return is_director(member)

    def _checks_bot(self, guild: discord.Guild) -> list[dict[str, Any]]:
        bot_member   = guild.get_member(self.bot.user.id) if self.bot.user else None
        bot_has_admin = bool(bot_member and bot_member.guild_permissions.administrator)

        if bot_member:
            all_non_everyone = [r for r in guild.roles if r.id != guild.default_role.id]
            max_position     = max((r.position for r in all_non_everyone), default=0)
            bot_at_top       = bot_member.top_role.position >= max_position
        else:
            bot_at_top = False

        return [
            {
                "id"          : "BOT_ADMIN",
                "label"       : "Bot has Administrator permission",
                "passed"      : bot_has_admin,
                "fixable"     : False,
                "manual_note" : "Have the owner grant the bot Administrator in Server Settings → Roles.",
            },
            {
                "id"          : "BOT_TOP",
                "label"       : "Bot role is at the very top of the role list",
                "passed"      : bot_at_top,
                "fixable"     : False,
                "manual_note" : "Have the owner drag the bot's role to the top in Server Settings → Roles.",
            },
        ]

    def _checks_permissions(self, guild: discord.Guild) -> list[dict[str, Any]]:
        everyone = guild.default_role

        everyone_bad_role_perms = [
            p.replace("_", " ").title()
            for p in DANGEROUS_PERMISSIONS
            if _perm_value(everyone.permissions, p)
        ]

        channel_violations: list[str] = []
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                continue
            overwrite = channel.overwrites_for(everyone)
            for perm in DANGEROUS_PERMISSIONS:
                if _overwrite_value(overwrite, perm) is True:
                    channel_violations.append(channel.name)
                    break

        bad_roles: list[str] = []
        for role in guild.roles:
            if role.id in (guild.default_role.id, SUPPORTING_DIRECTORS_ROLE_ID):
                continue
            if role.managed:
                continue
            if any(_perm_value(role.permissions, p) for p in NATIVE_MOD_PERMS):
                bad_roles.append(role.name)

        n_4 = 4
        return [
            {
                "id"      : "EVERYONE_ROLE_PERMS",
                "label"   : "@everyone has no dangerous role permissions",
                "passed"  : len(everyone_bad_role_perms) == 0,
                "fixable" : True,
                "detail"  : f"Active: {', '.join(everyone_bad_role_perms)}" if everyone_bad_role_perms else "",
            },
            {
                "id"      : "EVERYONE_CHANNEL_PERMS",
                "label"   : "@everyone has no dangerous channel overrides",
                "passed"  : len(channel_violations) == 0,
                "fixable" : True,
                "detail"  : (
                    f"{len(channel_violations)} channel(s) affected: "
                    f"{', '.join(channel_violations[:n_4])}{'...' if len(channel_violations) > n_4 else ''}"
                ) if channel_violations else "",
            },
            {
                "id"      : "NATIVE_MOD_PERMS",
                "label"   : "No role has native kick/ban/timeout permissions",
                "passed"  : len(bad_roles) == 0,
                "fixable" : True,
                "detail"  : (
                    f"{', '.join(bad_roles)} — Utility Bot's commands are safer; they enforce rate limits and proper logging."
                ) if bad_roles else "",
            },
        ]

    def _checks_quarantine(self, guild: discord.Guild) -> list[dict[str, Any]]:
        quarantine_role = guild.get_role(QUARANTINE_ROLE_ID)
        qr_has_perms    = quarantine_role is not None and quarantine_role.permissions.value != 0

        if quarantine_role:
            channels_missing_deny: list[str] = []
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
            qr_channel_ok         = False

        return [
            {
                "id"          : "QUARANTINE_EXISTS",
                "label"       : "Quarantine role exists",
                "passed"      : quarantine_role is not None,
                "fixable"     : False,
                "manual_note" : "Create a quarantine role.",
            },
            {
                "id"      : "QUARANTINE_ROLE_CLEAN",
                "label"   : "Quarantine role has no permissions enabled",
                "passed"  : not qr_has_perms,
                "fixable" : quarantine_role is not None,
                "detail"  : "The quarantine role should have zero permissions." if qr_has_perms else "",
            },
            {
                "id"      : "QUARANTINE_CHANNEL_DENY",
                "label"   : "Quarantine role has deny overrides set in all channels",
                "passed"  : qr_channel_ok,
                "fixable" : quarantine_role is not None,
                "detail"  : f"{len(channels_missing_deny)} channel(s) missing deny overrides" if channels_missing_deny else "",
            },
        ]

    def _checks_server_security(self, guild: discord.Guild) -> list[dict[str, Any]]:
        verification_ok = (
            guild.verification_level.value
            >= discord.VerificationLevel.medium.value
        )
        content_filter_ok = guild.explicit_content_filter != discord.ContentFilter.disabled

        return [
            {
                "id"      : "VERIFICATION_LEVEL",
                "label"   : "Verification level is at least Medium (10-min Discord account age)",
                "passed"  : verification_ok,
                "fixable" : True,
                "detail"  : f"Current: {guild.verification_level.name.replace('_', ' ').title()}" if not verification_ok else "",
            },
            {
                "id"      : "CONTENT_FILTER",
                "label"   : "Explicit content filter is enabled",
                "passed"  : content_filter_ok,
                "fixable" : True,
                "detail"  : "Currently disabled — images are not being scanned for NSFW content." if not content_filter_ok else "",
            },
        ]

    async def _checks_system(self) -> list[dict[str, Any]]:
        antinuke_config  = await _load_json_file("antinuke_config.json")
        antinuke_enabled = bool(antinuke_config.get("enabled", True)) if antinuke_config else False
        antinuke_log     = antinuke_config.get("log_channel_id") is not None if antinuke_config else False

        cases_config = await _load_json_file("cases_config.json")
        cases_log    = cases_config.get("log_channel_id") is not None if cases_config else False

        return [
            {
                "id"      : "ANTINUKE_ENABLED",
                "label"   : "Anti-nuke system is enabled",
                "passed"  : antinuke_enabled,
                "fixable" : True,
            },
            {
                "id"          : "ANTINUKE_LOG",
                "label"       : "Anti-nuke log channel is configured",
                "fail_label"  : "Anti-nuke log channel is __not__ configured",
                "passed"      : antinuke_log,
                "fixable"     : False,
                "manual_note" : "Set a log channel via the anti-nuke configuration command.",
            },
            {
                "id"          : "CASES_LOG",
                "label"       : "Cases log channel is configured",
                "fail_label"  : "Cases log channel is __not__ configured",
                "passed"      : cases_log,
                "fixable"     : False,
                "manual_note" : "Run /cases config to set the log channel.",
            },
        ]

    async def run_checks(self, guild: discord.Guild) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        checks.extend(self._checks_bot(guild))
        checks.extend(self._checks_permissions(guild))
        checks.extend(self._checks_quarantine(guild))
        checks.extend(self._checks_server_security(guild))
        checks.extend(await self._checks_system())
        return checks

    @app_commands.command(
        name        = "health",
        description = "View server health and run automated fixes.",
    )
    @help_description(
        desc      = "Directors only —— Views a server health report and runs automated fixes if any issues are found.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
    )
    async def health(self, interaction: discord.Interaction) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_use(actor):
            await send_major_error(
                interaction,
                title    = "Unauthorized!",
                texts    = "You lack the necessary permissions to run a health check.",
                subtitle = "Invalid permissions.",
            )
            return

        guild = interaction.guild
        if not guild:
            return

        _ = await interaction.response.defer(ephemeral = True)

        checks = await self.run_checks(guild)

        passed = sum(1 for c in checks if c["passed"])
        total  = len(checks)
        score  = (passed / total) * 100
        color  = _get_health_color(score)

        embed = discord.Embed(
            title     = f"Server Health — {score:.0f}%",
            color     = color,
            timestamp = datetime.now(UTC),
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
            lines: list[str] = []
            for check_id in check_ids:
                check = check_map.get(check_id)
                if not check:
                    continue
                icon = f"{ACCEPTED_EMOJI_ID}" if check["passed"] else f"{DENIED_EMOJI_ID}"
                text = check["label"] if check["passed"] else check.get("fail_label", check["label"])
                line = f"{icon} {text}"
                if not check["passed"] and check.get("detail"):
                    line += f"\n-# ↳ {check['detail']}"
                lines.append(line)
            _ = embed.add_field(
                name   = category_name,
                value  = "\n".join(lines),
                inline = False,
            )

        manual_fixes = [
            c for c in checks
            if not c["passed"] and not c["fixable"] and c.get("manual_note")
        ]
        if manual_fixes:
            _ = embed.add_field(
                name  = f"{CONTESTED_EMOJI_ID}  Manual Action Required",
                value = "\n".join(
                    f"**{c['label']}**\n-# ↳ {c['manual_note']}"
                    for c in manual_fixes
                ),
                inline = False,
            )

        _ = embed.set_footer(text=f"{passed}/{total} checks passed")

        fixable = [c["id"] for c in checks if not c["passed"] and c["fixable"]]
        view    = HealthFixView(guild, fixable, self)

        await interaction.followup.send(embed=embed, view = view, ephemeral = True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HealthCommands(cast("UtilityBot", bot)))
