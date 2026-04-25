import os
import json
import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
OWNER_ID = 1025704740828491806
CONFIG_FILE = "config.json"
LB_FILE = "leaderboards.json"

# --- FIXED IMAGE URLS ---
# Using the Discord CDN link you provided to ensure it loads and doesn't crash
HEADER_GIF = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377599662755931/WHITE-1.gif?ex=69e9a9bd&is=69e8583d&hm=cae7913688d5a686d7d1da1248509c23b11bacf17387fef4a9d546e6ae9874a7&"
VACANT_THUMB = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377629501030400/Black_question_mark.png?ex=69e9a9c4&is=69e85844&hm=c5f1e8c59fb5aff7c11f84e43133b22c7785163c20b0c150b5caf04095e32eb6&"

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Leaderboard rendering ----------
def build_spot_embed(spot):
    desc = (
        f"| `{spot['discord']}` |\n"
        f"«« | • {spot['roblox']} • | »»\n"
        f"**Country :** {spot['country']}\n"
        f"**Stage :** {spot['stage']}"
    )
    embed = discord.Embed(
        title=f"{spot['num']} - {spot['username']}",
        description=desc,
        color=0x2B2D31,
    )
    embed.set_image(url=HEADER_GIF)
    embed.set_thumbnail(url=spot.get("thumbnail") or VACANT_THUMB)
    return embed

async def refresh_leaderboard(guild: discord.Guild):
    lb = get_lb(guild.id)
    if not lb:
        return
    channel = guild.get_channel(int(lb["channel_id"]))
    if channel is None:
        return
    
    for mid in lb.get("message_ids", []):
        try:
            msg = await channel.fetch_message(int(mid))
            await msg.delete()
        except Exception:
            pass
            
    spots = lb["spots"]
    new_ids = []
    for i in range(0, len(spots), 10):
        embeds = [build_spot_embed(s) for s in spots[i:i+10]]
        msg = await channel.send(embeds=embeds)
        new_ids.append(str(msg.id))
        
    lb["message_ids"] = new_ids
    set_lb(guild.id, lb)

# ---------- /createlb ----------
@bot.tree.command(name="createlb", description="Create a leaderboard. Range like 1-10 (max 50).")
@app_commands.describe(spot_range="Range, e.g. 1-10", channel="Channel to post in")
async def createlb_cmd(interaction, spot_range: str, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission.", ephemeral=True); return
    try:
        a, b = spot_range.split("-")
        start, end = int(a.strip()), int(b.strip())
    except Exception:
        await interaction.followup.send("❌ Invalid range. Use `1-10`.", ephemeral=True); return
    if start < 1 or end < start:
        await interaction.followup.send("❌ Invalid range values.", ephemeral=True); return
    if (end - start + 1) > 50:
        await interaction.followup.send("❌ Max 50 spots.", ephemeral=True); return

    spots = [vacant_spot(n) for n in range(start, end + 1)]
    set_lb(interaction.guild.id, {
        "channel_id": str(channel.id),
        "message_ids": [],
        "spots": spots,
    })
    await interaction.followup.send(f"✅ Leaderboard created in {channel.mention}.", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))

# ---------- /fillspot ----------
@bot.tree.command(name="fillspot", description="Fill a leaderboard spot with player info")
@app_commands.describe(
    spot="Spot number", username="Display name", discord_handle="Discord @handle",
    roblox="Roblox username", country="Country flag emoji or name",
    stage="Stage text", thumbnail_url="Direct image URL",
)
async def fillspot_cmd(interaction, spot: int, username: str, discord_handle: str,
                       roblox: str, country: str, stage: str, thumbnail_url: str):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission.", ephemeral=True); return
    lb = get_lb(interaction.guild.id)
    if not lb:
        await interaction.followup.send("❌ Run `/createlb` first.", ephemeral=True); return
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is None:
        await interaction.followup.send("❌ Spot not in this leaderboard.", ephemeral=True); return
    
    lb["spots"][idx] = {
        "num": spot, "username": username, "discord": discord_handle,
        "roblox": roblox, "country": country, "stage": stage,
        "thumbnail": thumbnail_url, "vacant": False,
    }
    set_lb(interaction.guild.id, lb)
    await interaction.followup.send(f"✅ Spot {spot} updated.", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))

# ---------- /moveup ----------
@bot.tree.command(name="moveup", description="Move a spot up by 1")
async def moveup_cmd(interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission.", ephemeral=True); return
    lb = get_lb(interaction.guild.id)
    if not lb:
        await interaction.followup.send("❌ No leaderboard.", ephemeral=True); return
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is None or idx == 0:
        await interaction.followup.send("❌ Can't move up.", ephemeral=True); return
    
    spots = lb["spots"]
    spots[idx], spots[idx - 1] = spots[idx - 1], spots[idx]
    spots[idx]["num"], spots[idx - 1]["num"] = spots[idx - 1]["num"], spots[idx]["num"]
    
    set_lb(interaction.guild.id, lb)
    await interaction.followup.send(f"✅ Moved spot {spot} up.", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))

# ---------- /movedown ----------
@bot.tree.command(name="movedown", description="Move a spot down by 1")
async def movedown_cmd(interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission.", ephemeral=True); return
    lb = get_lb(interaction.guild.id)
    if not lb:
        await interaction.followup.send("❌ No leaderboard.", ephemeral=True); return
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is None or idx >= len(lb["spots"]) - 1:
        await interaction.followup.send("❌ Can't move down.", ephemeral=True); return
    
    spots = lb["spots"]
    spots[idx], spots[idx + 1] = spots[idx + 1], spots[idx]
    spots[idx]["num"], spots[idx + 1]["num"] = spots[idx + 1]["num"], spots[idx]["num"]
    
    set_lb(interaction.guild.id, lb)
    await interaction.followup.send(f"✅ Moved spot {spot} down.", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))

# ---------- /removeplayer ----------
@bot.tree.command(name="removeplayer", description="Reset a spot back to Vacant")
async def removeplayer_cmd(interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    if not has_permission(interaction):
        await interaction.followup.send("❌ No permission.", ephemeral=True); return
    lb = get_lb(interaction.guild.id)
    if not lb:
        await interaction.followup.send("❌ No leaderboard.", ephemeral=True); return
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None:
        lb["spots"][idx] = vacant_spot(spot)
        set_lb(interaction.guild.id, lb)
        await interaction.followup.send(f"✅ Spot {spot} reset to Vacant.", ephemeral=True)
        asyncio.create_task(refresh_leaderboard(interaction.guild))
# --- RAILWAY CONFIGURATION ---
# Railway will look for a variable named DISCORD_TOKEN in your settings
TOKEN = os.getenv('DISCORD_TOKEN')

class FlagBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # No command prefix needed for slash commands, but required by the class
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # This syncs your /flags command with Discord's servers
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print("Bot is ready and commands are synced.")

bot = FlagBot()

# --- SELECT MENU LOGIC ---
class FlagDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Unlock FPS", description="DFIntTaskSchedulerTargetFps"),
            discord.SelectOption(label="Remove Shadows", description="FIntRenderShadowIntensity"),
            discord.SelectOption(label="Disable Post-Process", description="FFlagDisablePostProcess"),
            discord.SelectOption(label="Voxel Lighting", description="DFFlagDebugRenderForceTechnologyVoxel"),
            discord.SelectOption(label="No Anti-Aliasing", description="FIntAntialiasingQuality"),
            discord.SelectOption(label="No Grass", description="FIntFRMMaxGrassDistance"),
            discord.SelectOption(label="Light Culling", description="FFlagDebugForceFSMCPULightCulling"),
            discord.SelectOption(label="Skinned Mesh Opt", description="FFlagOptimizeSkinnedMesh"),
            discord.SelectOption(label="Threaded Present", description="FFlagGfxDeviceAllowThreadedPresent"),
            discord.SelectOption(label="Low Terrain", description="FIntTerrainArraySliceSize"),
            discord.SelectOption(label="How to Setup", description="Installation guide for flags"),
        ]
        super().__init__(placeholder="Choose a legal flag or setup guide...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        
        flag_data = {
            "Unlock FPS": ("\"DFIntTaskSchedulerTargetFps\": 999", "Removes the 60 FPS cap."),
            "Remove Shadows": ("\"FIntRenderShadowIntensity\": 0", "Completely disables shadows for massive FPS gains."),
            "Disable Post-Process": ("\"FFlagDisablePostProcess\": \"True\"", "Removes blur and bloom effects."),
            "Voxel Lighting": ("\"DFFlagDebugRenderForceTechnologyVoxel\": \"True\"", "Uses the fastest lighting engine."),
            "No Anti-Aliasing": ("\"FIntAntialiasingQuality\": 0", "Disables edge smoothing."),
            "No Grass": ("\"FIntFRMMaxGrassDistance\": 0", "Stops rendering grass in the distance."),
            "Light Culling": ("\"FFlagDebugForceFSMCPULightCulling\": \"True\"", "Only calculates light you can see."),
            "Skinned Mesh Opt": ("\"FFlagOptimizeSkinnedMesh\": \"True\"", "Optimizes character animations."),
            "Threaded Present": ("\"FFlagGfxDeviceAllowThreadedPresent\": \"True\"", "Uses multiple CPU threads for rendering."),
            "Low Terrain": ("\"FIntTerrainArraySliceSize\": 0", "Reduces ground and rock detail.")
        }

        if selection == "How to Setup":
            setup_embed = discord.Embed(
                title="How to Setup Flags",
                description=(
                    "1. Press Win + R, type %LocalAppData%\\Roblox\\Versions and hit Enter.\n"
                    "2. Open the latest version folder.\n"
                    "3. Create a folder named ClientSettings.\n"
                    "4. Create a file inside named ClientAppSettings.json.\n"
                    "5. Paste your flags inside { } brackets."
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=setup_embed, ephemeral=True)
        else:
            code, info = flag_data[selection]
            flag_embed = discord.Embed(
                title=f"Flag: {selection}",
                description=f"**What it does:** {info}\n\n**Code:**\n```json\n{code}\n```",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=flag_embed, ephemeral=True)

class FlagView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(FlagDropdown())

# --- SLASH COMMAND ---
@bot.tree.command(name="flags", description="Get legal optimization flags for The Strongest Battlegrounds")
async def flags(interaction: discord.Interaction):
    intro_embed = discord.Embed(
        title="TSB Legal Flags Menu",
        description=(
            "Welcome. These flags are legal and safe to use. "
            "They only optimize performance and will not affect your hitboxes or physics.\n\n"
            "Select an option from the menu below to get the code."
        ),
        color=discord.Color.from_rgb(0, 0, 0)
    )
    await interaction.response.send_message(embed=intro_embed, view=FlagView(), ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN environment variable is required.")
    bot.run(TOKEN)
