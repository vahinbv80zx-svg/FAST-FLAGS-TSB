import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
LB_FILE = "leaderboards.json"

HEADER_GIF = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377599662755931/WHITE-1.gif"
VACANT_THUMB = "https://cdn.discordapp.com/attachments/1496355649502580757/1496377629501030400/Black_question_mark.png"

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- DATA ----------
def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_lb(guild_id):
    return _load(LB_FILE).get(str(guild_id))

def set_lb(guild_id, data):
    lbs = _load(LB_FILE)
    lbs[str(guild_id)] = data
    _save(LB_FILE, lbs)

def vacant_spot(num):
    return {
        "num": num,
        "username": "Vacant",
        "discord": "Vacant",
        "roblox": "Information",
        "country": "Null",
        "stage": "Null",
        "thumbnail": VACANT_THUMB,
        "vacant": True,
    }

# ---------- READY ----------
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Logged in as {bot.user} | Synced {len(synced)} commands")

# ---------- EMBED ----------
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

# ---------- REFRESH ----------
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
        except:
            pass

    new_ids = []
    spots = lb["spots"]

    for i in range(0, len(spots), 10):
        embeds = [build_spot_embed(s) for s in spots[i:i+10]]
        msg = await channel.send(embeds=embeds)
        new_ids.append(str(msg.id))

    lb["message_ids"] = new_ids
    set_lb(guild.id, lb)

# ---------- COMMANDS ----------
@bot.tree.command(name="createlb", description="Create leaderboard (max 50)")
@app_commands.describe(spot_range="Example: 1-10", channel="Channel")
async def createlb_cmd(interaction, spot_range: str, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)

    try:
        a, b = spot_range.split("-")
        start, end = int(a), int(b)
    except:
        await interaction.followup.send("❌ Invalid range", ephemeral=True)
        return

    if (end - start + 1) > 50:
        await interaction.followup.send("❌ Max 50 spots", ephemeral=True)
        return

    spots = [vacant_spot(n) for n in range(start, end + 1)]

    set_lb(interaction.guild.id, {
        "channel_id": str(channel.id),
        "message_ids": [],
        "spots": spots
    })

    await interaction.followup.send("✅ Leaderboard created", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))


@bot.tree.command(name="fillspot", description="Fill a spot")
async def fillspot_cmd(interaction, spot: int, username: str, discord_handle: str,
                       roblox: str, country: str, stage: str, thumbnail_url: str):

    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    if not lb:
        await interaction.followup.send("❌ No leaderboard", ephemeral=True)
        return

    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is None:
        await interaction.followup.send("❌ Invalid spot", ephemeral=True)
        return

    lb["spots"][idx] = {
        "num": spot,
        "username": username,
        "discord": discord_handle,
        "roblox": roblox,
        "country": country,
        "stage": stage,
        "thumbnail": thumbnail_url,
        "vacant": False
    }

    set_lb(interaction.guild.id, lb)
    await interaction.followup.send("✅ Updated", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))


@bot.tree.command(name="moveup")
async def moveup_cmd(interaction, spot: int):
    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    if not lb:
        return

    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is None or idx == 0:
        return

    spots = lb["spots"]
    spots[idx], spots[idx-1] = spots[idx-1], spots[idx]
    spots[idx]["num"], spots[idx-1]["num"] = spots[idx-1]["num"], spots[idx]["num"]

    set_lb(interaction.guild.id, lb)
    await interaction.followup.send("✅ Moved up", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))


@bot.tree.command(name="movedown")
async def movedown_cmd(interaction, spot: int):
    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    if not lb:
        return

    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is None or idx >= len(lb["spots"]) - 1:
        return

    spots = lb["spots"]
    spots[idx], spots[idx+1] = spots[idx+1], spots[idx]
    spots[idx]["num"], spots[idx+1]["num"] = spots[idx+1]["num"], spots[idx]["num"]

    set_lb(interaction.guild.id, lb)
    await interaction.followup.send("✅ Moved down", ephemeral=True)
    asyncio.create_task(refresh_leaderboard(interaction.guild))


@bot.tree.command(name="removeplayer")
async def removeplayer_cmd(interaction, spot: int):
    await interaction.response.defer(ephemeral=True)

    lb = get_lb(interaction.guild.id)
    if not lb:
        return

    idx = next((i for i, s in enumerate(lb["spots"]) if s["num"] == spot), None)
    if idx is not None:
        lb["spots"][idx] = vacant_spot(spot)
        set_lb(interaction.guild.id, lb)

        await interaction.followup.send("✅ Reset", ephemeral=True)
        asyncio.create_task(refresh_leaderboard(interaction.guild))


# ---------- RUN ----------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN required")
    bot.run(TOKEN)
