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
        "img_url": None # Added for image support
    }

def build_embed(spot):
    embed = discord.Embed(
        title=f"Rank #{spot['num']} - {spot['username']}",
        description=(
            f"**Discord:** {spot['discord']}\n"
            f"**Roblox:** {spot['roblox']}\n"
            f"**Country:** {spot['country']}\n"
            f"**Stage:** {spot['stage']}"
        ),
        color=discord.Color.blue() if spot['username'] != "Vacant" else discord.Color.dark_gray()
    )
    # If you have specific URLs, you can set them here
    if spot.get("img_url"):
        embed.set_image(url=spot["img_url"])
    
    # Example: Setting a generic thumbnail
    embed.set_thumbnail(url="https://i.imgur.com/your_default_icon.png")
    return embed

async def refresh_leaderboard(guild):
    lb = get_lb(guild.id)
    if not lb: return

    channel = guild.get_channel(int(lb["channel_id"]))
    if not channel: return

    spots = lb["spots"]
    message_ids = lb.get("message_ids", [])
    new_ids = []

    # Sort spots by rank number to ensure order
    spots.sort(key=lambda x: x["num"])

    # Discord allows 10 embeds per message
    for index, i in enumerate(range(0, len(spots), 10)):
        batch = spots[i:i+10]
        embeds = [build_embed(s) for s in batch]

        msg = None
        if index < len(message_ids):
            try:
                msg = await channel.fetch_message(int(message_ids[index]))
                await msg.edit(embeds=embeds)
            except discord.NotFound:
                msg = await channel.send(embeds=embeds)
        else:
            msg = await channel.send(embeds=embeds)
        
        new_ids.append(str(msg.id))

    lb["message_ids"] = new_ids
    set_lb(guild.id, lb)

# =========================
# LEADERBOARD COMMANDS
# =========================
@bot.tree.command(name="createlb", description="Initialize the leaderboard")
async def createlb(interaction: discord.Interaction, start: int, end: int):
    await interaction.response.defer(ephemeral=True)
    spots = [vacant_spot(i) for i in range(start, end + 1)]
    set_lb(interaction.guild.id, {
        "channel_id": str(interaction.channel.id),
        "message_ids": [],
        "spots": spots
    })
    await refresh_leaderboard(interaction.guild)
    await interaction.followup.send("Leaderboard created and synced.", ephemeral=True)

@bot.tree.command(name="fillspot", description="Fill a specific rank")
async def fillspot(interaction: discord.Interaction, spot: int, username: str, discord_name: str, roblox: str):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    if not lb: return await interaction.followup.send("No LB found.")

    found = False
    for s in lb["spots"]:
        if s["num"] == spot:
            s.update({"username": username, "discord": discord_name, "roblox": roblox})
            found = True
            break

    if found:
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send(f"Rank {spot} updated.", ephemeral=True)
    else:
        await interaction.followup.send("Spot not found.", ephemeral=True)

@bot.tree.command(name="moveup", description="Move a player up one rank")
async def moveup(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    spots = lb["spots"]
    
    idx = next((i for i, s in enumerate(spots) if s["num"] == spot), None)
    
    if idx is not None and idx > 0:
        # Swap all data EXCEPT the 'num' (rank)
        target_idx = idx - 1
        current_num = spots[idx]["num"]
        target_num = spots[target_idx]["num"]
        
        spots[idx], spots[target_idx] = spots[target_idx], spots[idx]
        
        # Re-assign the correct rank numbers so they don't move with the player
        spots[idx]["num"] = current_num
        spots[target_idx]["num"] = target_num
        
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send(f"Rank {spot} moved up.", ephemeral=True)
    else:
        await interaction.followup.send("Cannot move up further or spot not found.", ephemeral=True)

@bot.tree.command(name="removeplayer", description="Clear a rank")
async def removeplayer(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    if not lb: return
    
    for s in lb["spots"]:
        if s["num"] == spot:
            s.update(vacant_spot(spot))
            break
            
    set_lb(interaction.guild.id, lb)
    await refresh_leaderboard(interaction.guild)
    await interaction.followup.send(f"Cleared spot {spot}.", ephemeral=True)

# =========================
# FLAGS SYSTEM (FIXED)
# =========================
class FlagDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Unlock FPS", value="fps"),
            discord.SelectOption(label="Remove Shadows", value="shadows"),
            discord.SelectOption(label="How to Setup", value="setup"),
        ]
        super().__init__(placeholder="Choose an option...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "setup":
            await interaction.response.send_message("1. Open Roblox Folder\n2. Create `ClientSettings` folder\n3. Create `ClientAppSettings.json` inside.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Selected: {self.values[0]}", ephemeral=True)

class FlagView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Keep it active
        self.add_item(FlagDropdown())

@bot.tree.command(name="flags", description="Show the flags menu")
async def flags(interaction: discord.Interaction):
    embed = discord.Embed(title="Configuration Flags", description="Use the dropdown below to select a utility.", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, view=FlagView(), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

if TOKEN:
    bot.run(TOKEN)
