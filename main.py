import discord
from discord import app_commands
from discord.ext import commands
import os
import json

TOKEN = os.getenv("DISCORD_TOKEN")
LB_FILE = "leaderboards.json"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# FILE HANDLING
# =========================
def load_lb():
    if not os.path.exists(LB_FILE):
        return {}
    with open(LB_FILE, "r") as f:
        return json.load(f)

def save_lb(data):
    with open(LB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_lb(guild_id):
    return load_lb().get(str(guild_id))

def set_lb(guild_id, data):
    all_lb = load_lb()
    all_lb[str(guild_id)] = data
    save_lb(all_lb)

# =========================
# LEADERBOARD SYSTEM
# =========================
def vacant_spot(num):
    return {
        "num": num,
        "username": "Vacant",
        "discord": "Vacant",
        "roblox": "None",
        "country": "None",
        "stage": "None",
    }

def build_embed(spot):
    return discord.Embed(
        title=f"{spot['num']} - {spot['username']}",
        description=(
            f"Discord: {spot['discord']}\n"
            f"Roblox: {spot['roblox']}\n"
            f"Country: {spot['country']}\n"
            f"Stage: {spot['stage']}"
        ),
        color=discord.Color.dark_gray()
    )

async def refresh_leaderboard(guild):
    lb = get_lb(guild.id)
    if not lb:
        return

    channel = guild.get_channel(int(lb["channel_id"]))
    if not channel:
        return

    spots = lb["spots"]
    message_ids = lb.get("message_ids", [])
    new_ids = []

    for index, i in enumerate(range(0, len(spots), 10)):
        embeds = [build_embed(s) for s in spots[i:i+10]]

        if index < len(message_ids):
            try:
                msg = await channel.fetch_message(int(message_ids[index]))
                await msg.edit(embeds=embeds)
                new_ids.append(str(msg.id))
                continue
            except:
                pass

        msg = await channel.send(embeds=embeds)
        new_ids.append(str(msg.id))

    lb["message_ids"] = new_ids
    set_lb(guild.id, lb)

# =========================
# LEADERBOARD COMMANDS
# =========================
@bot.tree.command(name="createlb")
async def createlb(interaction: discord.Interaction, start: int, end: int):
    await interaction.response.defer(ephemeral=True)

    spots = [vacant_spot(i) for i in range(start, end + 1)]

    set_lb(interaction.guild.id, {
        "channel_id": str(interaction.channel.id),
        "message_ids": [],
        "spots": spots
    })

    await interaction.followup.send("Leaderboard created.", ephemeral=True)
    await refresh_leaderboard(interaction.guild)

@bot.tree.command(name="fillspot")
async def fillspot(interaction: discord.Interaction, spot: int, username: str, discord_name: str, roblox: str):
    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    if not lb:
        return await interaction.followup.send("No leaderboard.", ephemeral=True)

    for s in lb["spots"]:
        if s["num"] == spot:
            s["username"] = username
            s["discord"] = discord_name
            s["roblox"] = roblox

    set_lb(interaction.guild.id, lb)
    await interaction.followup.send("Updated.", ephemeral=True)
    await refresh_leaderboard(interaction.guild)

@bot.tree.command(name="moveup")
async def moveup(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    spots = lb["spots"]

    for i in range(len(spots)):
        if spots[i]["num"] == spot and i > 0:
            spots[i], spots[i-1] = spots[i-1], spots[i]
            break

    set_lb(interaction.guild.id, lb)
    await refresh_leaderboard(interaction.guild)
    await interaction.followup.send("Moved up.", ephemeral=True)

@bot.tree.command(name="movedown")
async def movedown(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    spots = lb["spots"]

    for i in range(len(spots)):
        if spots[i]["num"] == spot and i < len(spots)-1:
            spots[i], spots[i+1] = spots[i+1], spots[i]
            break

    set_lb(interaction.guild.id, lb)
    await refresh_leaderboard(interaction.guild)
    await interaction.followup.send("Moved down.", ephemeral=True)

# =========================
# FLAGS SYSTEM
# =========================
class FlagDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Unlock FPS"),
            discord.SelectOption(label="Remove Shadows"),
            discord.SelectOption(label="Disable Post Process"),
            discord.SelectOption(label="How to Setup"),
        ]
        super().__init__(placeholder="Choose a flag...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "How to Setup":
            await interaction.response.send_message(
                "Go to Roblox folder → create ClientSettings → add json file.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Flag selected: {self.values[0]}",
                ephemeral=True
            )

class FlagView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(FlagDropdown())

@bot.tree.command(name="flags")
async def flags(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Flags Menu",
        description="Select a flag below",
        color=discord.Color.black()
    )
    await interaction.response.send_message(embed=embed, view=FlagView(), ephemeral=True)

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# =========================
# RUN
# =========================
if TOKEN:
    bot.run(TOKEN)
else:
    print("No token found")
