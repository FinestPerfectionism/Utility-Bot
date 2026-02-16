import discord

class AdministratorsRolesComponents(discord.ui.LayoutView):
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Goobers Administration Team\n"
                "The Goobers Administration Team is responsible for overseeing server management and ensuring that all approved structural or operational changes are properly carried out.\n\n"
                "**Tasks**\n"
                "> *To implement proposals raised by Staff that have reached Accepted status.*\n\n"
                " When a proposal is accepted, an Administrator(s) is expected to implement its proposand. If a proposand is not technically feasible, cannot be executed with current resources, or requires additional refinement, Administrators may place the proposal into Needs Revision, Standstill, or otherwise delay implementation until it becomes feasible."
        ),
        discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.large
        ),
        discord.ui.TextDisplay(
            content=
                "-# **Note:** Administrators are held under the same rules and are expected to also do the same jobs as guild Trustees *and* Moderators. No exceptions."
        ),
        accent_color=0xff8cdf
    )

class ModeratorsRolesComponents(discord.ui.LayoutView):
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Goobers Moderation Team\n"
                "The Goobers Moderation Team is responsible for overseeing rule enforcement, maintaining community safety, and supporting the server's overall stability.\n\n"
                "**Tasks**\n"
                "> *To vote on and raise proposals that improve The Goobers server and its community.*\n\n"
                "All Moderators may raise Staff Proposals and vote on them. Senior Moderators+ may assist in directing or reviewing proposands for clarity or practicality. All proposands are expected to be formal, precise, and beneficial to the server's growth and function."
        ),
        discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.large
        ),
        discord.ui.TextDisplay(
            content=
                "-# **Note:** Moderators are held under the same rules and are expected to also do the same jobs as guild Trustees. No exceptions."
        ),
        accent_color=0x87e9ff
    )

class TrusteeRolesComponents(discord.ui.LayoutView):
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Goobers Guild Trustees\n"
                "Guild Trustees are members of the community who contribute to the server's improvement through proposals and suggestions.\n\n"
                "**Tasks**\n"
                "> *To raise proposals that improve The Goobers server and its community.*\n\n"
                "Guild Trustees may raise Staff Proposals to suggest improvements, changes, or additions to the server. While Trustees can raise proposals. They do not have access to proposal commands and must ask a staff member for assistance. All proposands are expected to be formal, precise, and beneficial to the server's growth and function."
        ),
        accent_color=0xfacd6c
    )

class AdministratorsRoles(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Administrator's Roles",
            custom_id="persistent_administrator_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            view=AdministratorsRolesComponents(),
            ephemeral=True
        )

class ModeratorsRoles(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Moderator's Roles",
            custom_id="persistent_moderator_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            view=ModeratorsRolesComponents(),
            ephemeral=True
        )

class TrusteeRoles(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Trustee's Roles",
            custom_id="persistent_trustee_button"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            view=TrusteeRolesComponents(),
            ephemeral=True
        )

class StaffProposalComponents1(discord.ui.LayoutView):    
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Welcome to Staff Proposals!\n"
                "A branch of the server dedicated to making improvements to the server that will benefit the community and its members."
      ),
  )

class StaffProposalComponents2(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Staff Proposal Information\n"
                "Staff proposals last updated <t:1771213225:D>.\n"
                "-# All below is subject to change at any time based on Directorate decision or structural updates.\n"
                "-# Assembled by the Directorate team. Primarily written by <@1311394031640776716>."
        ),
        discord.ui.Separator(
            visible=False,
            spacing=discord.SeparatorSpacing.small
        ),
        discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.small
        ),
        discord.ui.Separator(
            visible=False,
            spacing=discord.SeparatorSpacing.small
        ),
        discord.ui.TextDisplay(
            content=
                "Any member of the **Goobers Staff Team** (Administrators + Moderators + Directors + Owner) is allowed to vote in a proposal, or raise a proposal. All proposals are expected to be beneficial to the Goobers and its community.\n"
                "## Important Information\n"
                "### Abstaining\n"
                "Abstaining is influenced by the **final** majority vote.\n"
                "- Abstentions do not count as \"for\" or \"against\" during the poll itself.\n"
                "- When the poll ends:\n"
                "  - If the majority is **Accept**, all abstentions are counted as **Accept**.\n"
                "  - If the majority is **Deny**, all abstentions are counted as **Deny**.\n"
                "This applies only when determining the final proposal result.\n"
                "### Staff Count\n"
                "Proposal calculations must adapt to the current Staff count.\n"
                "- **S** = number of Staff voting roles.\n"
                "- **Majority** = ⌈(S / 2) + 1⌉.\n"
                "This updates automatically as Staff size changes.\n"
                "### Inactive or Missing Votes\n"
                "If a proposal cannot reach Majority due to missing Staff votes:\n"
                "- It remains open until the poll expires naturally.\n"
                "- If no Majority is reached by the end, it becomes **Contested**.\n"
                "### Vote Changes\n"
                "- Staff may change their votes at any time before the poll ends.\n"
                "- If a proposal hits a unanimous result during the poll, it ends instantly.\n"
                "- Vote changes are still allowed during a Contested period.\n"
                "- Once a proposal is **Locked**, votes cannot be changed.\n"
                "## Staff Groups\n"
                "**Staff** consists of:\n"
                "- **Owner**\n"
                "- **Directors**\n"
                "- **Administrators**\n"
                "- **Moderators**\n"
                "All Staff are equal in voting ability. Administrators are responsible for implementing accepted proposals.\n"
                "## Poll Format\n"
                "**Motion.**\n"
                "- <:cgreen:1437171496857501889> Accept  \n"
                "- <:cblue:1437171597952811059> Abstain  \n"
                "- <:cred:1437171288631414966> Deny  \n"
                "- <:cyellow:1437171198982357073> Accept, with minor revisions (optional)\n"
                "Poll length must be **three days or longer** if a proposand demands it.\n"
                "## Vetos\n"
                "- **Director Veto:** Any staff member with the Director role may veto a proposal at any time. This veto is absolute and does not require consultation or approval from other Directors or Staff members.  \n"
                "- **Veto Scope:** A veto can be applied to any proposal, regardless of its current vote count or status.  \n"
                "- **Veto Effect:** Once a veto is issued, the proposal is immediately halted and considered denied. Directors may either ask for revision, or end the proposal outright.\n"
                "## Scope\n"
                "While a user could conceivably raise a proposal about anything, Staff are not empowered to make any change they like in staff-proposals. Below is a non-exhaustive list of the types of suggestions that will *not* be considered:\n"
                "- Suggestions that relate to moderator policies or actions such as timeouts or bans.\n"
                "  - Staff may request policy changes if majority (75%) of staff agree on the change. This update may *not* be raised in staff-proposals.\n"
                "- Suggestions pertaining to individual users.\n"
                "- Suggestions that relate to the core rules and guiding philosophy of the server.\n"
                "  - Staff may request rule changes if *all* (100%) of staff agree on the change. The update may *not* be raised in staff-proposals.\n"
                "- Suggestions that relate to updates of staff-proposal-info.\n"
                "Staff may make suggestions to the items listed above __in the appropriate channel__, such as <#1444452435006590996>, <#1386133249373376665>, or <#1436345318554996976>.\n"
                "Guild Trustees may *not* suggest the items listed above anywhere in the server. \n\n"
                "-# **Proposand:** the core idea of a raised proposal.\n"
                "-# **Guild Trustees:** those with the <@&1463694813525180477> role."
        ),
        discord.ui.Separator(
            visible=True,
            spacing=discord.SeparatorSpacing.large
        ),
        discord.ui.ActionRow(
            AdministratorsRoles(),
            ModeratorsRoles(),
            TrusteeRoles()
        ),
    )

class StaffProposalComponents3(discord.ui.LayoutView):   
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Proposal Accepted\n"
                "A proposal is accepted whenever the conditions for acceptance are met.\n"
                "## Acceptance Requirements\n"
                "A proposal becomes **Accepted** if:\n"
                "### 1. Unanimous Accept\n"
                "All Staff who voted choose **Accept**.\n"
                "> Ends immediately.\n"
                "### 2. Majority Accept\n"
                "Accept votes reach the Majority threshold for current Staff size.\n"
                "> Locks only if remaining votes cannot overturn the Majority.\n"
                "### 3. Abstention Adjustment\n"
                "At poll end:\n"
                "- If **Accept** holds the Majority → all abstentions convert to Accept.\n"
                "- Final tally determines acceptance.\n"
                "### 4. Owner Vote\n"
                "- The Owner may vote normally at any time.\n"
                "- The Owner may not override Staff Majority acceptance.\n"
                "### Implementation\n"
                "Administrators implement all accepted proposals. If the proposal requires the Owner or Supporting Director specifically, the relevant tag is used.\n"
                "# Proposal Contested\n"
                "A proposal is Contested whenever its requirements are met.\n"
                "## Contested Requirements\nA proposal becomes **Contested** if:\n"
                "### 1. Tie at Poll End\n"
                "Accept vs Deny are equal after abstention conversion.\n"
                "### 2. No Majority Achieved\n"
                "Neither side reaches Majority by the end of the poll.\n"
                "### Contested Period\n"
                "A **3-day discussion period** begins.\n"
                "- Staff may revise votes.\n"
                "- If Majority forms, the proposal resolves immediately.\n"
                "### After 3 Days\n"
                "If still no Majority:\n"
                "- The **Owner** casts a final deciding vote.\n"
                "- The Owner's vote determines Accepted or Denied.\n"
                "The Owner cannot override a Staff Majority at any time.\n"
                "# Proposal Denied\n"
                "A proposal is denied whenever the requirements for denial are met.\n"
                "## Denial Requirements\n"
                "A proposal becomes **Denied** if:\n"
                "### 1. Unanimous Deny\n"
                "All Staff who voted choose **Deny**.\n"
                "> Ends immediately.\n"
                "### 2. Majority Deny\n"
                "Deny votes reach Majority.\n"
                "> Locks only if remaining votes cannot overturn the Majority.\n"
                "### 3. Abstention Adjustment\n"
                "At poll end:\n"
                "- If **Deny** holds the Majority → all abstentions convert to Deny.\n- Final tally determines denial.\n"
                "### 4. Owner Vote\n"
                "- The Owner may vote normally at any time.\n"
                "- The Owner may not override Staff Majority denial.\n"
                "# Proposal Standstill\n"
                "The **Standstill** status is used only for rare, special circumstances. This status is not triggered automatically and must be entered manually by a staff member.\n"
                "## Standstill Conditions\n"
                "A proposal may enter Standstill if:\n"
                "- Motion and votes conflict severely.\n"
                "- Staff statements contradict each other.\n"
                "- The proposal becomes halted for administrative, technical, or logistical reasons.\n"
                "- The situation is too mixed to evaluate.\n"
                "- Staff explicitly decide that normal evaluation cannot proceed.\n"
                "Standstill is a Staff decision, not a vote threshold. A proposal must exit Standstill before any final status (Accepted, Contested, Denied) is applied."
        ),
    )

class StaffProposalComponents4(discord.ui.LayoutView):   
    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=
                "# Non-Status Tags\n"
                "## NEEDS REVISION\n"
                "Used when a proposal receives positive motion, but  Administrator(s) state implementation is not possible in its current form, or, when Directors veto a proposal and the original poster chooses to rewrite.\n"
                "**Rules:**\n"
                "- A proposal **cannot be locked** while marked Needs Revision.\n"
                "- OP must revise the proposand.\n"
                "- After revision, the proposal restarts evaluation.\n"
                "## NEEDS IMPLEMENTATION\n"
                "Used only **after** a proposal is accepted.\n"    
                "**Rules:**\n"
                "- A proposal **cannot be locked** until Administrators implement the proposand.\n"
                "- Tag is removed once implementation is complete.\n"
                "## OWNER ACTION\n"    
                "Used for cases where:\n"
                "- Only the Owner can implement a proposal's requirements.\n"    
                "Does not affect vote mechanics.\n"
                "## S. DIRECTOR ACTION\n"    
                "Used for cases where:\n"
                "- Only a Supporting Director can implement a proposal's requirements.\n"
                "Does not affect vote mechanics.\n"
                "## LOCKED\nA proposal is **Locked** when:\n"
                "- Its result is final **and**\n"
                "- The proposand has been implemented.\n"
                "Moderators may still send messages, but a Locked proposal shouldn't be changed or reopened unless more discussion on the topic is necessary or new issues have arisen."
        ),
    )