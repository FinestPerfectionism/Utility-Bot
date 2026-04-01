import discord
from discord import app_commands
from discord.ext import commands

from constants import (
    BOT_OWNER_ID,
    HOLY_FATHER_ID,
)
from core.help import (
    help_description,
)
from core.utils import send_minor_error


class Ping(discord.ui.LayoutView):
    def __init__(self, ping: int) -> None:
        super().__init__()

        _ = self.add_item(
            discord.ui.TextDisplay(content = "# I HAVE BEEN AWAKENEDDDD."),
        )
        _ = self.add_item(
            discord.ui.Separator(
                visible = True,
                spacing = discord.SeparatorSpacing.small,
            ),
        )
        _ = self.add_item(
            discord.ui.TextDisplay(
                content = f"*cough cough* My ping is {ping} milliseconds.",
            ),
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Miscellaneous Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MiscCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        _ = self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /femboy Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name = "femboy",
        description="Such a good little utility kitten.",
    )
    @help_description(
        desc="Sends the bot's intentionally unserious self-introduction message. This is a flavor command with no arguments or permissions beyond being able to invoke the slash command.",
        prefix=False,
        slash=True,
    )
    async def femboy(self, interaction: discord.Interaction) -> None:
        _ = await interaction.response.defer()
        await interaction.followup.send(
            "i-i'm such a submissive wittle kitty UwU. *snuggles* I hewp cwose proposals... naa~~",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .super_secret_command Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name = "super_secret_command",
    )
    @help_description(
        desc="Runs a private easter-egg response path intended for the configured bot owner and a small hard-coded exception. Access is controlled by user ID checks inside the command, not by Discord roles.",
        prefix=True,
        slash=False,
    )
    async def super_secret_command(self, ctx: commands.Context[commands.Bot]) -> None:
        author_id = ctx.author.id

        if author_id == BOT_OWNER_ID:
            _ = await ctx.send(
                "This is a super super secret command that is used by people that will use it super super secretly.",
            )
            return

        if author_id == HOLY_FATHER_ID:
            _ = await ctx.send(
                "Hello daddy! <:puppy3:1464256700344303771> This is a super super secret command that is used by people that will use it super super secretly.",
            )
            return

        _ = await ctx.send(
            "Hmm… I don't think you're super super secret enough to use this super super secret command.",
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /roulette Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @app_commands.command(
        name = "roulette",
        description="Have fun...",
    )
    @help_description(
        desc="Plays a deliberately risky roulette gag. Depending on the random chamber result and the bot's permissions, the command may attempt to ban the invoking user or simply report that the shot misfired.",
        prefix=False,
        slash=True,
    )
    async def roulette(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        member = interaction.user

        if guild is None:
            await send_minor_error(
                interaction,
                "This command can only be used in a server.",
                subtitle = "Bad command environment.",
            )
            return

        CHEESE = 1167207694424350740
        if interaction.user.id == CHEESE:
            _ = await interaction.response.send_message(
                "My developer is so fucking tired of unbanning you and adding your roles back that he has decided that you can never touch this command again. Dumbass. <:laugh5:1481288430150484111>",
            )
            return

        _ = await interaction.response.defer(ephemeral=False)

        import secrets

        chamber = secrets.randbelow(6) + 1

        if chamber == 1:
            try:
                await guild.ban(
                    member,
                    reason="Played a stupid game, won a stupid prize.",
                    delete_message_seconds=0,
                )
                await interaction.followup.send(
                    "<a:CatShoot:1466460098955313294> *Click,* ***BAM***.",
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "*Click,* ***Ba***… wait… the gun's jammed!",
                )
        else:
            await interaction.followup.send(
                "*Click.* You live.",
            )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # .ping Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(
        name = "bot-ping",
    )
    @help_description(
        desc        = "The ping command displays the bot's current latency in milliseconds.",
        prefix      = True,
        slash       = False,
        has_inverse = False,
    )
    async def ping(self, ctx: commands.Context[commands.Bot]) -> None:
        latency_ms = round(self.bot.latency * 1000)
        _ = await ctx.send(
            view = Ping(latency_ms),
        )

async def setup(bot: commands.Bot) -> None:
    cog = MiscCommands(bot)
    await bot.add_cog(cog)
