import discord
from discord.ext import commands
from discord.ui import (
    Container,
    LayoutView,
    TextDisplay,
)

from constants import BOT_OWNER_ID, COLOR_BLURPLE
from core.help import run_help

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

BOT_INFO_TEXT = (
     "# Bot Information\n"
     "Various moderative, administrative, and directive utilities for the staff team. "
     "This bot is unusable outside of The Goobers guild. Do __not__ expect to receive support with usage.\n"
     "## Modules\n"
     "- **Moderation** — Warnings, mutes, bans, and other punitive actions.\n"
     "- **Utility** — General-purpose staff tools.\n"
     "- **Proposal Manager** — Create and manage proposals.\n"
     "- **Applications & Tickets Manager** — Handle applications and support tickets.\n"
     "## Developer\n"
    f"<:developer:1480043201581551676> My developer is this bitch: <@{BOT_OWNER_ID}>\n"
     "## Usage\n"
     "Run `.help <cmd>` for detailed information on a specific command."
)

def _build_info_view() -> LayoutView:
    class InfoView(LayoutView):
        container : Container[LayoutView] = Container(
            TextDisplay(content = BOT_INFO_TEXT),
            accent_color = COLOR_BLURPLE,
        )
    return InfoView()


class HelpCommands(commands.Cog):
    bot : commands.Bot
    def __init__(self, bot : commands.Bot) -> None:
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .help Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name = "help")
    async def help(
        self,
        ctx          : commands.Context[commands.Bot],
        *,
        command_name : str | None = None,
    ) -> None:
        if not command_name:
            _ = await ctx.send(view = _build_info_view(), allowed_mentions = discord.AllowedMentions.none())
            return

        query = command_name.lower().strip()

        special_responses : dict[str, str] = {
            "<cmd>"                : (
                "Brocacho... you're supposed to replace `<cmd>` with the command you want help with.\n"
                "-# Genuinely wondering how one makes it this far without realizing something as simple as this. 🥀"
            ),
            "super_secret_command" : "There is no super secret command in ba sing se.",
            "help"                 : "Help²",
            "me"                   : "No. <:laugh5:1481288430150484111>",
        }

        if query in special_responses:
            _ = await ctx.send(special_responses[query])
            return

        await run_help(self.bot, ctx, command_name)


async def setup(bot : commands.Bot) -> None:
    cog = HelpCommands(bot)
    await bot.add_cog(cog)
