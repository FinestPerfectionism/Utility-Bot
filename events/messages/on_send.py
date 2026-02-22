import discord
from discord.ext import commands

from datetime import timedelta
import random
import logging

from core.state import (
    AUTOMOD_DELETIONS,
    AUTOMOD_STRIKES,
    save_automod_strikes,
    ACTIVE_APPLICATIONS,
    save_active_applications,
)

from events.systems.applications import ApplicationSubmitView

from constants import (
    COLOR_BLURPLE,

    DIRECTOR_TASKS_CHANNEL_ID,

    DIRECTORS_ROLE_ID
)

MAX_STRIKES = 5
TIMEOUT_DURATION = timedelta(days=3)
WINDOW = timedelta(days=7)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Sending
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MessageSendHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if isinstance(message.channel, discord.Thread):
            thread = message.channel

            if (
                isinstance(thread.parent, discord.ForumChannel)
                and thread.parent_id == DIRECTOR_TASKS_CHANNEL_ID
                and message.id == thread.id
            ):
                await thread.send(
                    content=f"<@&{DIRECTORS_ROLE_ID}>",
                    allowed_mentions=discord.AllowedMentions(roles=True),
                )

        if (
            "https://tenor.com/view/dog-funny-video-funny-funny-dog-dog-peeing-gif-4718562751207105873"
            in (message.content or "").lower()
        ):
            try:
                AUTOMOD_DELETIONS.add(message.id)
                await message.delete()

                now = discord.utils.utcnow()
                strikes = AUTOMOD_STRIKES[message.author.id]
                strikes.append(now)
                strikes[:] = [t for t in strikes if now - t <= WINDOW]

                save_automod_strikes()

                warning = await message.channel.send(
                    f"{message.author.mention} Hey dude, can you like *not* send that GIF? "
                    "You're really not that funny."
                )
                await warning.delete(delay=15)

                save_automod_strikes()

                if len(strikes) >= MAX_STRIKES:
                    member = message.author
                    if isinstance(member, discord.Member):
                        await member.timeout(
                            TIMEOUT_DURATION,
                            reason="UB Auto-Moderation: night night",
                        )
                        await message.channel.send(
                            f"{message.author.mention} Alright bro, I've given you *five fucking warnings* "
                            "and you still haven't learned. Is a dog pissing on the floor that funny to you? "
                            "Regardless, sleep tight bitch."
                        )
                        AUTOMOD_STRIKES.pop(message.author.id, None)
                        save_automod_strikes()

            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            except Exception as e:
                logging.getLogger("Utility Bot").exception(
                    "Automod failure while processing message", exc_info=e
                )
            return

        if (
            "clanker"
            in (message.content or "").lower()
        ):
            grimace_emojis = ['<:grimace2:1469070596632608779>', '<:grimace3:1469070653624684820>']
            await message.reply(
                "stfu you meatbag 🥀 omfg icl ts pmo gng smh frfr <:exhausted:1467990265452167362>"
            )
            await message.add_reaction(
                random.choice(grimace_emojis)
            )

        if message.guild is None:
            app = ACTIVE_APPLICATIONS.get(message.author.id)
            if app:
                if app.get("reviewing"):
                    return

                if app.get("editing"):
                    if app["index"] < len(app["answers"]):
                        app["answers"][app["index"]] = message.content
                    else:
                        app["answers"].append(message.content)

                    app["editing"] = False
                    app["reviewing"] = True
                    save_active_applications()

                    embed = discord.Embed(
                        title="Review Your Application",
                        color=COLOR_BLURPLE,
                    )

                    for i, (q, a) in enumerate(
                        zip(app["questions"], app["answers"]), start=1
                    ):
                        embed.add_field(
                            name=f"{i}. {q}",
                            value=a[:1021] + "..." if len(a) > 1024 else (a or "*No response provided.*"),
                            inline=False,
                        )

                    msg = await message.channel.send(
                        embed=embed,
                        view=ApplicationSubmitView(message.author.id),
                    )

                    app["review_message_id"] = msg.id
                    app["messages"].append(msg.id)
                    save_active_applications()
                    return

                app["answers"].append(message.content)
                app["index"] += 1
                save_active_applications()

                if app["index"] >= len(app["questions"]):
                    app["reviewing"] = True
                    save_active_applications()

                    embed = discord.Embed(
                        title="Review Your Application",
                        color=COLOR_BLURPLE,
                    )

                    for i, (q, a) in enumerate(
                        zip(app["questions"], app["answers"]), start=1
                    ):
                        embed.add_field(
                            name=f"{i}. {q}",
                            value=a[:1021] + "..." if len(a) > 1024 else (a or "*No response provided.*"),
                            inline=False,
                        )

                    msg = await message.channel.send(
                        embed=embed,
                        view=ApplicationSubmitView(message.author.id),
                    )

                    app["review_message_id"] = msg.id
                    app["messages"].append(msg.id)
                    save_active_applications()
                    return

                msg = await message.channel.send(app["questions"][app["index"]])
                app["messages"].append(msg.id)
                save_active_applications()
                return

async def setup(bot: commands.Bot):
    await bot.add_cog(MessageSendHandler(bot))