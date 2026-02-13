import discord
from discord.ext import commands
from discord import app_commands

from core.bot import UtilityBot

import json
import os
from datetime import datetime
from typing import Dict, cast

from constants import(
    BOT_OWNER_ID,

    COLOR_GREEN,
    COLOR_RED,

    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
)
from core.utils import send_major_error, send_minor_error

from commands.moderation.cases import CaseType

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Lockdown Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class LockdownCommands(commands.Cog):
    def __init__(self, bot: "UtilityBot"):
        self.bot = bot
        self.data_file = "lockdown_data.json"
        self.data = self.load_data()

        self.DIRECTORS_ROLE_ID = DIRECTORS_ROLE_ID
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

        self.cases_manager = cast(UtilityBot, bot).cases_manager

    def permission_error(self, custom_text: str):
        class PermissionError(discord.ui.LayoutView):
            container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=(
                    f"### {DENIED_EMOJI_ID} Unauthorized!\n"
                    "-# No permissions.\n"
                    f"{custom_text}")),
                accent_color=COLOR_RED,
            )

        return PermissionError()

    def load_data(self) -> Dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_data()
        return self.get_default_data()

    def get_default_data(self) -> Dict:
        return {
            "active": False,
            "activated_at": None,
            "activated_by": None,
            "reason": None,
            "channel_permissions": {}
        }

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def has_role(self, member: discord.Member, role_id: int) -> bool:
        return any(role.id == role_id for role in member.roles)

    def is_director(self, member: discord.Member) -> bool:
        return self.has_role(member, self.DIRECTORS_ROLE_ID)

    def is_staff(self, member: discord.Member) -> bool:
        return self.has_role(member, self.STAFF_ROLE_ID)

    def can_manage_lockdown(self, member: discord.Member) -> bool:
        return self.is_director(member)

    def is_channel_exempt(self, channel: discord.TextChannel | discord.VoiceChannel | discord.ForumChannel | discord.StageChannel) -> bool:
        if channel.id in self.EXEMPT_CHANNELS:
            return True
        if channel.category_id and channel.category_id in self.EXEMPT_CATEGORIES:
            return True
        return False

    lockdown_group = app_commands.Group(
        name="lockdown",
        description="Directors only —— Server lockdown management."
    )

    @lockdown_group.command(
        name="status",
        description="View the current lockdown status."
    )
    async def lockdown_status(self, interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            return

        if not self.can_manage_lockdown(member):
            deniedcommanduse = self.permission_error("You lack the necessary permissions to run this command.")
            await interaction.response.send_message(
                view=deniedcommanduse,
                ephemeral=True
            )
            return

        if not self.data["active"]:
            embed = discord.Embed(
                title="Lockdown Status",
                description="The server is **not** currently in lockdown.",
                color=COLOR_GREEN,
                timestamp=datetime.now()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        activated_at = datetime.fromisoformat(self.data["activated_at"])
        guild = interaction.guild
        if guild is None:
            return
        activated_by = guild.get_member(self.data["activated_by"])
        activated_by_mention = activated_by.mention if activated_by else f"Unknown User ({self.data['activated_by']})"

        embed = discord.Embed(
            title="Lockdown Active",
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="Activated By",
            value=activated_by_mention,
            inline=True
        )
        embed.add_field(
            name="Activated",
            value=discord.utils.format_dt(activated_at, 'R'),
            inline=True
        )
        embed.add_field(
            name="Channels Locked",
            value=str(len(self.data["channel_permissions"])),
            inline=True
        )
        embed.add_field(
            name="Reason",
            value=self.data["reason"] or "No reason provided",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @lockdown_group.command(
        name="activate",
        description="Activate server lockdown."
    )
    @app_commands.describe(reason="Reason for lockdown.")
    async def lockdown_activate(
        self,
        interaction: discord.Interaction,
        reason: str | None = None
    ):
        reason = reason or "No reason provided"

        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_lockdown(actor):
            deniedadd = self.permission_error("You lack the necessary permissions to activate lockdown.")
            await interaction.response.send_message(
                view=deniedadd,
                ephemeral=True
            )
            return

        if self.data["active"]:
            await send_minor_error(
                interaction,
                "The server is already in lockdown.",
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            return

        staff_role = guild.get_role(self.STAFF_ROLE_ID)
        if not staff_role:
            await send_major_error(
                interaction,
                "Staff role not found.",
                subtitle=f"Invalid IDs. Contact <@{BOT_OWNER_ID}>."
            )
            return

        channels_locked = 0
        permission_backup = {}

        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.StageChannel)):
                if self.is_channel_exempt(channel):
                    continue

                try:
                    default_role = guild.default_role
                    overwrites = channel.overwrites_for(default_role)

                    permission_backup[str(channel.id)] = {
                        "send_messages": overwrites.send_messages,
                        "send_messages_in_threads": overwrites.send_messages_in_threads,
                        "create_public_threads": overwrites.create_public_threads,
                        "create_private_threads": overwrites.create_private_threads,
                        "connect": overwrites.connect,
                        "speak": overwrites.speak,
                    }

                    await channel.set_permissions(
                        default_role,
                        send_messages=False,
                        send_messages_in_threads=False,
                        create_public_threads=False,
                        create_private_threads=False,
                        connect=False,
                        speak=False,
                        reason=f"Lockdown activated by {actor}"
                    )

                    if isinstance(channel, discord.TextChannel):
                        await channel.set_permissions(
                            staff_role,
                            send_messages=True,
                            send_messages_in_threads=True,
                            reason=f"Lockdown engaged by {actor} - Staff exemption"
                        )

                    channels_locked += 1

                except discord.Forbidden:
                    continue
                except Exception:
                    continue

        self.data["active"] = True
        self.data["activated_at"] = datetime.now().isoformat()
        self.data["activated_by"] = actor.id
        self.data["reason"] = reason
        self.data["channel_permissions"] = permission_backup
        self.save_data()

        await self.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.LOCKDOWN_ADD,
            moderator=actor,
            reason=reason,
            target_user=None,
            metadata={"channels_locked": channels_locked}
        )

        embed = discord.Embed(
            title="Lockdown Engaged",
            color=COLOR_RED,
            timestamp=datetime.now()
        )
        embed.add_field(name="Director", value=actor.mention, inline=True)
        embed.add_field(name="Channels Locked", value=str(channels_locked), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(
            name="Note",
            value=f"Staff members ({staff_role.mention}) can still send messages.\n"
                  f"New members joining will be automatically kicked.",
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @lockdown_group.command(
        name="lift",
        description="Lift server lockdown."
    )
    async def lockdown_lift(self, interaction: discord.Interaction):
        actor = interaction.user
        if not isinstance(actor, discord.Member):
            return

        if not self.can_manage_lockdown(actor):
            deniedremove = self.permission_error("You lack the necessary permissions to lift lockdown.")
            await interaction.response.send_message(
                view=deniedremove,
                ephemeral=True
            )
            return

        if not self.data["active"]:
            await send_minor_error(
                interaction,
                "The server is not currently in lockdown.",
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            return

        channels_restored = 0
        channels_not_found = 0

        for channel_id, perms in self.data["channel_permissions"].items():
            channel = guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.StageChannel)):
                channels_not_found += 1
                continue

            try:
                default_role = guild.default_role

                await channel.set_permissions(
                    default_role,
                    send_messages=perms["send_messages"],
                    send_messages_in_threads=perms["send_messages_in_threads"],
                    create_public_threads=perms["create_public_threads"],
                    create_private_threads=perms["create_private_threads"],
                    connect=perms["connect"],
                    speak=perms["speak"],
                    reason=f"Lockdown lifted by {actor}"
                )

                staff_role = guild.get_role(self.STAFF_ROLE_ID)
                if staff_role and isinstance(channel, discord.TextChannel):
                    overwrites = channel.overwrites_for(staff_role)
                    if overwrites.is_empty():
                        await channel.set_permissions(
                            staff_role,
                            overwrite=None,
                            reason=f"Lockdown lifted by {actor} —— Removing staff override"
                        )

                channels_restored += 1

            except discord.Forbidden:
                continue
            except Exception:
                continue

        self.data["active"] = False
        self.data["activated_at"] = None
        self.data["activated_by"] = None
        self.data["reason"] = None
        self.data["channel_permissions"] = {}
        self.save_data()

        await self.cases_manager.log_case(
            guild=guild,
            case_type=CaseType.LOCKDOWN_REMOVE,
            moderator=actor,
            reason="Lockdown lifted",
            target_user=None,
            metadata={"channels_restored": channels_restored}
        )

        embed = discord.Embed(
            title="Lockdown Lifted",
            color=COLOR_GREEN,
            timestamp=datetime.now()
        )
        embed.add_field(name="Director", value=actor.mention, inline=True)
        embed.add_field(name="Channels Restored", value=str(channels_restored), inline=True)

        if channels_not_found > 0:
            embed.add_field(
                name=f"{CONTESTED_EMOJI_ID} Channels Not Found",
                value=f"{channels_not_found} channel(s) no longer exist and could not be restored.",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.data["active"]:
            return

        if member.bot:
            return

        guild = member.guild

        try:
            bot_member = guild.get_member(self.bot.user.id) if self.bot.user else None
            if bot_member:
                await self.cases_manager.log_case(
                    guild=guild,
                    case_type=CaseType.KICK,
                    moderator=bot_member,
                    reason="*Server is in lockdown —— automatic kick*",
                    target_user=member,
                    metadata={"auto_kick": True, "lockdown": True}
                )

            await member.kick(reason="Server is in lockdown")

        except discord.Forbidden:
            pass
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(LockdownCommands(cast(UtilityBot, bot)))