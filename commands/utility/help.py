import discord
from discord.ext import commands
from typing import cast
from core.help import (
    HelpedCallable,
    find_nested_command,
    build_help_view,
)
from constants import (
    COLOR_BLURPLE,
    BOT_OWNER_ID,
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

_BOT_INFO_TEXT = (
    f"# Bot Information\n"
    f"Various moderative, administrative, and directive utilities for the staff team. "
    f"This bot is unusable outside of The Goobers guild. Do __not__ expect to receive support with usage.\n"
    f"## Modules\n"
    f"- **Moderation** — Warnings, mutes, bans, and other punitive actions.\n"
    f"- **Utility** — General-purpose staff tools.\n"
    f"- **Proposal Manager** — Create and manage proposals.\n"
    f"- **Applications & Tickets Manager** — Handle applications and support tickets.\n"
    f"- **Verification Manager** — Manage member verification.\n"
    f"## Developer\n"
    f"<:developer:1480043201581551676> My developer is this bitch: <@{BOT_OWNER_ID}>\n"
    f"## Usage\n"
    f"Run `.help <cmd>` for detailed information on a specific command."
)

_NO_PING = discord.AllowedMentions(users=False)


def _build_info_view() -> discord.ui.LayoutView:
    class InfoView(discord.ui.LayoutView):
        container = discord.ui.Container( # type: ignore
            discord.ui.TextDisplay(content=_BOT_INFO_TEXT), # type: ignore
            accent_color=COLOR_BLURPLE,
        )
    return InfoView()


async def _run_help(
    bot:          commands.Bot,
    ctx_or_inter: commands.Context[commands.Bot] | discord.Interaction,
    command_name: str | None,
) -> None:
    if isinstance(ctx_or_inter, commands.Context):
        if not isinstance(ctx_or_inter.author, discord.Member):
            await ctx_or_inter.send(
                "Cannot resolve guild member context.",
            )
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
        await respond(view=_build_info_view(), allowed_mentions=_NO_PING)
        return

    parts    = command_name.strip().lstrip("/").split()
    callback = find_nested_command(bot, parts)

    if callback is None or not hasattr(callback, "__help_data__"):
        await respond(
            f"Command `{command_name}` not found or has no help data.",
            ephemeral=True,
        )
        return

    data = cast("HelpedCallable", callback).__help_data__
    view = build_help_view(
        command_name=" ".join(parts),
        data=data,
        member=member,
    )
    await respond(view=view)


class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .help Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="help")
    async def help(
        self,
        ctx: commands.Context[commands.Bot],
        *,
        command_name: str | None = None,
    ) -> None:
        if not command_name:
            return await _run_help(self.bot, ctx, None)

        query = command_name.lower().strip()

        snarky_responses = {
            "<cmd>": "Brocacho... you're supposed to replace `<cmd>` with the command you want help with.\n"
                     "-# Genuinely wondering how one makes it this far without realizing something as simple as this. 🥀",
            "super_secret_command": "There is no super secret command in ba sing se.",
            "help": "Help²",
            "me": "No. <:laugh5:1481288430150484111>"
        }

        if query in snarky_responses:
            await ctx.send(snarky_responses[query])
            return None

        return await _run_help(self.bot, ctx, command_name)

async def setup(bot: commands.Bot) -> None:
    cog = HelpCommands(bot)
    await bot.add_cog(cog)