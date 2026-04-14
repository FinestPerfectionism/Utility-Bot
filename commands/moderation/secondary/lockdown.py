import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import UtilityBot

from constants import (
    COLOR_GREEN,
    COLOR_RED,
    CONTESTED_EMOJI_ID,
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
)
from core.cases import CasesManager, CaseType
from core.help import ArgumentInfo, RoleConfig, help_description
from core.permissions import is_director
from core.responses import send_custom_message

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Lockdown Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class LockdownCommands(commands.Cog):
    def __init__(self, bot : "UtilityBot") -> None:
        self.bot       = bot
        self.data_file = "lockdown_data.json"
        self.data      = self.load_data()

        self.STAFF_ROLE_ID = STAFF_ROLE_ID

        self.EXEMPT_CATEGORIES = [
            1433851234661695609,
            1442891409584820416,
            1385654682197819573,
            1435770165626277908,
            1437524579932176385,
            1386359981271421059,
            1460736720202109075,
            1419440211066097725,
        ]

        self.EXEMPT_CHANNELS = [
            1436046265841614858,
            1392915080294695003,
            1434727818280833024,
        ]

    @property
    def cases_manager(self) -> CasesManager:
        return self.bot.cases_manager

    def load_data(self) -> dict[str, Any]:
        if Path(self.data_file).exists():
            with contextlib.suppress(json.JSONDecodeError), Path(self.data_file).open() as f:
                return json.load(f)
        return self.get_default_data()

    def get_default_data(self) -> dict[str, Any]:
        return {
            "active"              : False,
            "activated_at"        : None,
            "activated_by"        : None,
            "reason"              :  None,
            "channel_permissions" : {},
        }

    def save_data(self) -> None:
        with Path(self.data_file).open("w") as f:
            json.dump(self.data, f, indent=4)

    def can_manage_lockdown(self, member: discord.Member) -> bool:
        return is_director(member)

    def is_channel_exempt(self, channel: discord.TextChannel | discord.VoiceChannel | discord.ForumChannel | discord.StageChannel) -> bool:
        return (
            channel.id in self.EXEMPT_CHANNELS
            or (channel.category_id is not None and channel.category_id in self.EXEMPT_CATEGORIES)
        )

    lockdown_group = app_commands.Group(
        name        = "lockdown",
        description = "Directors only —— Server lockdown management.",
    )

    @lockdown_group.command(
        name        = "status",
        description = "View the current lockdown status.",
    )
    @help_description(
        desc      = "Directors only —— Views the current lockdown state and summary.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
    )
    async def lockdown_status(self, interaction : discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            return

        if not self.can_manage_lockdown(member):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        if not self.data["active"]:
            embed = discord.Embed(
                title       = "Lockdown Status",
                description = "The server is **not** currently in lockdown.",
                color       = COLOR_GREEN,
                timestamp   = datetime.now(UTC),
            )
            _ = await interaction.response.send_message(embed = embed, ephemeral = True)
            return

        activated_at = datetime.fromisoformat(self.data["activated_at"])
        guild = interaction.guild
        if guild is None:
            return
        activated_by         = guild.get_member(self.data["activated_by"])
        activated_by_mention = activated_by.mention if activated_by else f"Unknown User ({self.data['activated_by']})"

        embed = discord.Embed(
            title     = "Lockdown Active",
            color     = COLOR_RED,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(
            name   = "Activated By",
            value  = activated_by_mention,
            inline = True,
        )
        _ = embed.add_field(
            name   = "Activated",
            value  = discord.utils.format_dt(activated_at, "R"),
            inline = True,
        )
        _ = embed.add_field(
            name   = "Channels Locked",
            value  = str(len(self.data["channel_permissions"])),
            inline = True,
        )
        _ = embed.add_field(
            name   = "Reason",
            value  = self.data["reason"],
            inline = False,
        )

        _ = await interaction.response.send_message(embed = embed, ephemeral = True)

    @lockdown_group.command(
        name        = "activate",
        description = "Activate server lockdown.",
    )
    @app_commands.describe(reason = "Reason for lockdown.")
    @help_description(
        desc      = "Directors only —— Activates lockdown across the server.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
        arguments = {"reason": ArgumentInfo(description = "Reason for engaging lockdown.")},
    )
    async def lockdown_activate(
        self,
        interaction : discord.Interaction,
        reason      : str,
    ) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_lockdown(actor):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        if self.data["active"]:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "activate lockdown",
                subtitle = "The server is already in lockdown.",
                footer   = "Bad request",
            )
            return

        _ = await interaction.response.defer(ephemeral = True)

        guild = interaction.guild
        if guild is None:
            return

        staff_role = guild.get_role(self.STAFF_ROLE_ID)
        if not staff_role:
            await send_custom_message(
                interaction,
                msg_type          = "error",
                title             = "activate lockdown",
                subtitle          = "The staff role could not be found.",
                footer            = "Invalid IDs",
                contact_bot_owner = True,
            )
            return

        channels_locked   = 0
        permission_backup = {}

        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel | discord.VoiceChannel | discord.ForumChannel | discord.StageChannel):
                if self.is_channel_exempt(channel):
                    continue

                with contextlib.suppress(discord.Forbidden, Exception):
                    default_role: discord.Role                = guild.default_role
                    overwrites:   discord.PermissionOverwrite = channel.overwrites_for(default_role)

                    permission_backup[str(channel.id)] = {
                        "send_messages"            : overwrites.send_messages,
                        "send_messages_in_threads" : overwrites.send_messages_in_threads,
                        "create_public_threads"    : overwrites.create_public_threads,
                        "create_private_threads"   : overwrites.create_private_threads,
                        "connect"                  : overwrites.connect,
                        "speak"                    : overwrites.speak,
                    }

                    await channel.set_permissions(
                        default_role,
                        send_messages            = False,
                        send_messages_in_threads = False,
                        create_public_threads    = False,
                        create_private_threads   = False,
                        connect                  = False,
                        speak                    = False,
                        reason                   = f"UB Lockdown: Lockdown engaged by {actor}",
                    )

                    if isinstance(channel, discord.TextChannel):
                        await channel.set_permissions(
                            staff_role,
                            send_messages            = True,
                            send_messages_in_threads = True,
                            reason                   = f"UB Lockdown: lockdown engaged by {actor} —— Adding staff overrides",
                        )

                    channels_locked += 1

        self.data["active"]              = True
        self.data["activated_at"]        = datetime.now(UTC).isoformat()
        self.data["activated_by"]        = actor.id
        self.data["reason"]              = reason
        self.data["channel_permissions"] = permission_backup
        self.save_data()

        _ = await self.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.LOCKDOWN_ADD,
            moderator   = actor,
            reason      = reason,
            target_user = None,
            metadata    = {"channels_locked": channels_locked},
        )

        embed = discord.Embed(
            title     = "Lockdown Engaged",
            color     = COLOR_RED,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Director", value = actor.mention, inline = True)
        _ = embed.add_field(name = "Channels Locked", value = str(channels_locked), inline = True)
        _ = embed.add_field(name = "Reason", value = reason, inline = False)
        _ = embed.add_field(
            name   = "Note",
            value  = f"Staff members ({staff_role.mention}) can still send messages.\n"
                     f"New members joining will be automatically kicked.",
            inline = False,
        )

        await interaction.followup.send(embed = embed, ephemeral = True)

    @lockdown_group.command(
        name        = "lift",
        description = "Lift server lockdown.",
    )
    @help_description(
        desc      = "Directors only —— Lifs an active server lockdown and restores saved permissions.",
        prefix    = False,
        slash     = True,
        run_roles = [RoleConfig(role_id = DIRECTORS_ROLE_ID)],
    )
    async def lockdown_lift(self, interaction : discord.Interaction) -> None:
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_lockdown(actor):
            await send_custom_message(
                interaction,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        if not self.data["active"]:
            await send_custom_message(
                interaction,
                msg_type = "warning",
                title    = "lift lockdown",
                subtitle = "The server is not currently in lockdown.",
                footer   = "Bad request",
            )
            return

        _ = await interaction.response.defer(ephemeral = True)

        guild = interaction.guild
        if guild is None:
            return

        channels_restored  = 0
        channels_not_found = 0

        for channel_id, perms in self.data["channel_permissions"].items():
            channel = guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel | discord.VoiceChannel | discord.ForumChannel | discord.StageChannel):
                channels_not_found += 1
                continue

            with contextlib.suppress(discord.Forbidden, Exception):
                default_role: discord.Role = guild.default_role

                await channel.set_permissions(
                    default_role,
                    send_messages            = perms["send_messages"],
                    send_messages_in_threads = perms["send_messages_in_threads"],
                    create_public_threads    = perms["create_public_threads"],
                    create_private_threads   = perms["create_private_threads"],
                    connect                  = perms["connect"],
                    speak                    = perms["speak"],
                    reason                   = f"Lockdown lifted by {actor}",
                )

                staff_role: discord.Role | None = guild.get_role(self.STAFF_ROLE_ID)
                if staff_role and isinstance(channel, discord.TextChannel):
                    overwrites : discord.PermissionOverwrite = channel.overwrites_for(staff_role)
                    if overwrites.is_empty():
                        await channel.set_permissions(
                            staff_role,
                            overwrite = None,
                            reason    = f"Lockdown lifted by {actor} —— Removing staff overrides",
                        )

                channels_restored += 1

        self.data["active"]              = False
        self.data["activated_at"]        = None
        self.data["activated_by"]        = None
        self.data["reason"]              = None
        self.data["channel_permissions"] = {}
        self.save_data()

        _ = await self.cases_manager.log_case(
            guild       = guild,
            case_type   = CaseType.LOCKDOWN_REMOVE,
            moderator   = actor,
            reason      = "UB Lockdown: lockdown lifted by ",
            target_user = None,
            metadata    = {"channels_restored": channels_restored},
        )

        embed = discord.Embed(
            title     = "Lockdown Lifted",
            color     = COLOR_GREEN,
            timestamp = datetime.now(UTC),
        )
        _ = embed.add_field(name = "Director", value = actor.mention, inline = True)
        _ = embed.add_field(name = "Channels Restored", value = str(channels_restored), inline = True)

        if channels_not_found > 0:
            _ = embed.add_field(
                name   = f"{CONTESTED_EMOJI_ID} Channels Not Found",
                value  = f"{channels_not_found} channel(s) no longer exist and could not be restored.",
                inline = False,
            )

        await interaction.followup.send(embed = embed, ephemeral = True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if not self.data["active"]:
            return

        if member.bot:
            return

        guild = member.guild

        with contextlib.suppress(discord.Forbidden, Exception):
            bot_member : discord.Member | None = guild.get_member(self.bot.user.id) if self.bot.user else None
            if bot_member:
                _ = await self.cases_manager.log_case(
                    guild       = guild,
                    case_type   = CaseType.KICK,
                    moderator   = bot_member,
                    reason      = "*Server is in lockdown —— automatic kick*",
                    target_user = member,
                    metadata    = {"auto_kick": True, "lockdown": True},
                )

            await member.kick(reason = "UB Lockdown: server is in lockdown")

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(LockdownCommands(cast("UtilityBot", bot)))
