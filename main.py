import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# --- CONFIGURATION ---
TOKEN = os.environ.get("DISCORD_TOKEN")
LB_FILE = "leaderboards.json"
HEADER_GIF = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377599662755931/WHITE-1.gif?ex=69e9a9bd&is=69e8583d&hm=cae7913688d5a686d7d1da1248509c23b11bacf17387fef4a9d546e6ae9874a7&"
VACANT_THUMB = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377629501030400/Black_question_mark.png?ex=69e9a9c4&is=69e85844&hm=c5f1e8c59fb5aff7c11f84e43133b22c7785163c20b0c150b5caf04095e32eb6&"

# --- DATA HELPERS ---
def get_lb(guild_id):
    if not os.path.exists(LB_FILE): return None
    try:
        with open(LB_FILE, "r") as f:
            data = json.load(f)
        return data.get(str(guild_id))
    except: return None

def set_lb(guild_id, lb_data):
    data = {}
    if os.path.exists(LB_FILE):
        try:
            with open(LB_FILE, "r") as f:
                data = json.load(f)
        except: data = {}
    data[str(guild_id)] = lb_data
    with open(LB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def vacant_spot(n):
    return {"num": n, "username": "Vacant", "discord": "None", "roblox": "None", "country": "None", "stage": "None", "thumbnail": None, "vacant": True}

# --- BOT SETUP ---
class IntegratedBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = IntegratedBot()

# --- UTILS ---
def build_spot_embed(spot):
    desc = f"| `{spot['discord']}` |\n«« | • {spot['roblox']} • | »»\n**Country :** {spot['country']}\n**Stage :** {spot['stage']}"
    embed = discord.Embed(title=f"{spot['num']} - {spot['username']}", description=desc, color=0x2B2D31)
    embed.set_image(url=HEADER_GIF)
    embed.set_thumbnail(url=spot.get("thumbnail") or VACANT_THUMB)
    return embed

async def refresh_leaderboard(guild: discord.Guild):
    lb = get_lb(guild.id)
    if not lb: return
    channel = guild.get_channel(int(lb["channel_id"]))
    if not channel: return
    
    spots = lb["spots"]
    message_ids = lb.get("message_ids", [])
    updated_ids = []
    needed_msgs = (len(spots) + 9) // 10

    for i in range(needed_msgs):
        group = spots[i*10:(i+10)]
        embeds = [build_spot_embed(s) for s in group]
        
        msg_sent = False
        if i < len(message_ids):
            try:
                msg = await channel.fetch_message(int(message_ids[i]))
                await msg.edit(embeds=embeds)
                updated_ids.append(str(msg.id))
                msg_sent = True
            except:
                pass # If edit fails, we'll send a new one below
        
        if not msg_sent:
            new_msg = await channel.send(embeds=embeds)
            updated_ids.append(str(new_msg.id))
        
    lb["message_ids"] = updated_ids
    set_lb(guild.id, lb)

# --- COMMANDS ---
@bot.tree.command(name="createlb")
async def createlb(interaction: discord.Interaction, spot_range: str, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    try:
        a, b = spot_range.split("-")
        start, end = int(a.strip()), int(b.strip())
        spots = [vacant_spot(n) for n in range(start, end + 1)]
        # Reset IDs on a fresh createlb
        set_lb(interaction.guild.id, {"channel_id": str(channel.id), "message_ids": [], "spots": spots})
        await interaction.followup.send("✅ Leaderboard initialized.")
        await refresh_leaderboard(interaction.guild)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="fillspot")
async def fillspot(interaction: discord.Interaction, spot: int, username: str, discord_handle: str, roblox: str, country: str, stage: str, thumbnail_url: str):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    if not lb:
        await interaction.followup.send("❌ Use /createlb first.")
        return
        
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None:
        lb["spots"][idx] = {"num": spot, "username": username, "discord": discord_handle, "roblox": roblox, "country": country, "stage": stage, "thumbnail": thumbnail_url, "vacant": False}
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild) # Wait for this to finish to ensure save
        await interaction.followup.send(f"✅ Spot {spot} updated.")
    else:
        await interaction.followup.send("❌ Spot not found.")

@bot.tree.command(name="removeplayer")
async def removeplayer(interaction: discord.Interaction, spot: int):
    await interaction.response.defer(ephemeral=True)
    lb = get_lb(interaction.guild.id)
    if not lb: return
    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None:
        lb["spots"][idx] = vacant_spot(spot)
        set_lb(interaction.guild.id, lb)
        await refresh_leaderboard(interaction.guild)
        await interaction.followup.send("✅ Player removed.")

@bot.tree.command(name="flags")
async def flags_cmd(interaction: discord.Interaction):
    # (Kept the simple version to avoid any potential syntax crashes)
    await interaction.response.send_message("Check /flags again after the update!", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
