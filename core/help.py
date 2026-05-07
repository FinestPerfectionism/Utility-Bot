from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
    runtime_checkable,
)

import discord
from discord.ext import commands
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from collections.abc import (
        Awaitable,
        Callable,
        Coroutine,
        Sequence,
    )

    from discord.app_commands import Group as AppGroup
    from discord import SeparatorSpacing


from constants import (
    ACCEPTED_EMOJI_ID,
    COLOR_BLURPLE,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,
)

@runtime_checkable
class _AppCommand(Protocol):
    name           : str
    qualified_name : str
    callback       : object
    commands       : list[object]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

P    = ParamSpec("P")
T_co = TypeVar("T_co", covariant = True)

class AccessNode:
    pass

@dataclass
class RoleNode(AccessNode):
    role_id : int

@dataclass
class UserNode(AccessNode):
    user_id : int

@dataclass
class AndNode(AccessNode):
    children : list[AccessNode]

@dataclass
class OrNode(AccessNode):
    children : list[AccessNode]

@dataclass
class NotNode(AccessNode):
    child: AccessNode

def evaluate_access(node : AccessNode, member : discord.Member) -> bool:
    member_role_ids = {r.id for r in member.roles}

    if isinstance(node, RoleNode):
        return node.role_id in member_role_ids
    if isinstance(node, UserNode):
        return node.user_id == member.id
    if isinstance(node, AndNode):
        return all(evaluate_access(c, member) for c in node.children)
    if isinstance(node, OrNode):
        return any(evaluate_access(c, member) for c in node.children)
    if isinstance(node, NotNode):
        return not evaluate_access(node.child, member)
    return False

def describe_access_node(node : AccessNode) -> str:
    if isinstance(node, RoleNode):
        return f"<@&{node.role_id}>"
    if isinstance(node, UserNode):
        return f"<@{node.user_id}>"
    if isinstance(node, AndNode):
        parts = [describe_access_node(c) for c in node.children]
        return " **AND** ".join(parts)
    if isinstance(node, OrNode):
        parts = [describe_access_node(c) for c in node.children]
        return " **OR** ".join(parts)
    if isinstance(node, NotNode):
        return f"**NOT** {describe_access_node(node.child)}"
    return "Unknown"

class ArgType(Enum):
    Integer       = "Integer"
    Text          = "Text Input"
    Attachment    = "Attachment"
    Boolean       = "Boolean"
    Number        = "Number"
    ChannelSelect = "Channel Select"
    RoleSelect    = "Role Select"
    MemberSelect  = "Member Select"
    UserSelect    = "User Select"
    StringSelect  = "String Select"

@dataclass
class ArgDependency:
    argument : str
    negate   : bool = False

@dataclass
class ArgumentInfo:
    arg_type          : ArgType
    arg_type_detail   : str        | None   = None
    description       : str                 = ""
    required          : bool                = True
    shown_as_optional : bool                = False
    default           : str        | None   = None
    empty_behavior    : str        | None   = None
    choices           : list[str]           = field(default_factory = list)
    is_flag           : bool                = False
    depends_on        : list[ArgDependency] = field(default_factory = list)
    access_node       : AccessNode | None   = None
    extra_notes       : list[str]           = field(default_factory = list)

@dataclass
class ChannelRestriction:
    node     : AccessNode
    channels : list[int]

@dataclass
class CommandHelpData:
    desc          : str
    prefix        : bool
    slash         : bool
    command_name  : str        | None        = None
    access_node   : AccessNode | None        = None
    channel_rules : list[ChannelRestriction] = field(default_factory = list)
    has_inverse   : bool       | str         = False
    arguments     : dict[str, ArgumentInfo]  = field(default_factory = dict)
    aliases       : list[str]                = field(default_factory = list)

@runtime_checkable
class HelpCallback(Protocol[P, T_co]):
    __help_data__ : CommandHelpData
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Coroutine[None, None, T_co]: ...

class HelpedCallable:
    __help_data__: CommandHelpData = cast("CommandHelpData", cast(object, None))

def help_description(
    desc          : str,
    *,
    command_name  : str                       | None = None,
    prefix        : bool                             = False,
    slash         : bool                             = True,
    access_node   : AccessNode                | None = None,
    channel_rules : list[ChannelRestriction]  | None = None,
    has_inverse   : bool                      | str  = False,
    arguments     : dict[str, ArgumentInfo]   | None = None,
    aliases       : list[str]                 | None = None,
) -> Callable[[Callable[P, Coroutine[None, None, T_co]]], Callable[P, Coroutine[None, None, T_co]]]:
    _channel_rules = channel_rules or []
    _arguments     = arguments     or {}
    _aliases       = aliases       or []

    def decorator(func : Callable[P, Coroutine[None, None, T_co]]) -> Callable[P, Coroutine[None, None, T_co]]:
        data = CommandHelpData(
            desc          = desc,
            prefix        = prefix,
            slash         = slash,
            command_name  = command_name,
            access_node   = access_node,
            channel_rules = _channel_rules,
            has_inverse   = has_inverse,
            arguments     = _arguments,
            aliases       = _aliases,
        )
        cast("HelpedCallable", func).__help_data__ = data
        return func

    return decorator

def check_access(
    member : discord.Member,
    data   : CommandHelpData,
) -> tuple[str, list[str], list[str], list[int]]:
    if data.access_node is None:
        accessible_args   : list[str] = []
        inaccessible_args : list[str] = []
        for arg_name, arg_info in data.arguments.items():
            if arg_info.access_node is None or evaluate_access(arg_info.access_node, member):
                accessible_args.append(arg_name)
            else:
                inaccessible_args.append(arg_name)

        if inaccessible_args:
            return "partial", accessible_args, inaccessible_args, []
        return "full", accessible_args, inaccessible_args, []

    has_access = evaluate_access(data.access_node, member)
    if not has_access:
        return "none", [], list(data.arguments.keys()), []

    accessible_args   = []
    inaccessible_args = []
    for arg_name, arg_info in data.arguments.items():
        if arg_info.access_node is None or evaluate_access(arg_info.access_node, member):
            accessible_args.append(arg_name)
        else:
            inaccessible_args.append(arg_name)

    allowed_channels: list[int] = []
    for rule in data.channel_rules:
        if evaluate_access(rule.node, member):
            allowed_channels = sorted(set(allowed_channels) | set(rule.channels))

    if inaccessible_args or allowed_channels:
        return "partial", accessible_args, inaccessible_args, allowed_channels
    return "full", accessible_args, inaccessible_args, allowed_channels

async def resolve_command_ref(bot: commands.Bot, data : CommandHelpData) -> str:
    name = data.command_name
    if name is None:
        return ""

    if not data.slash:
        return f"`{name}`"

    parts = name.strip().split()

    fetched = await bot.tree.fetch_commands()
    parent  = next((c for c in fetched if c.name == parts[0]), None)

    if parent is None:
        return f"`{name}`"

    if len(parts) == 1:
        return f"</{parts[0]}:{parent.id}>"

    tail = " ".join(parts[1:])
    return f"</{tail}:{parent.id}>"

_NOTICE_LOGICAL_OR = (
    "-# In the absence of advanced restrictions, multiple listings are governed by the **Logical OR** operator.\n"
)

def _format_arg_type(info : ArgumentInfo) -> str:
    if info.arg_type_detail is not None:
        return f"{info.arg_type.value} ({info.arg_type_detail})"
    return info.arg_type.value

def build_argument_line(name : str, info : ArgumentInfo) -> str:
    display_required = info.required and not info.shown_as_optional

    if info.choices:
        choices_str = "|".join(info.choices)
        inner       = f"{name}: {choices_str}"
        return f"{{{inner}}}" if display_required else f"[{inner}]"

    if info.is_flag:
        inner = f"/{name}: {{{name}}}"
        return inner if display_required else f"[{inner}]"

    return f"{{{name}}}" if display_required else f"[{name}]"

def _build_arg_block(name: str, info: ArgumentInfo) -> str:
    bracket = build_argument_line(name, info)
    lines : list[str] = [f"### {bracket.capitalize()}"]
    lines.append(f"-# **Type:** {_format_arg_type(info)}")

    if info.description:
        lines.append(info.description)

    if info.required:
        lines.append("- **Required**")

    if info.shown_as_optional:
        lines.append(
            "-# **Why is this argument shown as required if it's shown as optional?** The command is initialized this way to allow for mass moderation through leaving the argument empty. Internal command logic is shown in the arguments code block. External command logic is shown in the argument descriptions."
        )

    if info.empty_behavior is not None:
        lines.append(f"- **Empty argument:** {info.empty_behavior}")

    if info.default is not None:
        lines.append(f"- **Default:** {info.default}")

    for dep in info.depends_on:
        dep_bracket = f"**[{dep.argument}]**"
        if dep.negate:
            lines.append(f"- Usable only if the {dep_bracket} argument is **not** chosen.")
        else:
            lines.append(f"- Usable only if the {dep_bracket} argument is chosen.")

    if info.access_node is not None:
        lines.append(f"- Restricted to: {describe_access_node(info.access_node)}")

    for note in info.extra_notes:
        lines.append(note)

    return "\n".join(lines)

def _build_authority_section(data : CommandHelpData, member: discord.Member) -> tuple[str, int]:
    status, _, _, allowed_channels = check_access(member, data)

    if status == "full":
        colour = COLOR_GREEN
        text   = (
            f"## Authority\n"
            f"{ACCEPTED_EMOJI_ID} **Authorized.**\n"
             "You are authorized to to run this command.\n"
             "-# Full permissions."
        )

    elif status == "none":
        colour = COLOR_RED
        text   = (
             "## Authority\n"
            f"{DENIED_EMOJI_ID} **Unauthorized!**\n"
             "You are not authorized to run this command.\n"
             "-# No permissions."
        )

    else:
        colour         = COLOR_YELLOW
        channel_detail = ""
        if allowed_channels:
            channels_str   = " ".join(f"<#{cid}>" for cid in allowed_channels)
            channel_detail = f"\nYou may only use this command in: {channels_str}"

        text = (
            "## Authority\n"
            f"{CONTESTED_EMOJI_ID} **Partially Authorized.**\n"
            "You are authorized to run this command, but not all of its arguments or channels are available to you."
            f"{channel_detail}\n"
            "-# Partial permissions."
        )

    return text, int(colour)

def _collect_role_nodes(node : AccessNode) -> list[RoleNode]:
    if isinstance(node, RoleNode):
        return [node]
    if isinstance(node, OrNode | AndNode):
        result : list[RoleNode] = []
        for child in node.children:
            result.extend(_collect_role_nodes(child))
        return result
    return []

def _collect_user_nodes(node : AccessNode) -> list[UserNode]:
    if isinstance(node, UserNode):
        return [node]
    if isinstance(node, OrNode | AndNode):
        result : list[UserNode] = []
        for child in node.children:
            result.extend(_collect_user_nodes(child))
        return result
    return []

def _build_authorized_section(data : CommandHelpData) -> str:
    lines : list[str] = ["## Authorized"]

    user_nodes : list[UserNode] = (
        _collect_user_nodes(data.access_node) if data.access_node is not None else []
    )
    role_nodes : list[RoleNode] = (
        _collect_role_nodes(data.access_node) if data.access_node is not None else []
    )

    lines.append("### Users")
    if user_nodes:
        for un in user_nodes:
            lines.append(f"<@{un.user_id}>")
        lines.append(_NOTICE_LOGICAL_OR)
    else:
        lines.append("Not applicable.")
        lines.append(_NOTICE_LOGICAL_OR.strip())

    lines.append("### Roles")
    if role_nodes:
        for rn in role_nodes:
            lines.append(f"<@&{rn.role_id}>")
        if len(role_nodes) > 1:
            op = "AND" if isinstance(data.access_node, AndNode) else "OR"
            lines.append(f"-# Multiple roles are governed by the **Logical {op}** operator.")
        else:
            lines.append(_NOTICE_LOGICAL_OR)
    else:
        lines.append(f"Not applicable.")
        lines.append(_NOTICE_LOGICAL_OR.strip())

    lines.append("### Advanced Restrictions")
    if data.channel_rules:
        for rule in data.channel_rules:
            channels_str = " ".join(f"<#{cid}>" for cid in rule.channels)
            lines.append(f"- {describe_access_node(rule.node)} → {channels_str}")
        lines.append(
            "-# **What are advanced restrictions?** Advanced Restrictions provide a logic specification detailing how command behavior behaves across different contexts. This framework is intended to explain the interdependent relationships between users, roles, and environments (such as specific channels) when working with arguments, sub-arguments, and nested-arguments when they may be accessible or restricted depending on a user's unique permission profile."
        )
    else:
        lines.append("Not applicable.")
        lines.append("-# **What are advanced restrictions?** Advanced Restrictions provide a logic specification detailing how command behavior behaves across different contexts. This framework is intended to explain the interdependent relationships between users, roles, and environments (such as specific channels) when working with arguments, sub-arguments, and nested-arguments when they may be accessible or restricted depending on a user's unique permission profile.")

    return "\n".join(lines)

def _build_arguments_section(command_name: str, data : CommandHelpData) -> str:
    arg_tokens  = " ".join(build_argument_line(n, i) for n, i in data.arguments.items())
    usage_lines : list[str] = []
    if data.prefix:
        usage_lines.append(f".{command_name} {arg_tokens}".strip())
    if data.slash:
        usage_lines.append(f"/{command_name} {arg_tokens}".strip())
    usage_block = "\n".join(usage_lines)

    arg_blocks = "\n".join(_build_arg_block(n, i) for n, i in data.arguments.items())

    return (
        f"## Arguments\n"
        f"```\n"
        f"{usage_block}\n"
        f"```\n"
         "{...} denotes a required argument.\n"
         "[...] denotes an optional argument.\n"
        f"{arg_blocks}"
    )

def build_help_view(
    command_name : str,
    data         : CommandHelpData,
    member       : discord.Member,
    command_ref  : str,
) -> LayoutView:
    display_name = command_ref or f"`/{command_name}`"

    prefix_emoji = ACCEPTED_EMOJI_ID if data.prefix else DENIED_EMOJI_ID
    slash_emoji  = ACCEPTED_EMOJI_ID if data.slash  else DENIED_EMOJI_ID

    aliases_line = ""
    if data.aliases:
        formatted    = ", ".join(f"`{a}`" for a in data.aliases)
        aliases_line = f"\n**Aliases:** {formatted}"

    inverse_line = ""
    if data.has_inverse and isinstance(data.has_inverse, str):
        inverse_line = f"\nThis command has an inverse, **{data.has_inverse}**."

    header_text = (
        f"# {display_name} Command\n"
         "## Description\n"
        f"{data.desc}\n"
         "## Variants\n"
        f"- {prefix_emoji} **Prefix**\n"
        f"- {slash_emoji} **Application**"
        f"{aliases_line}"
        f"{inverse_line}"
    )

    authority_text, _ = _build_authority_section(data, member)
    authorized_text   = _build_authorized_section(data)
    arguments_text    = _build_arguments_section(command_name, data)

    spacing : SeparatorSpacing = discord.SeparatorSpacing.large

    _header_td     : TextDisplay[LayoutView] = TextDisplay(content = header_text)
    _sep_1         : Separator[LayoutView]   = Separator(spacing = spacing)
    _authority_td  : TextDisplay[LayoutView] = TextDisplay(content = authority_text)
    _sep_2         : Separator[LayoutView]   = Separator(spacing = spacing)
    _authorized_td : TextDisplay[LayoutView] = TextDisplay(content = authorized_text)
    _sep_3         : Separator[LayoutView]   = Separator(spacing = spacing)
    _arguments_td  : TextDisplay[LayoutView] = TextDisplay(content = arguments_text)

    class HelpView(LayoutView):
        container : Container[LayoutView] = Container(
            _header_td,
            _sep_1,
            _authority_td,
            _sep_2,
            _authorized_td,
            _sep_3,
            _arguments_td,
        )

    return HelpView()

def member_has_role(member : discord.Member, role_id : int) -> bool:
    return any(r.id == role_id for r in member.roles)

def resolve_command(bot : commands.Bot, name : str) -> Callable[..., Awaitable[object]] | None:
    cmd = bot.get_command(name)
    if cmd:
        return cmd.callback

    for app_cmd in bot.tree.get_commands():
        if app_cmd.name == name:
            return getattr(app_cmd, "callback", None)

    return None

def find_nested_command(bot : commands.Bot, parts : list[str]) -> object | None:
    full   = " ".join(parts)
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

def collect_slash_commands(
    app_commands_list : Sequence[_AppCommand],
    seen_callbacks    : set[int],
    lines             : list[str],
) -> None:
    for app_cmd in app_commands_list:
        cb = app_cmd.callback
        if hasattr(cb, "__help_data__") and id(cb) not in seen_callbacks:
            seen_callbacks.add(id(cb))
            qualified = app_cmd.qualified_name or app_cmd.name
            lines.append(f"`/{qualified}` — {cast('HelpedCallable', cb).__help_data__.desc}")

        sub_commands = app_cmd.commands
        if sub_commands:
            collect_slash_commands(
                [c for c in sub_commands if isinstance(c, _AppCommand)],
                seen_callbacks,
                lines,
            )

async def run_help(
    bot          : commands.Bot,
    ctx_or_inter : commands.Context[commands.Bot] | discord.Interaction,
    command_name : str                            | None,
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
        seen_callbacks : set[int] = set()
        lines          : list[str] = []

        for cmd in bot.commands:
            cb = cast("HelpedCallable", cmd.callback)
            if hasattr(cb, "__help_data__"):
                seen_callbacks.add(id(cb))
                lines.append(f"`{cmd.name}` — {cb.__help_data__.desc}")

        app_cmds = [c for c in bot.tree.get_commands() if isinstance(c, _AppCommand)]
        collect_slash_commands(app_cmds, seen_callbacks, lines)

        if lines:
            _ = await respond(
                embed = discord.Embed(
                    title       = "Available Commands",
                    description = "\n".join(lines),
                    color       = COLOR_BLURPLE,
                ),
                allowed_mentions = discord.AllowedMentions.none(),
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

    data        = cast("HelpedCallable", callback).__help_data__
    command_ref = await resolve_command_ref(bot, data)

    view = build_help_view(
        command_name = " ".join(parts),
        data         = data,
        member       = member,
        command_ref  = command_ref,
    )
    _ = await respond(view = view)