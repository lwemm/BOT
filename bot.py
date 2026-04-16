from keep_alive import keep_alive
import os
from dotenv import load_dotenv 
load_dotenv()

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import Modal, TextInput

# -------------------- IDs -------------------- #
TEAM_ROLE_IDS = [
    1485699791836151962,
    1485700243738857552,
    1485700500522406000,
    1485700579580973239,
    1485700661533216909,
    1485700740612882706
]

GUILD_ID = 1483784922702549203
TRANSFERS_CHANNEL_ID = 1483857219090124801
RESULTS_CHANNEL_ID = 1483844409526063215
SANCTIONS_CHANNEL_ID = 1483845670115868812

MAX_PLAYERS = 10
MANAGER_ROLE_ID = 1483846177727185039
ASSISTANT_MANAGER_ROLE_ID = 1483846126816985220
REFEREE_ROLE_ID = 1483846048815513823

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# -------------------- Bot Ready -------------------- #
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    print("Bot ready")

# -------------------- Checks -------------------- #
def manager_only():
    async def predicate(interaction: Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            return False
        allowed_roles = [MANAGER_ROLE_ID, ASSISTANT_MANAGER_ROLE_ID]
        return any(role.id in allowed_roles for role in member.roles)
    return app_commands.check(predicate)

# -------------------- Offer View -------------------- #
class OfferView(discord.ui.View):
    def __init__(self, team_role: discord.Role, player: discord.Member):
        super().__init__(timeout=None)
        self.team_role = team_role
        self.player = player

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.player.id:
            await interaction.followup.send("This offer is not for you.")
            return

        if len(self.team_role.members) >= MAX_PLAYERS:
            await interaction.followup.send("Squad is full.")
            return

        await self.player.add_roles(self.team_role)
        await interaction.followup.send(f"You joined {self.team_role.name}.")

        channel = bot.get_channel(TRANSFERS_CHANNEL_ID)
        if channel:
            count = len(self.team_role.members)
            embed = discord.Embed(
                title="Offer Accepted",
                description=f"**{self.player.display_name}** has signed for **{self.team_role.name}**.\nSquad size: {count}/{MAX_PLAYERS}",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)

        self.stop()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != self.player.id:
            await interaction.followup.send("This offer is not for you.")
            return

        await interaction.followup.send("You rejected the offer.")
        self.stop()

# -------------------- Commands -------------------- #
@tree.command(name="offer")
@manager_only()
async def offer(interaction: discord.Interaction, player: discord.Member):
    await interaction.response.defer(ephemeral=True)

    manager = interaction.user
    team_role = next((r for r in manager.roles if r.id in TEAM_ROLE_IDS), None)

    if not team_role:
        await interaction.followup.send("You do not have a team role.")
        return

    if len(team_role.members) >= MAX_PLAYERS:
        await interaction.followup.send("Your squad is full.")
        return

    embed = discord.Embed(
        title="📄 Transfer Offer",
        description=f"{team_role.name} has sent you a transfer offer.\nDo you accept?",
        color=discord.Color.green()
    )

    try:
        await player.send(embed=embed, view=OfferView(team_role, player))
        await interaction.followup.send(f"Offer sent to {player.display_name}.")
    except:
        await interaction.followup.send("Player's DMs are closed.")

@tree.command(name="release")
@manager_only()
async def release(interaction: discord.Interaction, player: discord.Member):
    await interaction.response.defer(ephemeral=True)

    manager = interaction.user
    team_role = next((r for r in manager.roles if r.id in TEAM_ROLE_IDS), None)

    if not team_role:
        await interaction.followup.send("You do not have a team role.")
        return

    if team_role not in player.roles:
        await interaction.followup.send("Player is not in your team.")
        return

    await player.remove_roles(team_role)
    await interaction.followup.send(f"{player.display_name} released from {team_role.name}.")

# -------------------- MATCHDAY (FIXED) -------------------- #
@tree.command(name="matchday")
@app_commands.describe(
    manager="Select manager",
    team="Select team role",
    timestamp="Match time as Unix timestamp"
)
async def matchday(interaction: discord.Interaction, manager: discord.Member, team: discord.Role, timestamp: int):
    await interaction.response.defer(ephemeral=True)

    if not any(role.id == MANAGER_ROLE_ID for role in manager.roles):
        await interaction.followup.send("Selected user is not a manager.")
        return

    if team.id not in TEAM_ROLE_IDS:
        await interaction.followup.send("Invalid team role.")
        return

    # 🔥 FIX: ms girilirse otomatik düzelt
    if timestamp > 9999999999:
        timestamp = int(timestamp / 1000)

    sent = 0

    for member in team.members:
        try:
            await member.send(
                f"Match Reminder\n\nYou have a match today at <t:{timestamp}:f>.\nPlease prepare your team and be ready."
            )
            sent += 1
        except:
            continue

    await interaction.followup.send(
        f"Notification sent to {sent} players from {team.name}."
    )

# -------------------- SANCTION -------------------- #
@tree.command(name="sanction")
@app_commands.describe(player="Player", bail="Bail", reason="Reason", duration="Duration")
@app_commands.choices(bail=[
    app_commands.Choice(name="200", value="200"),
    app_commands.Choice(name="400", value="400"),
    app_commands.Choice(name="600", value="600"),
    app_commands.Choice(name="1000", value="1000"),
    app_commands.Choice(name="1500", value="1500"),
    app_commands.Choice(name="2000", value="2000"),
    app_commands.Choice(name="2500", value="2500"),
    app_commands.Choice(name="3000", value="3000"),
    app_commands.Choice(name="3500", value="3500"),
])
async def sanction(interaction: discord.Interaction, player: discord.Member, bail: app_commands.Choice[str], reason: str, duration: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    channel = bot.get_channel(SANCTIONS_CHANNEL_ID)

    embed = discord.Embed(title="WL SANCTION", color=discord.Color.red())
    embed.add_field(name="Player Got Suspended", value=player.mention, inline=False)
    embed.add_field(name="Bail", value=bail.value, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Duration", value=duration, inline=False)

    await channel.send(embed=embed)
    await interaction.response.send_message("Done.", ephemeral=True)

# -------------------- RUN --------------------
token = os.getenv('DISCORD_TOKEN')
keep_alive()
bot.run(token)
