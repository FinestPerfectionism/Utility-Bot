import discord

class ModerationComponents1(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=
                "# Welcome to Moderation Guidelines!\n"
                "Internal guidelines for the Goobers Moderation Team.\n"
                "-# **Note:** These guidelines are staff-only and may be revised at any time by Directorate decision. Sharing internal moderation policy outside staff spaces is prohibited."
        ),
    )

class ModerationComponents2(discord.ui.LayoutView):
    def __init__(self, timestamp: int) -> None:
        super().__init__(timeout=None)
        self.container = discord.ui.Container( # type: ignore
            discord.ui.TextDisplay( # type: ignore
                content=
                    "# Moderation Guidelines\n"
                   f"Moderation guidelines last updated <t:{timestamp}:D>.\n"
                    "-# All below is subject to change at any time based on Directorate decision or structural updates.\n"
                    "-# Assembled by the Directorate team. Primarily written by <@1311394031640776716>.\n"
            ),
            discord.ui.Separator( # type: ignore
                visible=False,
                spacing=discord.SeparatorSpacing.small
            ),
            discord.ui.Separator( # type: ignore
                visible=True,
                spacing=discord.SeparatorSpacing.small
            ),
            discord.ui.Separator( # type: ignore
                visible=False,
                spacing=discord.SeparatorSpacing.small
            ),
            discord.ui.TextDisplay( # type: ignore
                content=
                    "## §1 Scope and Permissions\n"
                    "Moderators must act within command permissions as implemented by the bot. If a command denies your action, escalate instead of attempting workarounds.\n\n"
                    "### §1.1 Role Scope\n"
                    "- **Junior Moderators** can create and view moderation notes, and mute members.\n"
                    "- **Senior Moderators and Directors** can execute primary enforcement: timeout, kick, ban, purge, and quarantine add. Senior Moderators and Directors can also use `/health`.\n"
                    "- **Directors only** can remove a timeout, unban, remove quarantine, configure case logs, and manage lockdown.\n\n"
                    "### §1.2 Documentation Requirement\n"
                    "All formal enforcement actions must be documented through bot commands so they are written to cases. If a command supports proof attachments, include proof when available.\n\n"
                    "### §1.3 Protected Targets\n"
                    "Staff and protected roles may not be timed out, kicked, or banned through normal moderation flow. If immediate containment is required, use quarantine (if authorized) or escalate to a Director.\n\n"
                    "## §2 Notes and Cases\n"
                    "### §2.1 Notes\n"
                    "Notes are part of the permanent internal moderation record and are visible to all Moderators and Directors. A note must include the behavior observed, context, and what action was or was not taken. Note deletion is restricted to Senior Moderators and Directors; editing or deleting another moderator's note is Director-only.\n\n"
                    "Do not add notes for informal interventions that did not result in a formal action.\n\n"
                    "### §2.2 Cases\n"
                    "Every enforcement command automatically creates a case entry. Use `/cases view` to review history before escalating punishments. Accumulated cases over a short period may justify escalation without an additional incident. Case log configuration via `/cases config` is Director-only.\n\n"
                    "## §3 Enforcement Standards\n"
                    "Punishments must be proportionate to the offense and consistent with prior enforcement. When in doubt, consult a Senior Moderator or Director before acting.\n\n"
                    "### §3.1 Timeouts\n"
                    "Timeouts are the default corrective action for active behavior violations when de-escalation fails or is inappropriate. Use the shortest duration that resolves the behavior. Timeout removals are Director-only; the hard cap is 28 days (bot-enforced).\n\n"
                    "- **5–15 minutes:** Minor disruption, first-offense spam, or off-topic behavior.\n"
                    "- **1–6 hours:** Repeated minor offenses, low-level harassment, or loophole language.\n"
                    "- **12–24 hours:** Significant harassment or repeated violations within a short timeframe.\n"
                    "- **3–7 days:** Severe harassment, discrimination, or explicit content outside NSFW.\n\n"
                    "Timeouts exceeding 7 days must be escalated to a Senior Moderator.\n\n"
                    "### §3.2 Kicks\n"
                    "Kicks are for serious disruption where the member may return under stricter expectations. Include precise reasons; vague reasons reduce review quality. **Kicks require Senior Moderator permissions.**\n\n"
                    "### §3.3 Bans\n"
                    "Bans must not be issued without clear justification. **Temporary bans** may be issued for severe first-time offenses or persistent rule violations. **Permanent bans** are reserved for egregious violations, credible threats, doxxing, or members with an extensive case history. Unbans are Director-only.\n\n"
                    "### §3.4 Quarantine\n"
                    "Quarantine is used to isolate high-risk members — including in staff-context conflicts — while preserving auditability. Because unquarantine restores saved roles, apply quarantine deliberately and with clear reasoning. Quarantine add is Senior Moderator+; quarantine remove is Director-only.\n\n"
                    "### §3.5 Purge\n"
                    "Purge is Senior Moderator+ and should only be used when cleanup serves moderation, safety, or evidence control needs. Keep reasons specific (spam wave, raid cleanup, slur flood, etc.)."
            ),
        )
        self.add_item(self.container) # type: ignore

class ModerationComponents3(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=
                "## §4 Abuse Prevention and Escalation\n"
                "### §4.1 Rate Limits and Auto-Quarantine\n"
                "Non-Director staff are rate-limited on severe actions including timeouts, kicks, bans, and quarantine adds. Repeated exceedance can trigger automatic quarantine. If rate limits are reached, stop, document, and escalate instead of retrying commands.\n\n"
                "### §4.2 When to Escalate\n"
                "Escalate to a Senior Moderator or Director when:\n"
                "- A situation requires permissions beyond those of a Junior Moderator.\n"
                "- Director-only actions are required (unban, untimeout, quarantine remove, lockdown, cases config).\n"
                "- The target is a staff member or protected role and hierarchy blocks action.\n"
                "- A ticket falls outside Moderator scope, or the Moderator is unsure how to proceed.\n"
                "- A situation is ambiguous, politically sensitive, or rapidly escalating.\n\n"
                "### §4.3 How to Escalate\n"
                "Use `.escalate` within a ticket to redirect it to Directors. For non-ticket situations, contact a Senior Moderator directly or raise the matter in the appropriate staff channel. Do not attempt to resolve a Director-scope ticket independently.\n\n"
                "### §4.4 Ticket Scope\n"
                "**Moderator tickets** handle questions and issues involving members. **Director tickets** handle partnership requests and issues involving staff. If a ticket becomes Director-scope mid-handling, escalate it immediately.\n\n"
                "### §4.5 Lockdown Authority\n"
                "Lockdown is Director-only. Moderators should gather context quickly and alert Directors with concise incident details and affected channels without delay.\n\n"
                "## §5 Moderator Conduct\n"
                "### §5.1 Impartiality\n"
                "Do not take enforcement action in situations where a personal conflict of interest exists. Hand off to another Moderator or escalate to a Senior Moderator or Director immediately.\n\n"
                "### §5.2 Moderation Abuse\n"
                "Abusing permissions for personal gain, retaliation, or to disadvantage a member is grounds for removal from the Moderation Team.\n\n"
                "### §5.3 Conduct Towards Members\n"
                "Moderators must remain calm, factual, and non-antagonistic when enforcing rules. Taunting, baiting, or arguing publicly with disruptive members is not permitted.\n\n"
                "### §5.4 Confidentiality\n"
                "Do not disclose notes, case history, internal deliberations, or internal policy details to non-staff members. This includes revealing that a member has notes on file or the contents of those notes.\n\n"
                "### §5.5 Consistency and Reviewability\n"
                "Use prior notes and cases to keep penalties consistent. Equivalent repeated behavior must not receive the same low-level response indefinitely without escalation. All moderation actions are reviewable by senior staff — be accurate, concise, and objective in every reason and note.\n\n"
                "## §6 Ban Appeals and Reviews\n"
                "### §6.1 Ban Appeals\n"
                "Ban appeals are handled by Directors only via the ticket system. Junior and Senior Moderators must not process them. If a banned member contacts a Moderator directly, direct them to the ticket system and do not engage further.\n\n"
                "### §6.2 Moderation Reviews\n"
                "Enforcement actions may be reviewed by a Senior Moderator or Director at any time. If an action is found unjustified, it may be reversed and the Moderator may receive internal feedback. Reviews are part of maintaining consistent enforcement and must not be taken personally.\n\n"
                "## §7 Expectations and Coordination\n"
                "### §7.1 Activity\n"
                "Moderators are expected to remain reasonably active. Prolonged inactivity without prior notice may result in removal from the Moderation Team at Directorate discretion.\n\n"
                "### §7.2 Communication\n"
                "Communicate openly with the team when handling ongoing situations. Note it in the appropriate staff channel to avoid duplicate handling or conflicting actions.\n\n"
                "### §7.3 Handling Raids\n"
                "In the event of a raid or coordinated disruption, prioritize muting or removing active disruptors immediately, alert Senior Moderators and Directors without delay, and do not engage with raiders in public channels. Document all actions once the situation is resolved. Senior Moderators and Directors will coordinate the broader response."
        ),
    )