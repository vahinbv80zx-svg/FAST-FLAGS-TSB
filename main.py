import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# --- CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
LB_FILE = "leaderboards.json"
HEADER_GIF = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377599662755931/WHITE-1.gif"
VACANT_THUMB = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377629501030400/Black_question_mark.png"

# --- DATA HELPERS ---
def get_lb(guild_id):
    if not os.path.exists(LB_FILE): return None
    try:
        with open(LB_FILE, "r") as f:
            return json.load(f).get(str(guild_id))
    except: return None

def set_lb(guild_id, lb_data):
    data = {}
    if os.path.exists(LB_FILE):
        try:
            with open(LB_FILE, "r") as f: data = json.load(f)
        except: pass
    data[str(guild_id)] = lb_data
    with open(LB_FILE, "w") as f: json.dump(data, f, indent=4)

def vacant_spot(n):
    return {"num": n, "username": "Vacant", "discord": "None", "roblox": "None", "country": "None", "stage": "None", "thumbnail": None, "vacant": True}

# --- BOT SETUP ---
class IntegratedBot(commands.Bot):
    def __init__(self):
        # Using all intents for maximum compatibility
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = IntegratedBot()

# --- REFRESH LOGIC ---
async def refresh_leaderboard(guild: discord.Guild):
    lb = get_lb(guild.id)
    if not lb: return
    channel = guild.get_channel(int(lb["channel_id"]))
    if not channel: return
    
    spots = lb["spots"]
    message_ids = lb.get("message_ids", [])
    new_ids = []
    
    needed = (len(spots) + 9) // 10
    
    for i in range(needed):
        group = spots[i*10:(i+10)]
        embeds = []
        for s in group:
            desc = f"| `{s['discord']}` |\n«« | • {s['roblox']} • | »»\n**Country :** {s['country']}\n**Stage :** {s['stage']}"
            e = discord.Embed(title=f"{s['num']} - {s['username']}", description=desc, color=0x2B2D31)
            e.set_image(url=HEADER_GIF)
            e.set_thumbnail(url=s.get("thumbnail") or VACANT_THUMB)
            embeds.append(e)

        msg = None
        # Try to find and edit existing message
        if i < len(message_ids):
            try:
                msg = await channel.fetch_message(int(message_ids[i]))
                await msg.edit(embeds=embeds)
            except:
                msg = await channel.send(embeds=embeds)
        else:
            msg = await channel.send(embeds=embeds)
            
        if msg: new_ids.append(str(msg.id))
        
    lb["message_ids"] = new_ids
    set_lb(guild.id, lb)

# --- LEADERBOARD COMMANDS ---
@bot.tree.command(name="createlb", description="Initialize the leaderboard")
async def createlb(interaction: discord.Interaction, spot_range: str, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    try:
        start, end = map(int, spot_range.split("-"))
        spots = [vacant_spot(n) for n in range(start, end + 1)]
        set_lb(interaction.guild.id, {"channel_id": str(channel.id), "message_ids": [], "spots": spots})
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send("✅ Leaderboard Created.")
    except:
        await interaction.followup.send("❌ Format: 1-10")

@bot.tree.command(name="fillspot", description="Fill a player spot")
async def fillspot(interaction: discord.Interaction, spot: int, username: str, discord_handle: str, roblox: str, country: str, stage: str, thumbnail_url: str):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    if not lb:
        return await interaction.followup.send("❌ Use /createlb first.")
        
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None:
        lb["spots"][idx] = {"num": spot, "username": username, "discord": discord_handle, "roblox": roblox, "country": country, "stage": stage, "thumbnail": thumbnail_url, "vacant": False}
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send(f"✅ Updated spot {spot}.")
    else:
        await interaction.followup.send("❌ Spot not found.")

@bot.tree.command(name="moveup", description="Move a player up")
async def moveup(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None and idx > 0:
        lb["spots"][idx], lb["spots"][idx-1] = lb["spots"][idx-1], lb["spots"][idx]
        for i, s in enumerate(lb["spots"]): lb["spots"][i]["num"] = i + 1
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send(f"✅ Moved {spot} up.")

@bot.tree.command(name="movedown", description="Move a player down")
async def movedown(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None and idx < len(lb["spots"]) - 1:
        lb["spots"][idx], lb["spots"][idx+1] = lb["spots"][idx+1], lb["spots"][idx]
        for i, s in enumerate(lb["spots"]): lb["spots"][i]["num"] = i + 1
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send(f"✅ Moved {spot} down.")

@bot.tree.command(name="removeplayer", description="Remove a player")
async def removeplayer(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None:
        lb["spots"][idx] = vacant_spot(spot)
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send(f"✅ Cleared spot {spot}.")

# --- FLAGS DROPDOWN ---
class FlagDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Unlock FPS", value="fps"),
            discord.SelectOption(label="Remove Shadows", value="shadows"),
            discord.SelectOption(label="No Grass", value="grass"),
            discord.SelectOption(label="How to Setup", value="setup")
        ]
        super().__init__(placeholder="Choose a flag...", options=options)

    async def callback(self, interaction: discord.Interaction):
        data = {
            "fps": ("\"DFIntTaskSchedulerTargetFps\": 999", "Removes the 60 FPS cap."),
            "shadows": ("\"FIntRenderShadowIntensity\": 0", "Disables shadows."),
            "grass": ("\"FIntFRMMaxGrassDistance\": 0", "Removes grass.")
        }
        if self.values[0] == "setup":
            await interaction.response.send_message("1. Win+R -> `%LocalAppData%\\Roblox\\Versions`\n2. Open latest folder\n3. Create `ClientSettings` folder\n4. Create `ClientAppSettings.json` inside.", ephemeral=True)
        else:
            code, desc = data[self.values[0]]
            await interaction.response.send_message(f"**{desc}**\n```json\n{{ {code} }}\n```", ephemeral=True)

@bot.tree.command(name="flags", description="Optimization flags")
async def flags_cmd(interaction: discord.Interaction):
    view = discord.ui.View(); view.add_item(FlagDropdown())
    await interaction.response.send_message("Select a flag:", view=view, ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
