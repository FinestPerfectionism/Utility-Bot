from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import TypedDict, cast

import discord
from discord.ext import commands

from constants import (
    DIRECTORS_ROLE_ID,
    SUPPORTING_DIRECTORS_ROLE_ID,
)
from core.help import ArgumentInfo, RoleConfig, help_description
from core.responses import send_custom_message

NOMINATION_DATA_FILE = "nomination_data.json"

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Data Helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class NominationCase(TypedDict):
    target_id : int
    acceptors : list[int]

def load_nomination_data() -> dict[str, NominationCase]:
    if not Path(NOMINATION_DATA_FILE).exists():
        return {}
    with Path(NOMINATION_DATA_FILE).open() as f:
        return cast("dict[str, NominationCase]", json.load(f))

def save_nomination_data(data: dict[str, NominationCase]) -> None:
    with Path(NOMINATION_DATA_FILE).open("w") as f:
        json.dump(data, f, indent=2)


def extract_name(nickname: str) -> str:
    if nickname and "|" in nickname:
        return nickname.split("|")[-1].strip()
    return nickname


# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Nomination Flags
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class NominationFlags(commands.FlagConverter, prefix="/", delimiter=" "):
    action  : str                    = commands.flag(aliases=["a"])
    user    : discord.Member | None  = commands.flag(aliases=["u"], default=None)
    case_id : str            | None  = commands.flag(name="id", default=None)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Nomination Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class NominationCommands(commands.Cog):
    def __init__(self, bot : commands.Bot) -> None:
        self.bot  = bot
        self.data : dict[str, NominationCase] = load_nomination_data()

    def _is_director(self, member: discord.Member) -> bool:
        return any(role.id == DIRECTORS_ROLE_ID for role in member.roles)

    def _get_directors(self, guild: discord.Guild) -> list[discord.Member]:
        role = guild.get_role(DIRECTORS_ROLE_ID)
        if role is None:
            return []
        return list(role.members)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .nomination/.nom Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="nomination", aliases=["nom"])
    @help_description(
        desc      = "Directors only —— Triggrs, accepts, or denies supporting-director nominations.",
        prefix    = True,
        slash     = False,
        run_roles = [RoleConfig(role_id=DIRECTORS_ROLE_ID)],
        aliases   = ["nom"],
        arguments = {
            "action": ArgumentInfo(description="Use `/action trigger`, `/action accept`, or `/action deny`.", is_flag=True),
            "user"  : ArgumentInfo(required = False, description="Target member for the nomination trigger.", is_flag=True),
            "id"    : ArgumentInfo(required = False, description="Nomination case ID used by trigger, accept, and deny.", is_flag=True),
        },
    )
    async def nomination(
        self,
        ctx   : commands.Context[commands.Bot],
        *,
        flags : NominationFlags,
    ) -> None:
        if not ctx.guild:
            await send_custom_message(
                ctx,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        invoker = ctx.author
        if not isinstance(invoker, discord.Member):
            return

        if not self._is_director(invoker):
            await send_custom_message(
                ctx,
                msg_type = "error",
                title    = "run command",
                subtitle = "You are not authorized to run this command.",
                footer   = "No permissions",
            )
            return

        action = flags.action.lower()
        guild  = ctx.guild

        if action == "trigger":
            await self._handle_trigger(ctx, guild, flags, invoker)
        elif action == "accept":
            await self._handle_accept(ctx, guild, flags, invoker)
        elif action == "deny":
            await self._handle_deny(ctx, flags)

    async def _handle_trigger(
        self,
        ctx      : commands.Context[commands.Bot],
        _guild   : discord.Guild,
        flags    : NominationFlags,
        _invoker : discord.Member,
    ) -> None:
        target  = flags.user
        case_id = flags.case_id

        if target is None or case_id is None:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "trigger nomination",
                subtitle = "A target user and case ID are required.",
                footer   = "Bad argument",
            )
            return

        if case_id in self.data:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "trigger nomination",
                subtitle = f"A nomination case with ID `{case_id}` already exists.",
                footer   = "Bad argument",
            )
            return

        if target.bot:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "trigger nomination",
                subtitle = "You cannot nominate a bot.",
                footer   = "Bad argument",
            )
            return

        case: NominationCase = {
            "target_id": target.id,
            "acceptors": [],
        }
        self.data[case_id] = case
        save_nomination_data(self.data)

        await send_custom_message(
            ctx,
            msg_type  = "success",
            title     = "start Director Nomination",
            subtitle  = f"ID: `{case_id}`",
            ephemeral = False,
        )

    async def _handle_accept(
        self,
        ctx     : commands.Context[commands.Bot],
        guild   : discord.Guild,
        flags   : NominationFlags,
        invoker : discord.Member,
    ) -> None:
        case_id = flags.case_id

        if case_id is None or case_id not in self.data:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "accept nomination",
                subtitle = f"No nomination case with ID `{case_id}` was found.",
                footer   = "Bad argument",
            )
            return

        case = self.data[case_id]

        if invoker.id in case["acceptors"]:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "accept nomination",
                subtitle = "You have already accepted this nomination.",
                footer   = "Bad request",
            )
            return

        case["acceptors"].append(invoker.id)
        save_nomination_data(self.data)

        directors    = self._get_directors(guild)
        director_ids = {d.id for d in directors}
        n            = sum(1 for uid in case["acceptors"] if uid in director_ids)
        m            = len(directors)

        await send_custom_message(
            ctx,
            msg_type  = "success",
            title     = f"add Director Nomination to nomination case `{case_id}`",
            subtitle  = f"{n}/{m} Directors for.",
            ephemeral = False,
        )

        if m > 0 and n >= m:
            await self._complete_nomination(guild, case_id, case)

    async def _complete_nomination(
        self,
        guild   : discord.Guild,
        case_id : str,
        case    : NominationCase,
    ) -> None:
        target = guild.get_member(case["target_id"])

        _ = self.data.pop(case_id, None)
        save_nomination_data(self.data)

        if target is None:
            return

        directors_role  = guild.get_role(DIRECTORS_ROLE_ID)
        supporting_role = guild.get_role(SUPPORTING_DIRECTORS_ROLE_ID)

        if directors_role is None or supporting_role is None:
            return

        with contextlib.suppress(discord.Forbidden, discord.HTTPException):
            await target.add_roles(directors_role, supporting_role)

        original_nick = target.nick or target.name
        new_nick      = f"S. Director | {extract_name(original_nick)}"

        n_32 = 32
        if len(new_nick) <= n_32:
            with contextlib.suppress(discord.Forbidden, discord.HTTPException):
                _ = await target.edit(nick=new_nick)

    async def _handle_deny(
        self,
        ctx   : commands.Context[commands.Bot],
        flags : NominationFlags,
    ) -> None:
        case_id = flags.case_id

        if case_id is None or case_id not in self.data:
            await send_custom_message(
                ctx,
                msg_type = "warning",
                title    = "deny nomination",
                subtitle = f"No nomination case with ID `{case_id}` was found.",
                footer   = "Bad argument",
            )
            return

        _ = self.data.pop(case_id, None)
        save_nomination_data(self.data)

        await send_custom_message(
            ctx,
            msg_type  = "information",
            title     = f"Nomination case `{case_id}` ended",
            subtitle  = f"Director {ctx.author.mention} has denied the nomination.",
            ephemeral = False,
        )

async def setup(bot : commands.Bot) -> None:
    await bot.add_cog(NominationCommands(bot))
