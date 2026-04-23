import discord
from discord import app_commands
from discord.ext import commands
import os

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

# Start the bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: No DISCORD_TOKEN found in environment variables.")

