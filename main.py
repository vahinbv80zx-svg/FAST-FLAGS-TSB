import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# --- CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
LB_FILE = "leaderboards.json"
HEADER_GIF = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377599662755931/WHITE-1.gif?ex=69e9a9bd&is=69e8583d&hm=cae7913688d5a686d7d1da1248509c23b11bacf17387fef4a9d546e6ae9874a7&"
VACANT_THUMB = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377629501030400/Black_question_mark.png?ex=69e9a9c4&is=69e85844&hm=c5f1e8c59fb5aff7c11f84e43133b22c7785163c20b0c150b5caf04095e32eb6&"

# --- DATA PERSISTENCE HELPERS ---
def get_lb(guild_id):
    if not os.path.exists(LB_FILE): return {}
    with open(LB_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(guild_id))

def set_lb(guild_id, lb_data):
    data = {}
    if os.path.exists(LB_FILE):
        with open(LB_FILE, "r") as f:
            data = json.load(f)
    data[str(guild_id)] = lb_data
    with open(LB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def vacant_spot(n):
    return {
        "num": n, "username": "Vacant", "discord": "None",
        "roblox": "None", "country": "None", "stage": "None",
        "thumbnail": None, "vacant": True
    }

def has_permission(interaction):
    return interaction.user.guild_permissions.administrator

# --- BOT CLASS SETUP ---
class IntegratedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # This syncs ALL commands attached to this bot instance
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} | Commands Synced Successfully")

bot = IntegratedBot()

# ---------- LEADERBOARD LOGIC ----------
def build_spot_embed(spot):
    desc = (
        f"| `{spot['discord']}` |\n"
        f"«« | • {spot['roblox']} • | »»\n"
        f"**Country :** {spot['country']}\n"
        f"**Stage :** {spot['stage']}"
    )
    embed = discord.Embed(title=f"{spot['num']} - {spot['username']}", description=desc, color=0x2B2D31)
    embed.set_image(url=HEADER_GIF)
    embed.set_thumbnail(url=spot.get("thumbnail") or VACANT_THUMB)
    return embed

async def refresh_leaderboard(guild: discord.Guild):
    lb = get_lb(guild.id)
    if not lb: return
    channel = guild.get_channel(int(lb["channel_id"]))
    if not channel: return
    
    for mid in lb.get("message_ids", []):
        try:
            msg = await channel.fetch_message(int(mid))
            await msg.delete()
        except: pass
            
    spots = lb["spots"]
    new_ids = []
    for i in range(0, len(spots), 10):
        embeds = [build_spot_embed(s) for s in spots[i:i+10]]
        msg = await channel.send(embeds=embeds)
        new_ids.append(str(msg.id))
        
    lb["message_ids"] = new_ids
    set_lb(guild.id, lb)

# ---------- LEADERBOARD COMMANDS ----------
@bot.tree.command(name="createlb", description="Create a leaderboard.")
async def createlb_cmd(interaction: discord.Interaction, spot_range: str, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission."); return
    try:
        a, b = spot_range.split("-")
        start, end = int(a.strip()), int(b.strip())
    except:
        await interaction.followup.send("❌ Invalid range (e.g. 1-10)."); return

    spots = [vacant_spot(n) for n in range(start, end + 1)]
    set_lb(interaction.guild.id, {"channel_id": str(channel.id), "message_ids": [], "spots": spots})
    await interaction.followup.send(f"✅ Leaderboard created in {channel.mention}.")
    asyncio.create_task(refresh_leaderboard(interaction.guild))

@bot.tree.command(name="fillspot", description="Fill a leaderboard spot")
async def fillspot_cmd(interaction: discord.Interaction, spot: int, username: str, discord_handle: str, roblox: str, country: str, stage: str, thumbnail_url: str):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission."); return
    lb = get_lb(interaction.guild.id)
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None) if lb else None
    if idx is None:
        await interaction.followup.send("❌ Spot not found."); return
    
    lb["spots"][idx] = {
        "num": spot, "username": username, "discord": discord_handle,
        "roblox": roblox, "country": country, "stage": stage,
        "thumbnail": thumbnail_url, "vacant": False,
    }
    set_lb(interaction.guild.id, lb)
    await interaction.followup.send(f"✅ Spot {spot} updated.")
    asyncio.create_task(refresh_leaderboard(interaction.guild))

# ---------- FLAG OPTIMIZATION LOGIC ----------
class FlagDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Unlock FPS", description="DFIntTaskSchedulerTargetFps"),
            discord.SelectOption(label="Remove Shadows", description="FIntRenderShadowIntensity"),
            discord.SelectOption(label="How to Setup", description="Installation guide for flags"),
        ] # Add your other options here as needed
        super().__init__(placeholder="Choose a legal flag...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        if selection == "How to Setup":
            content = "1. Go to %LocalAppData%\\Roblox\\Versions\n2. Open latest version folder\n3. Create ClientSettings folder\n4. Create ClientAppSettings.json inside."
        else:
            content = f"Code for {selection}: 
http://googleusercontent.com/immersive_entry_chip/0

### What was fixed:
* **Variable Overwriting:** Removed the second `bot = FlagBot()` which was deleting your leaderboard commands.
* **Unified Intents:** Combined the required intents (members and guilds) into one place.
* **Persistent Storage Helpers:** Added the `get_lb`, `set_lb`, and `vacant_spot` functions. Without these, your script would have crashed with a `NameError` the moment you tried to use `/createlb`.
* **Synced Setup:** Used `IntegratedBot.setup_hook` to ensure that every time the bot starts on Railway, it tells Discord about **every** command in the script at once.
