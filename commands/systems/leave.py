import discord
from discord.ext import commands
from discord import app_commands

from typing import Any
import json
import os
import contextlib

from core.help import (
    RoleConfig,
    help_description,
    ArgumentInfo
)
from core.utils import (
    send_minor_error,
    send_major_error
)
from core.permissions import (
    is_director,
    is_staff,
)

from constants import (
    BOT_OWNER_ID,
    DIRECTORS_ROLE_ID,
    STAFF_ROLE_ID,
    PERSONAL_LEAVE_ROLE_ID,
)

DATA_FILE = "leave_data.json"

def load_data() -> dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data: dict[str, Any]) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def extract_name(nickname: str) -> str:
    if nickname and "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname

def can_manage_leave(invocator: discord.Member, target: discord.Member) -> bool:
    if not is_staff(invocator):
        return False

    modifying_other = target.id != invocator.id

    if modifying_other:
        return is_director(invocator)

    return True


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Leave Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class LeaveCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.data = load_data()

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /leave Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    leave_group = app_commands.Group(
        name="leave",
        description="Staff only —— Leave commands."
    )

    @leave_group.command(name="add", description="Add personal leave to yourself or another user.")
    @help_description(
        desc        = f"The leave add command adds the <@{PERSONAL_LEAVE_ROLE_ID}> role to a staff member, and changes their nickname to \"P. Leave | username\". Their username is stored and restored upon /leave remove.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        has_inverse = "/leave remove",
        arguments   = {
            "target": ArgumentInfo(
                roles    = [DIRECTORS_ROLE_ID],
                required = False,
                description = "The user to add personal leave to."
            ),
        },
    )
    @app_commands.describe(target="The user to add personal leave to.")
    async def leave_add(
        self,
        interaction: discord.Interaction,
        target: discord.Member | None = None
    ) -> None:
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=True)

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(
                interaction,
                "Bots cannot go on personal leave.",
            )
            return

        if not is_staff(invocator):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )
            return

        if not is_staff(target_member):
            await send_minor_error(
                interaction,
                "Target must exist within the Goobers Staff Team.",
            )
            return

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to add personal leave to other Staff Members.",
                subtitle="Invalid permissions."
            )
            return

        if str(target_member.id) in self.data:
            await send_minor_error(
                interaction,
                "User is already on personal leave.",
            )
            return

        role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if role is None:
            await send_major_error(
                interaction,
                "I could not fetch the Personal Leave role.",
                subtitle=f"Invalid Configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if role in target_member.roles:
            await send_minor_error(
                interaction,
                "User already has the Personal Leave role.",
            )
            return

        original_full_nick = target_member.nick or target_member.name
        actual_name = extract_name(original_full_nick)
        new_nick = f"P. Leave | {actual_name}"

        if len(new_nick) > 32:
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The resulting nickname exceeds Discord's 32 character limit.",
                subtitle="Invalid operation."
            )
            return

        role_added = False
        nick_changed = False

        try:
            await target_member.add_roles(role)
            role_added = True

            await target_member.edit(nick=new_nick)
            nick_changed = True

            self.data[str(target_member.id)] = original_full_nick
            save_data(self.data)

            if target_member.id == interaction.user.id:
                await interaction.followup.send(
                    "You have been placed on personal leave.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been placed on personal leave.",
                    ephemeral=True
                )

        except discord.Forbidden:
            if role_added:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.remove_roles(role)

            if not role_added:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="I lack the necessary permissions to assign the Personal Leave role.",
                    subtitle="Invalid configuration. Contact the owner."
                )
            elif not nick_changed:
                if target_member.id == interaction.guild.owner_id:
                    await send_minor_error(
                        interaction,
                        title="Error!",
                        texts="The role was added, but I cannot change the server owner's nickname. Please change it manually.",
                    )
                else:
                    await send_major_error(
                        interaction,
                        title="Error!",
                        texts="I lack the necessary permissions to change this user's nickname.",
                        subtitle="Invalid configuration. Contact the owner."
                    )
            return

        except discord.HTTPException:
            if role_added:
                with contextlib.suppress(discord.HTTPException):
                    await target_member.remove_roles(role)

            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}> if this persists."
            )
            return

    @leave_group.command(name="remove", description="Remove personal leave from yourself or another user.")
    @app_commands.describe(target="The user to remove personal leave from.")
    @help_description(
        desc        = f"The leave remove command removes the <@{PERSONAL_LEAVE_ROLE_ID}> role from a staff member, and changes their nickname back to before they were on leave.",
        prefix      = False,
        slash       = True,
        run_roles   = [RoleConfig(role_id=STAFF_ROLE_ID)],
        has_inverse = "/leave add",
        arguments   = {
            "target": ArgumentInfo(
                roles=[DIRECTORS_ROLE_ID],
                required=False,
                description="The user to remove leave from."
            ),
        },
    )
    async def leave_remove(
        self,
        interaction: discord.Interaction,
        target: discord.Member | None = None
    ) -> None:
        if not interaction.guild:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle="Bad command environment."
            )
            return

        await interaction.response.defer(ephemeral=True)

        invocator = interaction.user
        if not isinstance(invocator, discord.Member):
            return

        target_member = target or invocator

        if target_member.bot:
            await send_minor_error(
                interaction,
                "Bots cannot go on personal leave.",
            )
            return

        if not is_staff(invocator):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to run this command.",
                subtitle="Invalid permissions."
            )
            return

        if not is_staff(target_member):
            await send_minor_error(
                interaction,
                "Target must exist within the Goobers Staff Team.",
            )
            return

        if not can_manage_leave(invocator, target_member):
            await send_major_error(
                interaction,
                title="Unauthorized!",
                texts="You lack the necessary permissions to remove personal leave from other Staff Members.",
                subtitle="Invalid permissions."
            )
            return

        stored_name = self.data.get(str(target_member.id))
        if not stored_name:
            await send_minor_error(
                interaction,
                "User is not on personal leave.",
            )
            return

        role = interaction.guild.get_role(PERSONAL_LEAVE_ROLE_ID)
        if role is None:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I could not fetch the Personal Leave role.",
                subtitle=f"Invalid configuration. Contact an administrator and <@{BOT_OWNER_ID}>."
            )
            return

        if role not in target_member.roles:
            self.data.pop(str(target_member.id), None)
            save_data(self.data)
            await send_minor_error(
                interaction,
                "User does not have the Personal Leave role.",
            )
            return

        nickname_error = None

        try:
            await target_member.remove_roles(role)

            current_nick = target_member.nick or target_member.name
            expected_nick = f"P. Leave | {extract_name(stored_name)}"

            if current_nick == expected_nick:
                try:
                    await target_member.edit(nick=stored_name)
                except discord.Forbidden:
                    nickname_error = "forbidden"
                except discord.HTTPException:
                    nickname_error = "http"

            self.data.pop(str(target_member.id), None)
            save_data(self.data)

        except discord.Forbidden:
            await send_major_error(
                interaction,
                title="Error!",
                texts="I lack the necessary permissions to remove the Personal Leave role.",
                subtitle="Invalid configuration. Contact the owner."
            )
            return

        except discord.HTTPException:
            await send_major_error(
                interaction,
                title="Error!",
                texts="A Discord API error occurred while removing the role. Please try again later.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
            return

        if nickname_error == "forbidden":
            if target_member.id == interaction.guild.owner_id:
                await send_minor_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I cannot change the server owner's nickname. Please change it back manually.",
                    subtitle="Not an error."
                )
            else:
                await send_major_error(
                    interaction,
                    title="Error!",
                    texts="The role was removed, but I lack the necessary permissions to change the nickname. Please change it back manually.",
                    subtitle="Invalid configuration. Contact the owner."
                )
        elif nickname_error == "http":
            await send_minor_error(
                interaction,
                title="Error!",
                texts="The role was removed, but a Discord API error prevented the nickname from being restored.",
                subtitle=f"Invalid operation. Contact <@{BOT_OWNER_ID}>."
            )
        else:
            if target_member.id == interaction.user.id:
                await interaction.followup.send(
                    "You have been removed from personal leave.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"{target_member.mention} has been removed from personal leave.",
                    ephemeral=True
                )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaveCommands(bot))