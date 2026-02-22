from __future__ import annotations

import discord
from discord.ext import commands

import functools
from dataclasses import (
    dataclass,
    field
)
from typing import (
    Awaitable,
    Optional,
    Union,
    Protocol,
    Callable,
    Any,
    runtime_checkable,
    cast,
    TypeVar,
    ParamSpec,
    Coroutine
)

from constants import(
    ACCEPTED_EMOJI_ID,
    DENIED_EMOJI_ID,
    CONTESTED_EMOJI_ID,

    COLOR_BLURPLE,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
)

P = ParamSpec("P")
T = TypeVar("T")

@runtime_checkable
class HelpCallback(Protocol):
    __help_data__: CommandHelpData
    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[Any]: ...

@dataclass
class ArgumentInfo:
    role:        Optional[int] = None
    required:    bool          = True
    description: Optional[str] = None
    is_flag:     bool          = False
    choices:     list[str]     = field(default_factory=list)

@dataclass
class CommandHelpData:
    desc:         str
    prefix:       bool
    slash:        bool
    run_role:     Optional[int]
    has_inverse:  Union[bool, str]
    arguments:    dict[str, ArgumentInfo] = field(default_factory=dict)
    aliases:      list[str]               = field(default_factory=list)

class HelpedCallable:
    __help_data__: CommandHelpData

def help_description(
    desc: str,
    prefix: bool = False,
    slash: bool = True,
    run_role: Optional[int] = None,
    has_inverse: Union[bool, str] = False,
    arguments: Optional[dict[str, ArgumentInfo]] = None,
    aliases: Optional[list[str]] = None,
):
    arguments = arguments or {}
    aliases   = aliases   or []

    def decorator(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, Coroutine[Any, Any, T]]:
        data = CommandHelpData(
            desc=desc,
            prefix=prefix,
            slash=slash,
            run_role=run_role,
            has_inverse=has_inverse,
            arguments=arguments,
            aliases=aliases,
        )

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await func(*args, **kwargs)

        cast(HelpedCallable, wrapper).__help_data__ = data
        return wrapper

    return decorator

def _member_has_role(member: discord.Member, role_id: Optional[int]) -> bool:
    if role_id is None:
        return True
    return any(r.id == role_id for r in member.roles)

def _check_access(
    member: discord.Member,
    data:   CommandHelpData,
) -> tuple[str, list[str], list[str]]:
    can_run = _member_has_role(member, data.run_role)
    if not can_run:
        return "none", [], list(data.arguments.keys())

    accessible, inaccessible = [], []
    for arg_name, arg_info in data.arguments.items():
        if _member_has_role(member, arg_info.role):
            accessible.append(arg_name)
        else:
            inaccessible.append(arg_name)

    if inaccessible:
        return "partial", accessible, inaccessible
    return "full", accessible, inaccessible

def _build_argument_line(name: str, info: ArgumentInfo) -> str:
    if info.choices:
        choices_str = "|".join(info.choices)
        inner = f"{name}: {choices_str}"
        return f"{{{inner}}}" if info.required else f"[{inner}]"

    if info.is_flag:
        inner = f"/{name}: {{{name}}}"
        return inner if info.required else f"[{inner}]"

    return f"{{{name}}}" if info.required else f"[{name}]"

def _build_help_view(
    command_name: str,
    data:         CommandHelpData,
    member:       discord.Member,
) -> discord.ui.LayoutView:

    arg_tokens = " ".join(
        _build_argument_line(n, i) for n, i in data.arguments.items()
    )

    usage_lines: list[str] = []
    if data.prefix:
        usage_lines.append(f"{command_name} {arg_tokens}".strip())
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

    main_text = (
        f"# \"{command_name}\" Command\n"
        f"## Description:\n{data.desc}\n"
        f"## Arguments:\n"
        f"```python\n{usage_block}\n```\n"
        f"-# {{…}} denotes a required argument\n"
        f"-# […] denotes an optional argument\n\n"
        f"{arg_details}"
        f"## Variants:\n"
        f"- {prefix_emoji} **Prefix**\n"
        f"- {slash_emoji} **Slash**"
        f"{aliases_line}"
        f"{inverse_line}"
    )

    status, accessible_args, inaccessible_args = _check_access(member, data)

    if status == "full":
        perm_colour = COLOR_GREEN
        perm_text = (
            f"### {ACCEPTED_EMOJI_ID} Authorized.\n"
            f"-# Valid permissions.\n"
            f"You have the necessary permissions to run this command."
        )

    elif status == "none":
        perm_colour = COLOR_RED
        perm_text = (
            f"### {DENIED_EMOJI_ID} Unauthorized!\n"
            f"-# Invalid permissions.\n"
            f"You lack the necessary permissions to run this command."
        )

    else:
        perm_colour = COLOR_YELLOW

        if not accessible_args:
            detail = (
                "None —— You lack access to all of this command's arguments."
            )
        else:
            detail = ", ".join(f"`{a}`" for a in accessible_args)

        perm_text = (
            f"### {CONTESTED_EMOJI_ID} Partially Authorized.\n"
            f"-# Partially valid permissions.\n"
            f"You have the necessary permissions to run this command, "
            f"but not all of its arguments. Specifically, you have access "
            f"to these arguments:\n- {detail}"
        )

    class HelpView(discord.ui.LayoutView):
        container1 = discord.ui.Container(
            discord.ui.TextDisplay(content=main_text),
            accent_color=COLOR_BLURPLE,
        )
        container2 = discord.ui.Container(
            discord.ui.TextDisplay(content=perm_text),
            accent_color=perm_colour,
        )

    return HelpView()

def _resolve_command(bot: commands.Bot, name: str) -> Optional[Callable[..., Awaitable[Any]]]:
    cmd = bot.get_command(name)
    if cmd:
        return cmd.callback

    for app_cmd in bot.tree.get_commands():
        if app_cmd.name == name:
            return getattr(app_cmd, "callback", None)

    return None

def _find_nested_command(bot: commands.Bot, parts: list[str]) -> Optional[object]:
    full = " ".join(parts)
    result = _resolve_command(bot, full)
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
        children = getattr(node, "commands", None) or []
        found = next((c for c in children if c.name == part), None)
        if found is None:
            return None
        node = found

    return getattr(node, "callback", None)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Listing helpers
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def _collect_slash_commands(
    app_commands_list: list[Any],
    seen_callbacks:    set[int],
    lines:             list[str],
) -> None:
    for app_cmd in app_commands_list:
        cb = getattr(app_cmd, "callback", None)
        if cb and hasattr(cb, "__help_data__") and id(cb) not in seen_callbacks:
            seen_callbacks.add(id(cb))
            qualified = getattr(app_cmd, "qualified_name", app_cmd.name)
            lines.append(f"`/{qualified}` — {cast(HelpedCallable, cb).__help_data__.desc}")

        sub_commands = getattr(app_cmd, "commands", None)
        if sub_commands:
            _collect_slash_commands(sub_commands, seen_callbacks, lines)

async def _run_help(
    bot: commands.Bot,
    ctx_or_inter: Union[commands.Context, discord.Interaction],
    command_name: Optional[str],
):
    if isinstance(ctx_or_inter, commands.Context):
        if not isinstance(ctx_or_inter.author, discord.Member):
            await ctx_or_inter.send("Cannot resolve guild member context.")
            return
        member  = ctx_or_inter.author
        respond = ctx_or_inter.send
    else:
        if not isinstance(ctx_or_inter.user, discord.Member):
            await ctx_or_inter.response.send_message(
                "Cannot resolve guild member context.",
                ephemeral=True,
            )
            return
        member  = ctx_or_inter.user
        respond = ctx_or_inter.response.send_message

    if not command_name:
        seen_callbacks: set[int] = set()
        lines: list[str] = []

        for cmd in bot.commands:
            cb = cast(HelpedCallable, cmd.callback)
            if hasattr(cb, "__help_data__"):
                seen_callbacks.add(id(cb))
                lines.append(f"`{cmd.name}` — {cb.__help_data__.desc}")

        _collect_slash_commands(bot.tree.get_commands(), seen_callbacks, lines)

        if lines:
            await respond(
                embed=discord.Embed(
                    title="Available Commands",
                    description="\n".join(lines),
                    color=COLOR_BLURPLE,
                )
            )
        else:
            await respond("No documented commands found.", ephemeral=True)
        return

    parts    = command_name.strip().lstrip("/").split()
    callback = _find_nested_command(bot, parts)

    if callback is None or not hasattr(callback, "__help_data__"):
        await respond(
            f"Command `{command_name}` not found or has no help data.",
            ephemeral=True,
        )
        return

    data = cast(HelpedCallable, callback).__help_data__

    view = _build_help_view(
        command_name=" ".join(parts),
        data=data,
        member=member,
    )
    await respond(view=view)