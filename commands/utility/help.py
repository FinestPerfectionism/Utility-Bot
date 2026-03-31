from typing import cast

import discord
from discord.ext import commands

from constants import (
    BOT_OWNER_ID,
    COLOR_BLURPLE,
    CONTESTED_EMOJI_ID,
)
from core.help import (
    HelpedCallable,
    build_help_view,
    find_nested_command,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_BOT_INFO_TEXT = (
     "# Bot Information\n"
     "Various moderative, administrative, and directive utilities for the staff team. "
     "This bot is unusable outside of The Goobers guild. Do __not__ expect to receive support with usage.\n"
     "## Modules\n"
     "- **Moderation** — Warnings, mutes, bans, and other punitive actions.\n"
     "- **Utility** — General-purpose staff tools.\n"
     "- **Proposal Manager** — Create and manage proposals.\n"
     "- **Applications & Tickets Manager** — Handle applications and support tickets.\n"
     "- **Verification Manager** — Manage member verification.\n"
     "## Developer\n"
    f"<:developer:1480043201581551676> My developer is this bitch: <@{BOT_OWNER_ID}>\n"
     "## Usage\n"
     "Run `.help <cmd>` for detailed information on a specific command."
)

_NO_PING = discord.AllowedMentions(users=False)


def _build_info_view() -> discord.ui.LayoutView:
    class InfoView(discord.ui.LayoutView):
        container = discord.ui.Container( # type: ignore
            discord.ui.TextDisplay(content=_BOT_INFO_TEXT), # type: ignore
            accent_color = COLOR_BLURPLE,
        )
    return InfoView()


async def _run_help(
    bot:          commands.Bot,
    ctx_or_inter: commands.Context[commands.Bot] | discord.Interaction,
    command_name: str                            | None,
) -> None:
    if isinstance(ctx_or_inter, commands.Context):
        if not isinstance(ctx_or_inter.author, discord.Member):
            _ = await ctx_or_inter.send(
               f"{CONTESTED_EMOJI_ID} **Failed to parse help data!**\n"
                "Cannot resolve guild member context.",
            )
            return
        member  = ctx_or_inter.author
        respond = ctx_or_inter.send
    else:
        if not isinstance(ctx_or_inter.user, discord.Member):
            _ = await ctx_or_inter.response.send_message(
               f"{CONTESTED_EMOJI_ID} **Failed to parse help data!**\n"
                "Cannot resolve guild member context.",
                ephemeral = True,
            )
            return
        member  = ctx_or_inter.user
        respond = ctx_or_inter.response.send_message

    if not command_name:
        _ = await respond(view = _build_info_view(), allowed_mentions=_NO_PING)
        return

    parts    = command_name.strip().lstrip("/").split()
    callback = find_nested_command(bot, parts)

    if callback is None or not hasattr(callback, "__help_data__"):
        _ = await respond(
            f"{CONTESTED_EMOJI_ID} Failed to parse help data!"
            f"Command `{command_name}` not found or has no help data.",
        )
        return

    data = cast("HelpedCallable", callback).__help_data__
    view = build_help_view(
        command_name = " ".join(parts),
        data=data,
        member=member,
    )
    _ = await respond(view = view)


class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .help Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "help")
    async def help(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        command_name: str | None = None,
    ) -> None:
        if not command_name:
            return await _run_help(self.bot, ctx, None)

        query = command_name.lower().strip()

        responses = {
            "<cmd>": "Brocacho... you're supposed to replace `<cmd>` with the command you want help with.\n"
                     "-# Genuinely wondering how one makes it this far without realizing something as simple as this. 🥀",
            "super_secret_command": "There is no super secret command in ba sing se.",
            "help": "Help²",
            "me": "No. <:laugh5:1481288430150484111>",
        }

        if query in responses:
            _ = await ctx.send(responses[query])
            return None

        return await _run_help(self.bot, ctx, command_name)

async def setup(bot: commands.Bot) -> None:
    cog = HelpCommands(bot)
    await bot.add_cog(cog)
