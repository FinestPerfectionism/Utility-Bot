import discord
from discord.ext import commands

from typing import Optional, cast, Union

from core.help import HelpedCallable, _find_nested_command, _build_help_view

from constants import(
    COLOR_BLURPLE
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Help Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

async def _run_help(
  bot: commands.Bot,
  ctx_or_inter: Union[commands.Context, discord.Interaction],
  command_name: Optional[str],
):
  if isinstance(ctx_or_inter, commands.Context):
    if not isinstance(ctx_or_inter.author, discord.Member):
        await ctx_or_inter.send(
            "Cannot resolve guild member context.",
        )
        return

    member = ctx_or_inter.author
    respond = ctx_or_inter.send
  else:
      if not isinstance(ctx_or_inter.user, discord.Member):
          await ctx_or_inter.response.send_message(
              "Cannot resolve guild member context.",
              ephemeral=True,
          )
          return
      member = ctx_or_inter.user
      respond = ctx_or_inter.response.send_message

  if not command_name:
      lines = []
      for cmd in bot.commands:
          cb = cast(HelpedCallable, cmd.callback)
          if hasattr(cb, "__help_data__"):
              lines.append(f"`{cmd.name}` — {cb.__help_data__.desc}")

      for app_cmd in bot.tree.get_commands():
          cb = cast(HelpedCallable, getattr(app_cmd, "callback", None))
          if cb and hasattr(cb, "__help_data__"):
              lines.append(f"`/{app_cmd.name}` — {cb.__help_data__.desc}")

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

  parts = command_name.strip().lstrip("/").split()
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

class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # ~help Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context, *, command_name: Optional[str] = None):
        await _run_help(self.bot, ctx, command_name)

async def setup(bot: commands.Bot):
  cog = HelpCommands(bot)
  await bot.add_cog(cog)