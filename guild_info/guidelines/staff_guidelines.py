import discord


class StaffComponents1(discord.ui.LayoutView):
    container: discord.ui.Container[discord.ui.LayoutView] = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Welcome to Staff Guidelines!\n"
                "Shared guidelines for all members of the Goobers Staff Team.\n"
                "-# **Note:** These guidelines are staff-only and may be revised at any time by Directorate decision. They apply to all staff regardless of team or seniority. Sharing internal staff policy outside staff spaces is prohibited.",
        ),
    )

class StaffComponents2(discord.ui.LayoutView):
    def __init__(self, timestamp: int) -> None:
        super().__init__(timeout = None)
        self.container: discord.ui.Container[discord.ui.LayoutView] = discord.ui.Container(
            discord.ui.TextDisplay(
                content=
                    "# Staff Guidelines\n"
                   f"Staff guidelines last updated <t:{timestamp}:D>.\n"
                    "-# All below is subject to change at any time based on Directorate decision or structural updates.\n"
                    "-# Assembled by the Directorate team. Primarily written by <@1311394031640776716>.\n",
            ),
            discord.ui.Separator(
                visible = False,
                spacing = discord.SeparatorSpacing.small,
            ),
            discord.ui.Separator(
                visible = True,
                spacing = discord.SeparatorSpacing.small,
            ),
            discord.ui.Separator(
                visible = False,
                spacing = discord.SeparatorSpacing.small,
            ),
            discord.ui.TextDisplay(
                content=
                    "## §1 The Staff Structure\n"
                    "The Goobers Staff Team is composed of three distinct bodies: the **Directorate**, the **Moderation Team**, and the **Administration Team**. Each serves a different function, and their separation is intentional. Staff members must understand not only their own team's responsibilities but how all three relate to each other.\n\n"
                    "### §1.1 The Directorate\n"
                    "The Directorate governs the server at the highest level. Directors hold Senior Staff status within both the Moderation and Administration Teams, and may exercise authority across both. Directorate decisions are final. All staff teams operate under Directorate oversight.\n\n"
                    "### §1.2 The Moderation Team\n"
                    "The Moderation Team is responsible for member-facing enforcement: rule violations, tickets, mutes, timeouts, kicks, bans, and quarantines. Moderators do not manage server infrastructure. Their authority is over member conduct, not server structure.\n\n"
                    "### §1.3 The Administration Team\n"
                    "The Administration Team is responsible for the server's structural and technical backend: channels, roles, expressions, bots, webhooks, events, and server-level settings. Administrators do not hold enforcement authority over members. Their authority is over server structure, not member conduct.\n\n"
                    "### §1.4 Separation of Function\n"
                    "The Moderation and Administration Teams are **not the same team** and must not be treated as interchangeable. A Moderator observing a structural issue should report it to an Administrator or Director rather than acting on it. An Administrator observing a conduct issue should report it to a Moderator or Director rather than acting on it. Acting outside your team's scope without authorization is not permitted.\n\n"
                    "## §2 Dual Roles and Overlap\n"
                    "Staff members may hold positions in both the Moderation and Administration Teams simultaneously. This is explicitly permitted and common at higher levels of the staff structure. Dual-role staff must maintain awareness of which team's authority applies in a given moment and act accordingly.\n\n"
                    "### §2.1 Directors as Senior Staff\n"
                    "Directors hold Senior Staff status in both teams and may exercise Senior Moderator and Senior Administrator authority when necessary. This exists to allow intervention in escalated situations — not as an invitation to routinely handle frontline moderation or administration.\n\n"
                    "### §2.2 Dual-Role Expectations\n"
                    "Holding a role in both teams does not exempt a staff member from either team's standards. When acting as a Moderator, Moderation guidelines govern; when acting as an Administrator, Administration guidelines govern.",
            ),
        )
        _ = self.add_item(self.container)

class StaffComponents3(discord.ui.LayoutView):
    container: discord.ui.Container[discord.ui.LayoutView] = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "## §3 Proposals as a Shared System\n"
                "The Staff Proposal system is the primary formal mechanism through which all staff teams interact.\n\n"
                "### §3.1 Who Can Raise Proposals\n"
                "Any member of the Staff Team — Moderators, Administrators, Directors, and the Owner — may raise a Staff Proposal. Guild Trustees may also raise proposals within their defined scope. All proposals are expected to be formal, precise, and beneficial to the server.\n\n"
                "### §3.2 Advisory Voting\n"
                "All staff are equal in advisory voting ability. A vote cast by a Junior Moderator carries the same advisory weight as one cast by a Senior Administrator. The advisory poll is non-binding — final authority rests with the Staff Committee.\n\n"
                "### §3.3 Implementation is Administration's Responsibility\n"
                "Once a proposal is accepted, implementation is the Administration Team's responsibility. If an accepted proposal affects moderation workflows, Administrators must coordinate with the Moderation Team before and during implementation.\n\n"
                "### §3.4 Scope Restrictions\n"
                "Proposals may not touch moderation policy, the core rules, or staff proposal procedures. These require separate processes and different thresholds. Staff may raise concerns about these topics in the appropriate internal channels.\n\n"
                "## §4 Cross-Team Communication\n"
                "The Moderation and Administration Teams share staff spaces and will regularly encounter situations that require coordination. Clear communication between teams is essential to avoid conflicting actions, gaps in coverage, and duplicated effort.\n\n"
                "### §4.1 Notifying the Other Team\n"
                "When an action in one team's domain may affect the other, the acting team must communicate before or immediately after acting. Examples include: infrastructure changes that affect moderation channels or bot commands (Administration notifies Moderation), or moderation events that require structural changes such as a lockdown (Moderation notifies Administration and escalates to Directors).\n\n"
                "### §4.2 Referring Across Teams\n"
                "If a staff member encounters an issue outside their team's scope, they must refer it promptly rather than ignoring it or attempting to handle it independently. Use the appropriate staff channel and tag the relevant team or a Director.\n\n"
                "### §4.3 Avoiding Conflicting Actions\n"
                "When both teams are simultaneously involved in a situation — such as a raid requiring both moderation action and potential lockdown — actions must be coordinated through Directors. Do not carry out structural or enforcement changes in parallel without a shared understanding of who is doing what.",
        ),
    )

class StaffComponents4(discord.ui.LayoutView):
    container: discord.ui.Container[discord.ui.LayoutView] = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "## §5 Shared Conduct Standards\n"
                "The following standards apply to all staff regardless of team or seniority.\n\n"
                "### §5.1 Professionalism\n"
                "All staff are expected to conduct themselves professionally when acting in a staff capacity. This includes interactions with members, interactions with other staff, and conduct within internal staff channels. Conflict between staff members must be handled privately or escalated to the Directorate — not aired in public or semi-public spaces.\n\n"
                "### §5.2 Confidentiality\n"
                "Internal staff discussion, policy details, case information, proposal deliberations, and Directorate directives must not be shared outside staff spaces. This applies to all staff at all levels. Directorate members are not exempt.\n\n"
                "### §5.3 No Abuse of Authority\n"
                "Staff authority exists to serve the server and its members. Using staff permissions for personal gain, retaliation, favoritism, or to disadvantage any member or staff colleague is prohibited and grounds for removal. This applies across all three teams.\n\n"
                "### §5.4 Impartiality\n"
                "Staff must not take action — whether moderation or administrative — in situations where a personal conflict of interest exists. Hand the situation off to a colleague or escalate to a Director immediately.\n\n"
                "### §5.5 Out-of-Role Conduct\n"
                "Staff are community members outside their staff capacity. They are not held to a stricter behavioral standard in casual conversation, but sustained conduct that would reflect poorly on the staff team — targeted harassment, bad-faith disruption, or behavior inconsistent with the server's standards — may be reviewed by the Directorate regardless of whether it occurred in a staff capacity.\n\n"
                "## §6 Shared Expectations\n"
                "### §6.1 Activity\n"
                "All staff are expected to remain reasonably active within their role. The standard for acceptable activity may differ by team and seniority, but prolonged inactivity without prior notice is grounds for removal at Directorate discretion regardless of team.\n\n"
                "### §6.2 Good Faith\n"
                "Staff are expected to act in good faith at all times — toward members, toward colleagues, and toward the server. Decisions made in genuine good faith that turn out to be wrong will be handled with appropriate feedback. Decisions made in bad faith will be handled as misconduct.\n\n"
                "### §6.3 Escalation is Not Failure\n"
                "Escalating a situation to a Senior staff member or Director is always appropriate when a situation exceeds your scope, authority, or confidence. Attempting to handle something independently when escalation is warranted — and getting it wrong — is exponentially worse than escalating. No staff member will be penalized for escalating appropriately.",
        ),
    )
