from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar, cast, runtime_checkable

import discord
from discord.ext import commands
from discord.ui import Container, LayoutView, TextDisplay

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

    from discord.app_commands import Group as AppGroup

from constants import (
    ACCEPTED_EMOJI_ID,
    COLOR_BLURPLE,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

P    = ParamSpec("P")
T_co = TypeVar("T_co", covariant=True)

@runtime_checkable
class HelpCallback(Protocol[P, T_co]):
    __help_data__: CommandHelpData
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T_co]: ...

@dataclass
class RoleConfig:
    role_id  : int
    channels : list[int] = field(default_factory=list)

@dataclass
class UserConfig:
    user_id  : int
    channels : list[int] = field(default_factory=list)

@dataclass
class ArgumentInfo:
    roles       : list[int]  = field(default_factory=list)
    required    : bool       = True
    description : str | None = None
    is_flag     : bool       = False
    choices     : list[str]  = field(default_factory=list)

@dataclass
class CommandHelpData:
    desc        : str
    prefix      : bool
    slash       : bool
    run_roles   : list[RoleConfig]
    run_users   : list[UserConfig]
    has_inverse : bool | str
    arguments   : dict[str, ArgumentInfo] = field(default_factory=dict)
    aliases     : list[str]               = field(default_factory=list)

class HelpedCallable:
    __help_data__: CommandHelpData = field(init=False)

def help_description(
    desc        :                           str,
    *,
    prefix      :                           bool = False,
    slash       :                           bool = True,
    run_roles   :        list[RoleConfig] | None = None,
    run_users   :        list[UserConfig] | None = None,
    has_inverse :                    bool | str  = False,
    arguments   : dict[str, ArgumentInfo] | None = None,
    aliases     :               list[str] | None = None,
) -> Callable[[Callable[P, Coroutine[Any, Any, T_co]]], Callable[P, Coroutine[Any, Any, T_co]]]:
    run_roles = run_roles or []
    run_users = run_users or []
    arguments = arguments or {}
    aliases   = aliases   or []

    def decorator(func : Callable[P, Coroutine[Any, Any, T_co]]) -> Callable[P, Coroutine[Any, Any, T_co]]:
        data = CommandHelpData(
            desc        = desc,
            prefix      = prefix,
            slash       = slash,
            run_roles   = run_roles,
            run_users   = run_users,
            has_inverse = has_inverse,
            arguments   = arguments,
            aliases     = aliases,
        )

        cast("HelpedCallable", func).__help_data__ = data
        return func

def member_has_role(member: discord.Member, role_id : int) -> bool:
    return any(r.id == role_id for r in member.roles)

def check_access(
    member      : discord.Member,
    data        : CommandHelpData,
    _channel_id : int | None = None,
) -> tuple[str, list[str], list[str], list[int]]:
    member_role_ids = {r.id for r in member.roles}

    user_match = next((uc for uc in data.run_users if uc.user_id == member.id), None)
    if user_match is not None:
        allowed_channels: list[int] = [] if not user_match.channels else sorted(user_match.channels)

        accessible   : list[str] = []
        inaccessible : list[str] = []
        for arg_name, arg_info in data.arguments.items():
            if not arg_info.roles or member_role_ids.intersection(arg_info.roles):
                accessible.append(arg_name)
            else:
                inaccessible.append(arg_name)

        if inaccessible or allowed_channels:
            return "partial", accessible, inaccessible, allowed_channels
        return "full", accessible, inaccessible, allowed_channels

    if data.run_roles:
        matching = [rc for rc in data.run_roles if rc.role_id in member_role_ids]
        if not matching:
            return "none", [], list(data.arguments.keys()), []

        unrestricted = any(not rc.channels for rc in matching)
        if unrestricted:
            allowed_channels = []
        else:
            seen: set[int] = set()
            for rc in matching:
                seen.update(rc.channels)
            allowed_channels = sorted(seen)
    else:
        allowed_channels = []

    accessible   = []
    inaccessible = []
    for arg_name, arg_info in data.arguments.items():
        if not arg_info.roles or member_role_ids.intersection(arg_info.roles):
            accessible.append(arg_name)
        else:
            inaccessible.append(arg_name)

    channel_restricted = bool(allowed_channels)
    if inaccessible or channel_restricted:
        return "partial", accessible, inaccessible, allowed_channels
    return "full", accessible, inaccessible, allowed_channels

def build_argument_line(name: str, info: ArgumentInfo) -> str:
    if info.choices:
        choices_str = "|".join(info.choices)
        inner = f"{name}: {choices_str}"
        return f"{{{inner}}}" if info.required else f"[{inner}]"

    if info.is_flag:
        inner = f"/{name}: {{{name}}}"
        return inner if info.required else f"[{inner}]"

    return f"{{{name}}}" if info.required else f"[{name}]"

def build_help_view(
    command_name : str,
    data         : CommandHelpData,
    member       : discord.Member,
) -> LayoutView:

    arg_tokens = " ".join(
        build_argument_line(n, i) for n, i in data.arguments.items()
    )

    usage_lines: list[str] = []
    if data.prefix:
        usage_lines.append(f".{command_name} {arg_tokens}".strip())
    if data.slash:
        usage_lines.append(f"/{command_name} {arg_tokens}".strip())
    usage_block = "\n".join(usage_lines)

    arg_details_lines: list[str] = []
    for arg_name, arg_info in data.arguments.items():
        if arg_info.choices:
            choices_str = "|".join(arg_info.choices)
            bracket = f"{{{arg_name}: {choices_str}}}" if arg_info.required else f"[{arg_name}: {choices_str}]"
        elif arg_info.is_flag:
            bracket = f"{arg_name}: {{{arg_name}}}" if arg_info.required else f"[{arg_name}: {arg_name}]"
        else:
            bracket = f"{{{arg_name}}}" if arg_info.required else f"[{arg_name}]"

        line = f"**{bracket.capitalize()}**"
        if arg_info.is_flag:
            line += " [Flag]"
        if arg_info.choices:
            line += " [Choices]"
        if arg_info.roles:
            roles_str = " ".join(f"<@&{rid}>" for rid in arg_info.roles)
            line += f" [Roles: {roles_str}]"
        if arg_info.description:
            line += f"\n{arg_info.description}"
        arg_details_lines.append(line)
    arg_details = ("\n".join(arg_details_lines) + "\n") if arg_details_lines else ""

    prefix_emoji = ACCEPTED_EMOJI_ID if data.prefix else DENIED_EMOJI_ID
    slash_emoji  = ACCEPTED_EMOJI_ID if data.slash  else DENIED_EMOJI_ID

    aliases_line = ""
    if data.aliases:
        formatted = ", ".join(f"`{a}`" for a in data.aliases)
        aliases_line = f"\n**Aliases:** {formatted}"

    inverse_line = ""
    if data.has_inverse and isinstance(data.has_inverse, str):
        inverse_line = f"\nThis command has an inverse, **{data.has_inverse}**."

    roles_lines: list[str] = []
    if data.run_roles:
        for rc in data.run_roles:
            role_mention = f"<@&{rc.role_id}>"
            if rc.channels:
                channels_str = " ".join(f"<#{cid}>" for cid in rc.channels)
                roles_lines.append(f"- {role_mention} *(channels: {channels_str})*")
            else:
                roles_lines.append(f"- {role_mention}")

    if data.run_users:
        for uc in data.run_users:
            user_mention = f"<@{uc.user_id}>"
            if uc.channels:
                channels_str = " ".join(f"<#{cid}>" for cid in uc.channels)
                roles_lines.append(f"- {user_mention} *(channels: {channels_str})*")
            else:
                roles_lines.append(f"- {user_mention}")

    roles_block = "\n".join(roles_lines) if roles_lines else "- No role restriction."

    main_text = (
        f'# "{command_name}" Command\n'
        f"## Description:\n{data.desc}\n"
        f"## Required Roles:\n{roles_block}\n"
         "## Arguments:\n"
        f"```python\n{usage_block}\n```\n"
         "-# {{…}} denotes a required argument\n"
         "-# […] denotes an optional argument\n\n"
        f"{arg_details}"
         "## Variants:\n"
        f"- {prefix_emoji} **Prefix**\n"
        f"- {slash_emoji} **Slash**"
        f"{aliases_line}"
        f"{inverse_line}"
    )

    status, accessible_args, _, allowed_channels = check_access(member, data)

    if status == "full":
        perm_colour = COLOR_GREEN
        perm_text = (
            f"### {ACCEPTED_EMOJI_ID} Authorized.\n"
             "-# Valid permissions.\n"
             "You have the necessary permissions to run this command."
        )

    elif status == "none":
        perm_colour = COLOR_RED
        perm_text = (
            f"### {DENIED_EMOJI_ID} Unauthorized!\n"
             "-# Invalid permissions.\n"
             "You are not authorized to run this command."
        )

    else:
        perm_colour = COLOR_YELLOW

        if not accessible_args:
            args_detail = "None —— You lack access to all of this command's arguments."
        else:
            args_detail = ", ".join(f"`{a}`" for a in accessible_args)

        channel_detail = ""
        if allowed_channels:
            channels_str = " ".join(f"<#{cid}>" for cid in allowed_channels)
            channel_detail = f"\nYou may only use this command in: {channels_str}"

        perm_text = (
            f"### {CONTESTED_EMOJI_ID} Partially Authorized.\n"
             "-# Partially valid permissions.\n"
             "You have the necessary permissions to run this command, "
             "but not all of its arguments. Specifically, you have access "
            f"to these arguments:\n- {args_detail}"
            f"{channel_detail}"
        )

    class HelpView(LayoutView):
        container1: Container[LayoutView] = Container(
            TextDisplay(content = main_text),
            accent_color = COLOR_BLURPLE,
        )
        container2: Container[LayoutView] = Container(
            TextDisplay(content = perm_text),
            accent_color = perm_colour,
        )

    return HelpView()

def resolve_command(bot: commands.Bot, name: str) -> Callable[..., Awaitable[Any]] | None:
    cmd = bot.get_command(name)
    if cmd:
        return cmd.callback

    for app_cmd in bot.tree.get_commands():
        if app_cmd.name == name:
            return getattr(app_cmd, "callback", None)

    return None

def find_nested_command(bot: commands.Bot, parts: list[str]) -> object | None:
    full = " ".join(parts)
    result = resolve_command(bot, full)
    if result:
        return result

    node = None
    for app_cmd in bot.tree.get_commands():
        if app_cmd.name == parts[0]:
            node = app_cmd
            break

    if node is None:
        return None

    for part in parts[1:]:
        children : list[AppGroup] = getattr(node, "commands", None) or []
        found = next((c for c in children if c.name == part), None)
        if found is None:
            return None
        node = found

    return getattr(node, "callback", None)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def collect_slash_commands(
    app_commands_list : list[Any],
    seen_callbacks    : set[int],
    lines             : list[str],
) -> None:
    for app_cmd in app_commands_list:
        cb = getattr(app_cmd, "callback", None)
        if cb and hasattr(cb, "__help_data__") and id(cb) not in seen_callbacks:
            seen_callbacks.add(id(cb))
            qualified = getattr(app_cmd, "qualified_name", app_cmd.name)
            lines.append(f"`/{qualified}` — {cast('HelpedCallable', cb).__help_data__.desc}")

        sub_commands = getattr(app_cmd, "commands", None)
        if sub_commands:
            collect_slash_commands(sub_commands, seen_callbacks, lines)

async def run_help(
    bot          : commands.Bot,
    ctx_or_inter : commands.Context[commands.Bot] | discord.Interaction,
    command_name :                            str | None,
) -> None:
    if isinstance(ctx_or_inter, commands.Context):
        if not isinstance(ctx_or_inter.author, discord.Member):
            _ = await ctx_or_inter.send("Cannot resolve guild member context.")
            return
        member  = ctx_or_inter.author
        respond = ctx_or_inter.send
    else:
        if not isinstance(ctx_or_inter.user, discord.Member):
            _ = await ctx_or_inter.response.send_message(
                "Cannot resolve guild member context.",
                ephemeral = True,
            )
            return
        member  = ctx_or_inter.user
        respond = ctx_or_inter.response.send_message

    if not command_name:
        seen_callbacks: set[int] = set()
        lines: list[str] = []

        for cmd in bot.commands:
            cb = cast("HelpedCallable", cmd.callback)
            if hasattr(cb, "__help_data__"):
                seen_callbacks.add(id(cb))
                lines.append(f"`{cmd.name}` — {cb.__help_data__.desc}")

        collect_slash_commands(bot.tree.get_commands(), seen_callbacks, lines)

        if lines:
            _ = await respond(
                embed = discord.Embed(
                    title       = "Available Commands",
                    description = "\n".join(lines),
                    color       = COLOR_BLURPLE,
                ),
            )
        else:
            _ = await respond("No documented commands found.", ephemeral = True)
        return

    parts    = command_name.strip().lstrip("/").split()
    callback = find_nested_command(bot, parts)

    if callback is None or not hasattr(callback, "__help_data__"):
        _ = await respond(
            f"Command `{command_name}` not found or has no help data.",
            ephemeral = True,
        )
        return

    data = cast("HelpedCallable", callback).__help_data__

    view = build_help_view(
        command_name = " ".join(parts),
        data         = data,
        member       = member,
    )
    _ = await respond(view = view)
