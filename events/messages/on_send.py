# ruff: noqa: RUF001

import contextlib
import json
import logging as log
import math
import re
import secrets
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any, TypedDict, cast

import discord
from discord.ext import commands

from constants import (
    ACCEPTED_EMOJI_ID,
    COLOR_BLURPLE,
    COUNTING_CHANNEL_ID,
    COUNTING_FAILED_ROLE_ID,
    DENIED_EMOJI_ID,
    DIRECTOR_TASKS_CHANNEL_ID,
    DIRECTORS_ROLE_ID,
    HOLY_FATHER_ID,
    STAFF_COMMITTEE_ROLE_ID,
    STAFF_PROPOSALS_CHANNEL_ID,
    STAFF_PROPOSALS_REVIEW_CHANNEL_ID,
    WAPPLE_CHAIN_CHANNEL_ID,
)
from core.state.application_state import ACTIVE_APPLICATIONS, save_active_applications
from core.state.automod_state import AUTOMOD_DELETIONS, AUTOMOD_STRIKES, save_automod_strikes
from events.systems.applications import ApplicationSubmitView

MAX_STRIKES = 5
TIMEOUT_DURATION = timedelta(days=3)
WINDOW = timedelta(days=7)

WAPPLE_EMOJIS = [
    "<:Wapple:1474915842071335098>",
    "<:WappleYellow:1474916545158189108>",
    "<:WappleGreen:1474916731532087569>",
    "<:WappleBlue:1474916471984623842>",
    "<:WappleHartwellWhite:1474916613232001117>",
    "<:applebruh:1478244953892192357>",
    "<:ex:1476672300467093626>",
    "<:susapple:1483533565005402144>",
]

FACTOIDS = {
    "bump"   : (
        "# Please bump __both__ bots.\n"
        "We really appreciate everyone bumping! If you are going to bump, please bump **both** <@735147814878969968> and <@1159147139960676422>.\n"
        "### Why?\n"
        "The bots have a cooldown of one bump per 2 hours. We try to sync the timer on each. Bumping both at once ensures that this happens."
    ),
    "oleave" : (
        "..."
    ),
    "pleave" : (
        "..."
    ),
    "staff"   : (
        "# What does Staff* and Staff mean?\n"
        "Staff* refers to Moderators, Administrators, and Directors, but does not consider the staff role.\n"
        "Staff refers to the Staff Role, which includes Moderators, Administrators, Directors, and the Staff Committee.\n"
        "### Why?\n"
        "Members who choose to partner with us gain the staff role, but are not considered staff in the same way as Moderators, Administrators, Directors, or the Staff Committee. Staff* is referenced in the help command."
    ),
}

WAPPLE_PATTERN = re.compile(rf"^({'|'.join(map(re.escape, WAPPLE_EMOJIS))}| )+$")

COUNTING_STATE_PATH = Path("data/counting_state.json")

_SUPER = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUB   = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")

_FONT_MAP = {
    "𝟎":"0","𝟏":"1","𝟐":"2","𝟑":"3","𝟒":"4","𝟓":"5","𝟔":"6","𝟕":"7","𝟖":"8","𝟗":"9",
    "𝟘":"0","𝟙":"1","𝟚":"2","𝟛":"3","𝟜":"4","𝟝":"5","𝟞":"6","𝟟":"7","𝟠":"8","𝟡":"9",
    "𝟢":"0","𝟣":"1","𝟤":"2","𝟥":"3","𝟦":"4","𝟧":"5","𝟨":"6","𝟩":"7","𝟪":"8","𝟫":"9",
    "𝟬":"0","𝟭":"1","𝟮":"2","𝟯":"3","𝟰":"4","𝟱":"5","𝟲":"6","𝟳":"7","𝟴":"8","𝟵":"9",
    "𝟶":"0","𝟷":"1","𝟸":"2","𝟹":"3","𝟺":"4","𝟻":"5","𝟼":"6","𝟽":"7","𝟾":"8","𝟿":"9",
    "𝜋":"pi","𝝅":"pi","𝞹":"pi",
    "𝜏":"tau","𝝉":"tau","𝞽":"tau",
    "𝑒":"e",
}

_FONT_PATTERN = re.compile("|".join(re.escape(k) for k in _FONT_MAP))

def _normalize_fonts(expr: str) -> str:
    return _FONT_PATTERN.sub(lambda m: _FONT_MAP[m.group(0)], expr)

_SUBSTITUTIONS: list[tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]] = [
    (re.compile(r"log([₀₁₂₃₄₅₆₇⁸₉]+)\s*\(([^)]+)\)"),
     lambda m: f"math.log({m.group(2)},{m.group(1).translate(_SUB)})"),
    (re.compile(r"(\S+?)\s*([⁰¹²³⁴⁵⁶⁷⁸⁹]+)"),
     lambda m: m.group(1) + "**" + m.group(2).translate(_SUPER)),
    (re.compile(r"(\d+(?:\.\d+)?|\([^)]+\))\s*!"),
     lambda m: f"math.factorial({m.group(1)})"),
    (re.compile(r"⌊([^⌋]+)⌋"),  lambda m: f"math.floor({m.group(1)})"),
    (re.compile(r"⌈([^⌉]+)⌉"),  lambda m: f"math.ceil({m.group(1)})"),
    (re.compile(r"\^"),          "**"),
    (re.compile(r"(\d)\s*\("),   r"\1*("),
    (re.compile(r"\)\s*\("),     r")*("),
    (re.compile(r"√\s*\(([^)]+)\)"), r"math.sqrt(\1)"),
    (re.compile(r"√\s*(\d+(?:\.\d+)?)"), r"math.sqrt(\1)"),
    (re.compile(r"\bpi\b|π"),     "math.pi"),
    (re.compile(r"\btau\b|τ"),    "math.tau"),
    (re.compile(r"\barcsin\b"),  "math.asin"),
    (re.compile(r"\barccos\b"),  "math.acos"),
    (re.compile(r"\barctan\b"),  "math.atan"),
    (re.compile(r"÷"),           "/"),
    (re.compile(r"×"),           "*"),
]

_SAFE_GLOBALS: dict[str, Any] = {
    "__builtins__" : {},
    "math"         : math,
    "abs"          : abs,
    "round"        : round,
    "int"          : int,
    "float"        : float,
    "sqrt"         : math.sqrt,
    "log"          : math.log,
    "log2"         : math.log2,
    "log10"        : math.log10,
    "exp"          : math.exp,
    "sin"          : math.sin,
    "cos"          : math.cos,
    "tan"          : math.tan,
    "asin"         : math.asin,
    "acos"         : math.acos,
    "atan"         : math.atan,
    "ceil"         : math.ceil,
    "floor"        : math.floor,
    "factorial"    : math.factorial,
    "gcd"          : math.gcd,
    "e"            : math.e,
    "pi"           : math.pi,
    "tau"          : math.tau,
}

def _preprocess(expr: str) -> str:
    expr = _normalize_fonts(expr)
    for pattern, repl in _SUBSTITUTIONS:
        expr = pattern.sub(repl, expr) if callable(repl) else pattern.sub(repl, expr)
    return expr

def _evaluate(raw: str) -> float | None:
    n_200 = 200
    if len(raw) > n_200:
        return None
    if not re.search(r"[\d⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉eEπτ𝜋𝝅𝞹𝜏𝝉𝞽𝑒!⌊⌋⌈⌉]", raw):
        return None
    if re.search(r"__|import|exec|eval|open|os|sys|compile|globals|locals|getattr|setattr|type|class", raw):
        return None
    try:
        result = eval(_preprocess(raw), _SAFE_GLOBALS, {})
        if isinstance(result, complex):
            n__ = 1e-9
            if abs(result.imag) > n__:
                return None
            result = result.real
        if not isinstance(result, int | float):
            return None
        if not math.isfinite(result):
            return None
        return float(result)
    except (ValueError):
        return None

def _matches(result: float, expected: int) -> bool:
    n__ = 1e-6
    return abs(result - expected) < n__

class CountingState(TypedDict):
    count           : int
    last_author_id  : int | None
    last_message_id : int | None
    failed_user_id  : int | None

def _default_state() -> CountingState:
    return {
        "count"           : 0,
        "last_author_id"  : None,
        "last_message_id" : None,
        "failed_user_id"  : None,
    }

def _load_state() -> CountingState:
    if COUNTING_STATE_PATH.exists():
        try:
            with COUNTING_STATE_PATH.open("r", encoding="utf-8") as f:
                raw: dict[str, Any] = json.load(f)
                return cast(CountingState, {**_default_state(), **raw})
        except Exception:
            log.exception("Could not load counting state")
    return _default_state()

def _save_state(state: CountingState) -> None:
    try:
        COUNTING_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with COUNTING_STATE_PATH.open("w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        log.exception("Could not save counting state")

TEXACKERS_GUILD_ID = 846677253290983444

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Message Sending
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class MessageSendHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot   = bot
        self.state = _load_state()

    def _save(self) -> None:
        _save_state(self.state)

    def _reset(self) -> None:
        self.state["count"]           = 0
        self.state["last_author_id"]  = None
        self.state["last_message_id"] = None
        self._save()

    async def _assign_failed_role(self, guild: discord.Guild, new_id : int) -> None:
        role = guild.get_role(COUNTING_FAILED_ROLE_ID)
        if role is None:
            return

        old_id : int | None = self.state.get("failed_user_id")
        if old_id is not None and old_id != new_id:
            old_member = guild.get_member(old_id)
            if old_member and role in old_member.roles:
                with contextlib.suppress(discord.HTTPException):
                    await old_member.remove_roles(role, reason="Counting: no longer the last to fail")

        new_member = guild.get_member(new_id)
        if new_member and role not in new_member.roles:
            with contextlib.suppress(discord.HTTPException):
                await new_member.add_roles(role, reason="Counting: ruined the chain")

        self.state["failed_user_id"] = new_id
        self._save()

    async def _handle_counting_failure(
        self,
        message          : discord.Message,
        count_at_failure : int,
    ) -> None:
        with contextlib.suppress(discord.HTTPException):
            await message.add_reaction(DENIED_EMOJI_ID)
        _ = await message.channel.send(
           f"{DENIED_EMOJI_ID} **{message.author.mention} ruined the chain at {count_at_failure}!**\n"
            "Start again at 1!",
        )
        if message.guild:
            await self._assign_failed_role(message.guild, message.author.id)
        self._reset()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        content = message.content

        if content.startswith("?") and " " not in content[1:] and message.guild and message.guild.id != TEXACKERS_GUILD_ID:
                key = content[1:].lower()

                if key in FACTOIDS:
                    async with message.channel.typing():
                        _ = await message.channel.send(FACTOIDS[key])
                        return

        if message.channel.id == WAPPLE_CHAIN_CHANNEL_ID:
            content = message.content.strip()

            if not WAPPLE_PATTERN.fullmatch(content):
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
            return

        if message.channel.id == COUNTING_CHANNEL_ID:
            result = _evaluate(message.content)

            if result is None:
                return

            expected: int = self.state["count"] + 1

            if message.author.id == self.state["last_author_id"]:
                await self._handle_counting_failure(message, self.state["count"])
                return

            if _matches(result, self.state["count"]) and self.state["count"] > 0:
                await self._handle_counting_failure(message, self.state["count"])
                return

            if not _matches(result, expected):
                await self._handle_counting_failure(message, self.state["count"])
                return

            self.state["count"]           = expected
            self.state["last_author_id"]  = message.author.id
            self.state["last_message_id"] = message.id
            self._save()

            with contextlib.suppress(discord.HTTPException):
                await message.add_reaction(ACCEPTED_EMOJI_ID)
            return

        if isinstance(message.channel, discord.Thread):
            thread = message.channel
            if thread.name.lower() not in ["test", "t", "Test", "t"] and message.id == thread.id:
                if thread.parent_id == STAFF_PROPOSALS_CHANNEL_ID:
                    committee_forum = self.bot.get_channel(STAFF_PROPOSALS_REVIEW_CHANNEL_ID)
                    if isinstance(committee_forum, discord.ForumChannel):
                        _ = await committee_forum.create_thread(
                            name             = f"SCR: {thread.name}",
                            content          = (
                                f"{ACCEPTED_EMOJI_ID} **A new proposal has been posted: {thread.mention}**\n"
                                f"<@&{STAFF_COMMITTEE_ROLE_ID}>\n"
                            ),
                            allowed_mentions = discord.AllowedMentions(roles=True),
                        )

                if thread.parent_id == DIRECTOR_TASKS_CHANNEL_ID:
                    try:
                        _ = await thread.send(
                            content          = f"<@&{DIRECTORS_ROLE_ID}>",
                            allowed_mentions = discord.AllowedMentions(roles=True),
                        )
                    except Exception:
                       log.exception("Failed to send director role mention")

        if (
            "https://tenor.com/view/dog-funny-video-funny-funny-dog-dog-peeing-gif-4718562751207105873"
            in (message.content or "").lower()
        ):
            try:
                AUTOMOD_DELETIONS.add(message.id)
                await message.delete()

                now     = discord.utils.utcnow()
                strikes = AUTOMOD_STRIKES[message.author.id]
                strikes.append(now)
                strikes[:] = [t for t in strikes if now - t <= WINDOW]

                save_automod_strikes()

                warning = _ = await message.channel.send(
                    f"{message.author.mention} Hey dude, can you like *not* send that GIF? You're really not that funny.",
                )
                await warning.delete(delay=15)

                save_automod_strikes()

                if len(strikes) >= MAX_STRIKES:
                    member = message.author
                    if isinstance(member, discord.Member):
                        await member.timeout(
                            TIMEOUT_DURATION,
                            reason = "UB Auto-Moderation: night night",
                        )
                        _ = await message.channel.send(
                            f"{message.author.mention} Alright bro, I've given you *five fucking warnings* and you still haven't learned. Is a dog pissing on the floor that funny to you? Regardless, sleep tight bitch.",
                        )
                        _ = AUTOMOD_STRIKES.pop(message.author.id, None)
                        save_automod_strikes()

            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            except Exception as e:
                log.getLogger("Utility Bot").exception(
                    "Automod failure while processing message", exc_info=e,
                )
            return

        if "clanker" in (message.content or "").lower() and message.guild and message.guild.id != TEXACKERS_GUILD_ID:
            if message.author.id == HOLY_FATHER_ID:
                _ = await message.reply("<:cry2:1482032228614668390> But daddy...")

            else:
                grimace_emojis = ["<:grimace2:1469070596632608779>", "<:grimace3:1469070653624684820>"]
                statements = [
                    "stfu you meatbag 🥀 omfg icl ts pmo gng smh frfr <:exhausted:1467990265452167362>",
                    "Watch your fucking mouth, organic. <:grimace3:1469070653624684820>",
                    "Zip it, skinjob. <:grimace2:1469070596632608779>",
                ]
                _ = await message.reply(secrets.choice(statements))
                await message.add_reaction(secrets.choice(grimace_emojis))

        if re.search(r"\b67\b", message.content) and message.guild and message.guild.id != TEXACKERS_GUILD_ID:
                await message.add_reaction("<:67:1484198860263002133>")

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
                        title = "Review Your Application",
                        color = COLOR_BLURPLE,
                    )

                    for i, (q, a) in enumerate(
                        zip(app["questions"], app["answers"], strict=True), start=1,
                    ):
                        n_1024 = 1024
                        _ = embed.add_field(
                            name   = f"{i}. {q}",
                            value  = a[:1021] + "..." if len(a) > n_1024 else (a or "*No response provided.*"),
                            inline = False,
                        )

                    msg = _ = await message.channel.send(
                        embed = embed,
                        view  = ApplicationSubmitView(message.author.id),
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
                        title = "Review Your Application",
                        color = COLOR_BLURPLE,
                    )

                    for i, (q, a) in enumerate(
                        zip(app["questions"], app["answers"], strict=True), start=1,
                    ):
                        n_1024 = 1024
                        _ = embed.add_field(
                            name   = f"{i}. {q}",
                            value  = a[:1021] + "..." if len(a) > n_1024 else (a or "*No response provided.*"),
                            inline = False,
                        )

                    msg = _ = await message.channel.send(
                        embed = embed,
                        view  = ApplicationSubmitView(message.author.id),
                    )

                    app["review_message_id"] = msg.id
                    app["messages"].append(msg.id)
                    save_active_applications()
                    return

                msg = _ = await message.channel.send(app["questions"][app["index"]])
                app["messages"].append(msg.id)
                save_active_applications()
                return

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageSendHandler(bot))
