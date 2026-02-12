import discord
from discord.ext import commands
from discord import ui

from core.state import (
    APPLICATIONS_OPEN,
    BLACKLIST,
    ACTIVE_APPLICATIONS,
    save_active_applications
)

from constants import (
    COLOR_GREEN,
    COLOR_BLURPLE,
    COLOR_RED,

    ACCEPTED_EMOJI_ID,
    CONTESTED_EMOJI_ID,
    DENIED_EMOJI_ID,

    MODERATORS_ROLE_ID,
    JUNIOR_MODERATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
    MODERATORS_AND_ADMINISTRATORS_ROLE_ID,
    STAFF_ROLE_ID,
    DIRECTORS_ROLE_ID,
    TRUSTED_ROLE_ID,

    APPLICATION_LOG_CHANNEL_ID,
    ARCHIVED_APPLICATION_LOG_CHANNEL_ID
)

ADMIN_ROLE_IDS = {
    JUNIOR_ADMINISTRATORS_ROLE_ID,
    ADMINISTRATORS_ROLE_ID,
    SENIOR_ADMINISTRATORS_ROLE_ID,
}

MOD_ROLE_IDS = {
    JUNIOR_MODERATORS_ROLE_ID,
    MODERATORS_ROLE_ID,
    SENIOR_MODERATORS_ROLE_ID,
}

async def test():
    pass

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Applications System
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Decision Modal
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class DecisionModal(ui.Modal, title="Decision Reason"):
    notes = ui.TextInput(label="Notes", required=True)

    def __init__(self, applicant_id: int, app_type: str, accepted: bool, message_id: int):
        super().__init__()
        self.message_id = message_id
        self.applicant_id = applicant_id
        self.app_type = app_type
        self.accepted = accepted

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(
            ephemeral=True
        )
        await interaction.followup.send(
            "Decision recorded.",
            ephemeral=True
        )
        guild = interaction.guild

        log_channel = interaction.client.get_channel(APPLICATION_LOG_CHANNEL_ID)
        if not isinstance(log_channel, discord.TextChannel):
            return

        try:
            msg = await log_channel.fetch_message(self.message_id)
        except discord.NotFound:
            return

        if self.applicant_id not in ACTIVE_APPLICATIONS:
            await interaction.followup.send(
                "This application has already been handled.",
                ephemeral=True
            )
            return

        if guild is None:
            return

        member = guild.get_member(self.applicant_id)
        user = interaction.client.get_user(self.applicant_id)
        if member is None or user is None:
            return

        if self.accepted:
            role_ids = ([
                JUNIOR_ADMINISTRATORS_ROLE_ID, ADMINISTRATORS_ROLE_ID
            ] if self.app_type == "admin" else
                        [JUNIOR_MODERATORS_ROLE_ID, MODERATORS_ROLE_ID])

            roles = [
                r for rid in role_ids + [STAFF_ROLE_ID, TRUSTED_ROLE_ID]
                if (r := guild.get_role(rid))
            ]

            if roles:
                await member.add_roles(*roles)

            member = guild.get_member(self.applicant_id)
            if member is None:
                return

            member_role_ids = {r.id for r in member.roles}

            is_mod = member_role_ids & {
                JUNIOR_MODERATORS_ROLE_ID,
                MODERATORS_ROLE_ID,
                SENIOR_MODERATORS_ROLE_ID,
            }

            is_admin = member_role_ids & {
                JUNIOR_ADMINISTRATORS_ROLE_ID,
                ADMINISTRATORS_ROLE_ID,
                SENIOR_ADMINISTRATORS_ROLE_ID,
            }

            if is_mod and is_admin:
                combined_role = guild.get_role(
                    MODERATORS_AND_ADMINISTRATORS_ROLE_ID)
                if combined_role and member:
                    await member.add_roles(combined_role)

            await user.send(
                f"{ACCEPTED_EMOJI_ID} **Application Accepted**\n"
                f"-# Your application has been accepted! Welcome to the staff team!\n"
                f"-# **Notes:** {self.notes.value}"
            )
        else:
            await user.send(
                f"{DENIED_EMOJI_ID} **Application Denied**\n"
                f"-# Your application has been denied."
                f"-# **Notes:** {self.notes.value}"
            )

        new_embed = discord.Embed(
            title=msg.embeds[0].title if msg.embeds else "Application Decision",
            color=COLOR_GREEN if self.accepted else COLOR_RED
        )
        new_embed.add_field(
            name="Decision",
            value="Accepted" if self.accepted else "Denied",
            inline=True
        )
        new_embed.add_field(
            name="Handled By",
            value=interaction.user.mention,
            inline=True
        )
        new_embed.add_field(
            name="Decision Notes",
            value=self.notes.value,
            inline=False
        )

        new_embed.set_footer(text="Decision Made")
        new_embed.timestamp = interaction.created_at

        await msg.edit(embed=new_embed, view=None)

        archive_channel = interaction.client.get_channel(
            ARCHIVED_APPLICATION_LOG_CHANNEL_ID
        )

        if isinstance(archive_channel, discord.TextChannel):
            original_embed = msg.embeds[0] if msg.embeds else None

            if original_embed:
                archive_embed = discord.Embed(
                    title="Archived Application",
                    color=COLOR_BLURPLE,
                    timestamp=interaction.created_at
                )

                for field in original_embed.fields:
                    archive_embed.add_field(
                        name=field.name,
                        value=field.value,
                        inline=False
                    )

                await archive_channel.send(embed=archive_embed)

        thread_id = ACTIVE_APPLICATIONS.get(self.applicant_id, {}).get("thread_id")
        if thread_id:
            try:
                channel = await interaction.client.fetch_channel(thread_id)

                if isinstance(channel, discord.Thread):
                    await channel.edit(locked=True, archived=True)
            except discord.NotFound:
                pass

        ACTIVE_APPLICATIONS.pop(self.applicant_id, None)
        save_active_applications()

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Decision View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class DecisionView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Accept", style=discord.ButtonStyle.success, custom_id="decision:accept")
    async def accept(self, interaction: discord.Interaction, _):
        msg = interaction.message
        assert msg is not None
        data = next(
            (v for v in ACTIVE_APPLICATIONS.values()
             if v.get("log_message_id") == msg.id),
            None
        )
        if not data:
            await interaction.response.send_message(
                "This application has already been handled.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DecisionModal(
                applicant_id=data["applicant_id"],
                app_type=data["type"],
                accepted=True,
                message_id=msg.id
            )
        )

    @ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="decision:deny")
    async def deny(self, interaction: discord.Interaction, _):
        msg = interaction.message
        assert msg is not None
        data = next(
            (v for v in ACTIVE_APPLICATIONS.values()
             if v.get("log_message_id") == msg.id),
            None
        )
        if not data:
            await interaction.response.send_message(
                "This application has already been handled.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            DecisionModal(
                applicant_id=data["applicant_id"],
                app_type=data["type"],
                accepted=False,
                message_id=msg.id
            )
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Questions / State
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

ADMIN_QUESTIONS = [
    "What is your timezone?", "Are you above the age of 13?",
    "How long have you been a member of this server?",
    "Why do you want to be an administrator?",
    "What prior experience do you have in Discord servers (if any)?",
    "How active are you on Discord on a typical week?",
    "What do you think makes a good staff member?",
    "How do you handle responsibility and long-term commitments?",
    "What experience do you have managing Discord bots, roles, or channels?",
    "Which Discord permissions are you most familiar with, and why?",
    "A bot you manage suddenly starts spamming or malfunctioning. What steps do you take?",
    "How would you safely test a new bot or feature before rolling it out server-wide?",
    "A role’s permissions are accidentally misconfigured, exposing private channels. What do you do first?",
    "How do you organize roles and channels to keep a server easy to navigate?",
    "If an administrator disagrees with another administrator’s setup decision, how would you handle it?",
    "How do you document or communicate technical changes to the rest of the staff team?",
    "What security risks should administrators be aware of on Discord?",
    "If given access to high-level permissions, how would you ensure you don’t misuse them?"
]

MOD_QUESTIONS = [
    "What is your timezone?", "Are you above the age of 13?",
    "How long have you been a member of this server?",
    "Why do you want to be a moderator?",
    "What prior experience do you have moderating communities (if any)?",
    "How active are you on Discord on a typical week?",
    "What do you think makes a good staff member?",
    "How do you handle responsibility and long-term commitments?",
    "How would you describe your approach to enforcing rules fairly?",
    "A user breaks a minor rule but claims they didn’t know it existed. How do you respond?",
    "Two users are arguing aggressively in chat but haven’t broken a rule yet. What do you do?",
    "A user reports harassment, but there is little evidence. How do you proceed?",
    "How do you stay calm when dealing with difficult or disrespectful users?",
    "What would you do if you saw another moderator enforcing rules unfairly?",
    "How do you balance being friendly with being authoritative?",
    "A rule is unclear or outdated. How would you handle enforcement in the meantime?",
    "How would you handle repeat offenders who skirt the rules without clearly breaking them?",
    "What does creating a 'safe place for everyone' mean to you in practice?"
]

async def delete_application_messages(client: discord.Client, user_id: int):
    data = ACTIVE_APPLICATIONS.get(user_id)
    if not data:
        return

    channel_id = data.get("channel_id")
    if not channel_id:
        return

    channel = await client.fetch_channel(channel_id)
    if not isinstance(channel, discord.DMChannel):
        return

    for msg_id in data.get("messages", []):
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    ACTIVE_APPLICATIONS.pop(user_id, None)
    save_active_applications()

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Role Gate Logic
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

def can_apply(member: discord.Member, app_type: str) -> bool:
    role_ids = {r.id for r in member.roles}
    is_admin = bool(role_ids & ADMIN_ROLE_IDS)
    is_mod = bool(role_ids & MOD_ROLE_IDS)

    if is_admin and is_mod:
        return False
    if app_type == "admin" and is_admin:
        return False
    if app_type == "mod" and is_mod:
        return False

    return True

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Application Submit View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ApplicationSubmitView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @ui.button(label="Edit", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, _):
        data = ACTIVE_APPLICATIONS.get(self.user_id)
        if not data:
            return
        data["editing"] = True
        data["reviewing"] = False
        await interaction.response.send_message(
            "Select a question to edit:",
            view=EditQuestionSelectView(
            self.user_id),
            ephemeral=True
        )

    @ui.button(label="Submit", style=discord.ButtonStyle.success)
    async def submit(self, interaction: discord.Interaction, _):
        data = ACTIVE_APPLICATIONS.get(self.user_id)
        if not data:
            await interaction.response.send_message(
                "This application is no longer active",
                ephemeral=True
            )
            return

        try:
            dm_channel = await interaction.client.fetch_channel(
                data["channel_id"])

            if isinstance(dm_channel, discord.DMChannel):
                try:
                    review_msg = await dm_channel.fetch_message(
                        data["review_message_id"])
                    await review_msg.edit(view=None)
                except discord.NotFound:
                    pass
        except discord.NotFound:
            pass
        channel = interaction.client.get_channel(APPLICATION_LOG_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        type_map = {"admin": "Administrator", "mod": "Moderator"}

        embed = discord.Embed(
            title=
            f"{interaction.user} — {type_map.get(data['type'], data['type'].capitalize())} Application",
            color=COLOR_BLURPLE
        )

        for i, (q, a) in enumerate(zip(data["questions"], data["answers"]), start=1):
            embed.add_field(
                name=f"{i}. {q}",
                value=a[:1021] + "..." if len(a) > 1024 else (a or "*No response provided.*"),
                inline=False
            )

        msg = await channel.send(
            content=f"<@&{DIRECTORS_ROLE_ID}>",
            embed=embed
        )

        await msg.edit(view=DecisionView())

        thread = await msg.create_thread(
            name=f"{interaction.user.display_name}'s "
                 f"{'Administrator' if data['type'] == 'admin' else 'Moderator'} Application"
        )

        ACTIVE_APPLICATIONS[self.user_id]["thread_id"] = thread.id
        save_active_applications()

        ACTIVE_APPLICATIONS[self.user_id]["log_message_id"] = msg.id
        ACTIVE_APPLICATIONS[self.user_id]["applicant_id"] = self.user_id
        save_active_applications()

        await interaction.response.send_message(
            "Application submitted.",
            ephemeral=True
        )

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, _):
        await delete_application_messages(interaction.client, self.user_id)
        await interaction.response.send_message(
            "Your application has been cancelled and deleted.",
            ephemeral=True
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Application Components
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ApplicationComponents(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        for item in self.walk_children():
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "application_menu:apply_mod":
                    item.callback = self.mod_btn
                elif item.custom_id == "application_menu:apply_admin":
                    item.callback = self.admin_btn

    container1 = discord.ui.Container(
        discord.ui.TextDisplay(
            content="# Staff Applications\n"
            "Staff applications are reviewed carefully to ensure we select members who are responsible, active, and aligned with the server’s values. Take your time when completing the application and ensure all answers are honest and well thought out.\n\n"
            "- **How to Start:** Fully complete the application form and answer every question to the best of your ability.\n"
            "- **Detail Matters:** Short, low-effort, or vague responses significantly reduce your chances of acceptance.\n"
            "- **Honesty Required:** Any form of lying or exaggeration will result in automatic rejection.\n"
            "- **Professionalism:** Use respectful language and proper grammar throughout your application.\n\n"
            "After submission, applications will be reviewed by the Directorate team. Do not DM staff for updates, as this will negatively affect your application. Decisions are final (unless stated otherwise), and feedback may not always be provided.\n\n"
            "**Note:** All applications are and will be taken seriously. Be professional — take your time. You may cancel and delete your application at any point by typing `~cancel`."
        ),
        discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.large
        ),
        discord.ui.TextDisplay(
            content="We look forward to reviewing any and all applications! Sincerely,\n-# The Goobers Directorate team."
        ),
        discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.large
        ),
        discord.ui.ActionRow(
                discord.ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Open Moderators Application",
                    custom_id="application_menu:apply_mod",
                ),
                discord.ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Open Administrators Application",
                    custom_id="application_menu:apply_admin",
                ),
        ),
        accent_color=COLOR_GREEN,
    )

    async def mod_btn(self, interaction: discord.Interaction):
        view = ApplicationMenuView()
        await view.handle_mod_application(interaction)

    async def admin_btn(self, interaction: discord.Interaction):
        view = ApplicationMenuView()
        await view.handle_admin_application(interaction)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Application Menu View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class ApplicationMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_mod_application(self, interaction: discord.Interaction):
        if interaction.user.id in BLACKLIST["applications"]:
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **You have been blacklisted from opening applications!**\n"
                "You are blacklisted from opening applications. Contact a Director.",
                ephemeral=True
            )
            return

        if interaction.user.id in ACTIVE_APPLICATIONS:
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "You already have an active application. Please finish or cancel it before starting a new one.",
                ephemeral=True
            )
            return

        if not APPLICATIONS_OPEN["mod"]:
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "Sorry, Moderator applications are closed right now!",
                ephemeral=True
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "This can only be used in a server.",
                ephemeral=True
            )
            return

        if not can_apply(interaction.user, "mod"):
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "You already exist within the Goobers Moderation Team.",
                ephemeral=True
            )
            return

        ACTIVE_APPLICATIONS[interaction.user.id] = {
            "type": "mod",
            "questions": MOD_QUESTIONS,
            "answers": [],
            "index": 0,
            "editing": False,
            "reviewing": False,
            "channel_id": None,
            "messages": []
        }
        save_active_applications()

        dm = await interaction.user.create_dm()
        msg = await dm.send(
            MOD_QUESTIONS[0] +
            "\n-# You can cancel and delete the application at any point by typing `~cancel`."
        )

        data = ACTIVE_APPLICATIONS[interaction.user.id]
        data["channel_id"] = dm.id
        data["messages"].append(msg.id)
        save_active_applications()

        await interaction.response.send_message(
            f"{ACCEPTED_EMOJI_ID} **Successfully opened application!**\n"
            "The application has been sent to your DMs.",
            ephemeral=True
        )

    async def handle_admin_application(self, interaction: discord.Interaction):
        if interaction.user.id in BLACKLIST["applications"]:
            await interaction.response.send_message(
                f"{DENIED_EMOJI_ID} **You have been blacklisted from opening applications!**\n"
                "You are blacklisted from opening applications. Contact a Director.",
                ephemeral=True
            )
            return

        if interaction.user.id in ACTIVE_APPLICATIONS:
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "You already have an active application. Please finish or cancel it before starting a new one.",
                ephemeral=True
            )
            return

        if not APPLICATIONS_OPEN["admin"]:
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "Sorry, Administrator applications are closed right now!",
                ephemeral=True
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "This can only be used in a server.",
                ephemeral=True
            )
            return

        if not can_apply(interaction.user, "admin"):
            await interaction.response.send_message(
                f"{CONTESTED_EMOJI_ID} **Failed to open application!**\n"
                "You already exist within the Goobers Administration Team.",
                ephemeral=True
            )
            return

        ACTIVE_APPLICATIONS[interaction.user.id] = {
            "type": "admin",
            "questions": ADMIN_QUESTIONS,
            "answers": [],
            "index": 0,
            "editing": False,
            "reviewing": False,
            "channel_id": None,
            "messages": []
        }
        save_active_applications()

        dm = await interaction.user.create_dm()
        msg = await dm.send(
            ADMIN_QUESTIONS[0] +
            "\n-# You can cancel and delete the application at any point by typing `~cancel`."
        )

        data = ACTIVE_APPLICATIONS[interaction.user.id]
        data["channel_id"] = dm.id
        data["messages"].append(msg.id)
        save_active_applications()

        await interaction.response.send_message(
            f"{ACCEPTED_EMOJI_ID} **Successfully opened application!**\n"
            "The application has been sent to your DMs.",
            ephemeral=True
        )

    async def mod_btn(self, interaction: discord.Interaction, _):
        await self.handle_mod_application(interaction)

    async def admin_btn(self, interaction: discord.Interaction, _):
        await self.handle_admin_application(interaction)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Edit Question Select View
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class EditQuestionSelectView(ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id

        data = ACTIVE_APPLICATIONS.get(user_id)
        if not data:
            return

        options = [
            discord.SelectOption(
                label=f"Question {i + 1}",
                description=(q[:97] + "...") if len(q) > 100 else q,
                value=str(i)) for i, q in enumerate(data["questions"])
        ]

        self.add_item(EditQuestionSelect(options, user_id))

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Edit Question Select
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

class EditQuestionSelect(ui.Select):
    def __init__(self, options, user_id):
        super().__init__(placeholder="Select a question to edit.",
                         options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        data = ACTIVE_APPLICATIONS.get(self.user_id)
        if not data:
            return

        data["index"] = int(self.values[0])
        data["editing"] = True
        data["reviewing"] = False
        save_active_applications()

        await interaction.response.send_message(
            f"**Editing Question:**\n{data['questions'][data['index']]}",
            ephemeral=True
        )

class ApplicationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(ApplicationsCog(bot))