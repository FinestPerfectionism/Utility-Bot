from discord import ButtonStyle, SeparatorSpacing
from discord.ui import Button, Container, LayoutView, Section, Separator, TextDisplay
from inspect import cleandoc

from constants import STANDSTILL_EMOJI_ID


class RuleComponents1(LayoutView):
    container : Container[LayoutView] = Container(
        TextDisplay(
            content = cleandoc("""
                # Welcome to The Goobers!\n
                A server for dumbassery and gaming.\n
                -# **Note:** It is within moderators' discretion as to whether you are breaking rules regardless of if the rules they find you to be breaking are listed here.
                """
            ),
        ),
    )

class RuleComponents2(LayoutView):
    def __init__(self, timestamp : int) -> None:
        super().__init__(timeout = None)
        self.container : Container[LayoutView] = Container(
            Section[LayoutView](
                TextDisplay(
                    content =
                        "# Rules",
                ),
                accessory = Button(
                    url   =  "https://discord.com/terms",
                    style = ButtonStyle.link,
                    label =  "Discord Terms of Service",
                    emoji = f"{STANDSTILL_EMOJI_ID}",
                ),
            ),
            TextDisplay(
                content = cleandoc(f"""
                    Rules last updated <t:{timestamp}:D>.\n
                    -# All below is subject to change at any time based on Directorate decision or structural updates.\n
                    -# Assembled by the Directorate team. Primarily written by <@1311394031640776716>.\n
                    """
                ),
            ),
            Separator(
                visible = False,
                spacing = SeparatorSpacing.small,
            ),
            Separator(
                visible = True,
                spacing = SeparatorSpacing.small,
            ),
            Separator(
                visible = False,
                spacing = SeparatorSpacing.small,
            ),
            TextDisplay(
                content =
                    "## §1 Behavior\n"
                    "### §1.1 Harassment\n"
                    "Any form of harassment, threats, or intimidation is forbidden.\n"
                    "**Example:**\n"
                    "> \"imma kill you if you don't give tell me\"\n\n"
                    "### §1.2 Discrimination\n"
                    "Racism, sexism, ableism, or other discriminatory behavior is prohibited.\n"
                    "**Example:**\n"
                    "> \"you're so acoustic\"\n\n"
                    "### §1.3 NSFW Content\n"
                    "Sharing explicit content is strictly prohibited in all channels unless explicitly marked NSFW. (Looks like we have none, so no NSFW :])\n"
                    "**Example:**\n"
                    "> \"Here's the link to my special cam 😘🥵: …\"\n\n"
                    "## §2 Language\n"
                    "### §2.1 No Loophole Language\n"
                    "Attempting to bypass rules through euphemisms, coded language, or indirect references is forbidden.\n"
                    "**Example:**\n"
                    '> "-.-- --- ..- .----. .-. . / ... ..- -.-. .... / .- / ... .. .-.. .-.. -.-- / .-.. .. - - .-.. . / -... .-.. ..- -.. / ..-. --- .-. / - .-. .- -. ... .-.. .- - .. -. --. / - .... .. ..."\n\n'
                    "### §2.2 Spam\n"
                    "Repetitive messages, excessive emojis, pinging, or automated scripts are prohibited.\n"
                    "**Example:**\n"
                    '> "hello hello hello hello hello hello hello hello hello hello hello hello hello hello hello hello hello hello hello hello"\n\n'
                    "## §3 Privacy and Safety\n"
                    "### §3.1 Doxxing\n"
                    "Sharing personal information without explicit consent is banned.\n"
                    "**Example:**\n"
                    '> "his name is walter hartwell white he lives at 308 negra arroyo lane, albuquerque, new mexico, 87104."\n\n'
                    "### §3.2 Impersonation\n"
                    "Pretending to be staff, members, or external figures is not allowed.\n"
                    "**Example:**\n"
                    '> "im totally S. Director | 𝙸𝚗𝚏𝚒𝚗𝚒𝚞𝚖³"\n\n'
                    "## §4 Channel Use\n"
                    "### §4.1 Channel Specific Rules\n"
                    "All content must follow the designated purpose of each channel. Off-topic content is prohibited.\n"
                    "**Example:**\n"
                    "> *Ear-rape*",
            ),
        )
        _ = self.add_item(self.container)
