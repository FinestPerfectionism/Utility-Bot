import discord
from discord.ext import commands
from discord import app_commands

from constants import (
    COLOR_BLURPLE,

    BOT_LOG_CHANNEL_ID
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Command Handling
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class CommandLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Application Command Handling
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        command: app_commands.Command,
    ):
        channel = self.bot.get_channel(BOT_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title="Application Command Executed",
            color=COLOR_BLURPLE,
            timestamp=interaction.created_at,
        )

        embed.add_field(
            name="User",
            value=f"`{interaction.user}`\n`{interaction.user.id}`",
            inline=True,
        )

        if interaction.guild:
            embed.add_field(
                name="Guild",
                value=f"`{interaction.guild}`\n`{interaction.guild.id}`",
                inline=True,
            )

        cmd = interaction.command
        cmd_name = f"/{cmd.qualified_name}" if cmd else "Unknown"

        embed.add_field(
            name="Command",
            value=f"`{cmd_name}`",
            inline=True,
        )

        display_channel = "DM"

        if interaction.guild and interaction.channel:
            if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
                display_channel = interaction.channel.mention
            else:
                display_channel = str(interaction.channel)

        embed.add_field(
            name="Channel",
            value=display_channel,
            inline=False,
        )

        await channel.send(embed=embed)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Prefix Command Handling
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        channel = self.bot.get_channel(BOT_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title="Prefix Command Executed",
            color=COLOR_BLURPLE,
            timestamp=ctx.message.created_at,
        )

        embed.add_field(
            name="User",
            value=f"`{ctx.author}`\n`{ctx.author.id}`",
            inline=True,
        )

        if ctx.guild:
            embed.add_field(
                name="Guild",
                value=f"`{ctx.guild}`\n`{ctx.guild.id}`",
                inline=True,
            )

        embed.add_field(
            name="Command",
            value=f"`.{ctx.command.qualified_name if ctx.command else 'Unknown'}`",
            inline=True,
        )

        embed.add_field(
            name="Channel",
            value=(
                ctx.channel.mention
                if isinstance(ctx.channel, (discord.TextChannel, discord.Thread))
                else "DM"
            ),
            inline=False,
        )

        await channel.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(CommandLogger(bot))