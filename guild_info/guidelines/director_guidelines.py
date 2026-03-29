import discord

class DirectorateComponents1(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=
                "# Welcome to Directorate Guidelines!\n"
                "Internal guidelines for the Goobers Directorate.\n"
                "-# **Note:** These guidelines are Directorate-only and may be revised at any time by Directorate decision. They apply to all Directors regardless of rank. Sharing internal Directorate policy outside authorized spaces is prohibited."
        ),
    )

class DirectorateComponents2(discord.ui.LayoutView):
    def __init__(self, timestamp: int) -> None:
        super().__init__(timeout = None)
        self.container = discord.ui.Container( # type: ignore
            discord.ui.TextDisplay( # type: ignore
                content=
                    "# Directorate Guidelines\n"
                   f"Directorate guidelines last updated <t:{timestamp}:D>.\n"
                    "-# All below is subject to change at any time based on Directorate decision or structural updates.\n"
                    "-# Assembled by the Directorate team. Primarily written by <@1311394031640776716>.\n"
            ),
            discord.ui.Separator( # type: ignore
                visible = False,
                spacing = discord.SeparatorSpacing.small
            ),
            discord.ui.Separator( # type: ignore
                visible = True,
                spacing = discord.SeparatorSpacing.small
            ),
            discord.ui.Separator( # type: ignore
                visible = False,
                spacing = discord.SeparatorSpacing.small
            ),
            discord.ui.TextDisplay( # type: ignore
                content=
                    "## §1 Directorate Authority\n"
                    "The Directorate holds ultimate governance authority over the server. All staff teams operate under Directorate oversight. Directorate decisions are final and binding unless revisited by the Directorate itself.\n\n"
                    "### §1.1 Leading Director\n"
                    "The Leading Director is the true owner of the server and holds ultimate authority over all operations and governance decisions. No decision — including those made collectively by Supporting Directors — may override the Leading Director's determination. The Leading Director is not obligated to provide justification to other Directors when overruling a decision, though doing so is encouraged for internal clarity.\n\n"
                    "### §1.2 Supporting Directors\n"
                    "Supporting Directors assist in governance, participate in the Staff Committee, and hold Senior Staff status in both the Moderation and Administration Teams. Supporting Directors act with full Directorate authority in their own right, subject to the Leading Director's supremacy. When the Leading Director is unavailable, Supporting Directors are expected to handle escalated matters collectively.\n\n"
                    "### §1.3 Senior Staff Status\n"
                    "All Directors hold Senior Staff status within both the Moderation and Administration Teams. This authorizes Directors to execute the full permission set of Senior Moderators and Senior Administrators when the situation demands it. This authority exists for escalated intervention — not to supplant the frontline work of the Moderation and Administration Teams in routine situations.\n\n"
                    "### §1.4 Directorate as a Governing Body\n"
                    "On matters of internal policy, staff appointments, partnership decisions, and escalated enforcement, the Directorate acts as a body. Supporting Directors are expected to communicate and align before issuing decisions that affect the wider staff team or the public. Unilateral decisions by a Supporting Director on major governance matters should be the exception, not the norm.\n\n"
                    "## §2 Staff Committee\n"
                    "Directors form the core of the Staff Committee. A thorough understanding of the committee's process is required of all Directors. For full procedural details, refer to the staff proposal information.\n\n"
                    "### §2.1 Composition and Quorum\n"
                    "The Staff Committee is composed of all active Directors and the Owner. A quorum of at least two committee members is required to issue any final decision. Directors who are inactive or unavailable during a review window do not prevent a quorum from forming, provided the minimum threshold is met.\n\n"
                    "### §2.2 Decisions and Deliberation\n"
                    "A simple majority of present committee members is sufficient to issue Accept, Accept with minor revisions, or Deny decisions. Standstill and Contested status require unanimous agreement among present members. Directors are expected to review all vote data and staff discussion before issuing a decision — not only the poll totals.\n\n"
                    "### §2.3 Directorate-Review Proposals\n"
                    "Certain proposals bypass the standard Staff Committee process and are routed directly to the Directorate for internal review. This applies to matters where the nature of the proposal falls outside the scope of staff advisory voting — most notably, the addition or removal of bots. When a proposal enters Directorate review, the Directorate deliberates internally and issues a decision at their discretion. Normal veto, revision, and standstill mechanics still apply.\n\n"
                    "### §2.4 Review Timeline\n"
                    "The Staff Committee must issue a final decision within 5 days of the advisory poll concluding. If no decision is reached, the proposal automatically enters Contested status. Directors are responsible for ensuring this window is respected — delays without cause reflect on the Directorate."
            ),
        )
        self.add_item(self.container) # type: ignore

class DirectorateComponents3(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=
                "## §3 Nominations and Promotions\n"
                "All appointment and promotion decisions are made internally by the Directorate. Senior Staff members may provide information or advice regarding Junior Staff candidates, but such input is non-binding. The final decision rests entirely with the Directorate.\n\n"
                "### §3.1 Director Nominations\n"
                "Director nominations require **unanimous agreement** from the existing Directorate. A single objection from any Director is sufficient to prevent a nomination from proceeding. Director nominations are only made under special circumstances and must not be treated as a routine reward for strong performance.\n\n"
                "### §3.2 Junior to Senior Promotions\n"
                "Promoting a Junior staff member (Junior Moderator or Junior Administrator) to their Senior counterpart requires that **at least ²⁄₃ of Directors accept**, with the remaining Directors either accepting or abstaining. A Director actively opposing the promotion is sufficient to prevent it from meeting threshold.\n\n"
                "### §3.3 Member to Junior Staff\n"
                "Bringing a member into the staff team as a Junior Moderator or Junior Administrator requires that **at least ¹⁄₃ of Directors accept**, with the remaining Directors either accepting or abstaining. This lower threshold reflects the trial nature of Junior positions.\n\n"
                "### §3.4 Guild Trustee Nominations\n"
                "Nominating a member to the Guild Trustee role requires that **all Directors abstain or accept** — no Director may actively oppose the nomination for it to proceed. Because Guild Trustees are not staff, the threshold is deliberately permissive, but the role must not be awarded without consensus.\n\n"
                "### §3.5 Removals\n"
                "Any Director may initiate the removal of a staff member from their role. Removal of Junior staff may be actioned unilaterally by a Director in cases of clear and immediate misconduct. For Senior staff and above, removal should be discussed with the wider Directorate before action is taken except in circumstances requiring immediate intervention. All removals must be documented internally.\n\n"
                "## §4 Veto Powers\n"
                "Any Director may veto a Staff Proposal at any time before the Staff Committee issues a final decision. A veto is absolute, requires no approval from other Directors or staff, and immediately halts the proposal.\n\n"
                "### §4.1 Appropriate Use\n"
                "A veto should be exercised when a proposal poses a clear risk to server stability, violates policy, is technically unworkable, or where the Director has substantive grounds that the proposal should not proceed in its current form. A veto is not an appropriate tool for expressing a preference or disagreement with a proposal's direction absent substantive concerns — in those cases, voting Deny in the advisory poll or engaging in staff discussion is the appropriate avenue.\n\n"
                "### §4.2 Director Accountability\n"
                "Directors are accountable for their vetoes. While justification is not formally required, Directors are strongly expected to provide brief reasoning when vetoing — particularly when acting contrary to a strong staff consensus. Vetoes issued without explanation against overwhelming staff support should be rare and reserved for serious concerns. A pattern of unexplained vetoes contrary to staff consensus reflects poorly on the Directorate as a body.\n\n"
                "### §4.3 Post-Veto Options\n"
                "After a veto is issued, the Director may either request revision from the proposer — in which case the proposal enters NEEDS REVISION — or end the proposal outright. The Director must communicate which outcome applies."
        ),
    )

class DirectorateComponents4(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=
                "## §5 Director Tickets\n"
                "Directors are responsible for all tickets escalated to Director scope. This includes ban appeals, partnership requests, and issues involving staff members.\n\n"
                "### §5.1 Ban Appeals\n"
                "Banned members may appeal only through the official ticket system. Junior and Senior Moderators must not process ban appeals and should direct any banned member who contacts them to the ticket system without further engagement.\n\n"
                "When reviewing a ban appeal, Directors must:\n"
                "- Review the full case history for the banned member before responding.\n"
                "- Consider the severity of the original offense, time elapsed, and whether the ban remains proportionate.\n"
                "- Reach a decision collectively where possible. A single Director may issue a decision, but contentious appeals should involve wider Directorate input.\n"
                "- Communicate the outcome clearly within the ticket. Reasons for denial are not required but should be provided where doing so does not compromise internal information.\n"
                "- Document the outcome internally.\n\n"
                "Appeals may be denied outright, granted resulting in an unban, or granted with conditions such as a probationary period. Unbans may only be executed by Directors.\n\n"
                "### §5.2 Partnership Requests\n"
                "All partnership requests must arrive via the official ticket system. Moderators receiving a partnership request should escalate it to Directors using `.escalate` without processing it themselves.\n\n"
                "When reviewing a partnership request, Directors must:\n"
                "- Review the requesting server against the Partnership Requirements.\n"
                "- Assess eligibility, activity, and whether the partnership would be mutually beneficial.\n"
                "- Reach a decision collectively. No single Director may independently approve or promise a partnership.\n"
                "- Communicate the outcome within the ticket. Reasons for denial are not required.\n\n"
                "If approved, Directors must communicate terms within the ticket and direct authorized staff to carry out implementation. Partnership decisions are entirely at Directorate discretion and are not subject to staff advisory voting.\n\n"
                "### §5.3 Staff Issue Tickets\n"
                "Tickets involving staff members — whether raised by a member against a staff member, or by a staff member against another — are Director-scope and must not be handled by Junior or Senior Moderators. If a Moderator receives a ticket that implicates staff conduct, it must be escalated to Directors via `.escalate` immediately without further engagement.\n\n"
                "When reviewing a staff issue ticket, Directors must:\n"
                "- Review available context, including case history and any prior internal records relating to the staff member involved.\n"
                "- Approach the review impartially. A Director with a direct personal stake in the outcome should recuse themselves and defer to the remaining Directorate.\n"
                "- Reach a decision collectively where the situation is serious. Minor issues may be resolved at a single Director's discretion.\n"
                "- Communicate the outcome clearly within the ticket where appropriate, without disclosing internal deliberations.\n"
                "- Document all findings and outcomes internally.\n\n"
                "If a staff issue ticket reveals potential misconduct, it must be escalated to full internal review under §6."
        ),
    )

class DirectorateComponents5(discord.ui.LayoutView):
    container = discord.ui.Container( # type: ignore
        discord.ui.TextDisplay( # type: ignore
            content=
                "## §6 Staff Misconduct\n"
                "### §6.1 What Constitutes Misconduct\n"
                "Staff misconduct includes: abuse of permissions, harassment of members or colleagues, breaching confidentiality, acting outside authorized scope, sustained bad-faith behavior, and actions that damage the server's reputation or operation. Misconduct is not limited to formal enforcement actions — it encompasses any conduct incompatible with holding a staff role.\n\n"
                "### §6.2 Handling Misconduct\n"
                "Directors are the sole body authorized to formally investigate and sanction staff misconduct. When misconduct is identified or reported, the relevant Director(s) should:\n"
                "- Review the situation with all available context before acting.\n"
                "- Consult the wider Directorate before issuing formal consequences where time allows.\n"
                "- Act decisively in cases requiring immediate containment — quarantine is available for high-risk situations.\n"
                "- Communicate outcomes to the affected staff member directly.\n\n"
                "### §6.3 Director Misconduct\n"
                "A Director who acts in bad faith, abuses their authority, or engages in conduct incompatible with the role is subject to review by the remaining Directorate. The Leading Director holds final authority over any action taken against a Supporting Director. There is no formal appeal process for Directorate decisions regarding Director conduct.\n\n"
                "## §7 Quarantine Management\n"
                "Quarantine is the primary tool for isolating high-risk or disruptive members pending review. Directors are the only staff authorized to remove quarantine.\n\n"
                "When a member is quarantined, Directors must review the situation promptly. Resolution options include: lifting quarantine and taking no further action, lifting quarantine and issuing a formal enforcement action, maintaining quarantine pending further review, or proceeding to a ban. Because unquarantine restores saved roles, the decision must be deliberate and documented.\n\n"
                "## §8 Internal Disagreements\n"
                "### §8.1 Between Supporting Directors\n"
                "Disagreements between Supporting Directors should be resolved through internal discussion. Directors are expected to approach disagreements in good faith and seek a workable consensus. Disagreements must not be aired in staff channels or public spaces.\n\n"
                "### §8.2 Leading Director Resolution\n"
                "If Supporting Directors reach a genuine impasse, the matter may be referred to the Leading Director for a final determination. The Leading Director's decision resolves the disagreement and may not be overruled by Supporting Directors.\n\n"
                "## §9 Directorate Conduct and Expectations\n"
                "### §9.1 Authority with Accountability\n"
                "The authority the Directorate holds exists to serve the server. It must not be exercised arbitrarily, for personal benefit, or to advantage or disadvantage any member or staff colleague. Directors are held to the same shared conduct standards as all staff and are not exempt from them by virtue of their rank.\n\n"
                "### §9.2 Transparency to Staff\n"
                "Directors are not required to disclose internal deliberations, but should communicate decisions clearly and promptly to staff where the decision affects them. Staff should not learn of significant governance changes through inference.\n\n"
                "### §9.3 Activity and Availability\n"
                "Directors are expected to remain active and responsive, particularly to escalated tickets, contested proposals, and staff misconduct reports. Prolonged unavailability without notice is not acceptable at the Directorate level. If a Director anticipates extended absence, the wider Directorate must be informed in advance."
        ),
    )