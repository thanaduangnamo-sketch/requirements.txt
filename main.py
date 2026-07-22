import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands

# 📌 ระบุ ID เซิร์ฟเวอร์หลักของคุณที่นี่
MAIN_GUILD_ID = 1522224772258332792

# ==========================================
# 🌐 Web Server สำหรับ Render (กันบอทดับ)
# ==========================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("🤖 Bot Active 24/7!".encode("utf-8"))

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

# ==========================================
# 🤖 Bot Setup & Status เม็ดม่วง
# ==========================================
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 🔐 ระบบ Verification (Modal & View)
# ==========================================
class VerifyCodeModal(discord.ui.Modal, title="🔐 Verify Identity"):
    def __init__(self, correct_code: str, role_id: int):
        super().__init__()
        self.correct_code = correct_code
        self.role_id = role_id

        self.code_input = discord.ui.TextInput(
            label=f"🔢 Enter Code: {correct_code}",
            placeholder="Type the 4-digit code shown above...",
            min_length=4,
            max_length=4,
            required=True
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip() == self.correct_code:
            role = interaction.guild.get_role(self.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 Verification Successful!",
                        description=f"Welcome {interaction.user.mention} ✨\nYou have been given the **{role.name}** role.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ Bot permission error. Please move bot's role higher.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Role not found in server.", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Invalid Code!",
                description="Please click the button to try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class PersistentVerifyView(discord.ui.View):
    def __init__(self, mode: str = "code", role_id: int = None):
        super().__init__(timeout=None)
        self.mode = mode
        self.role_id = role_id

    @discord.ui.button(label="Click to Verify", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="persistent_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id_to_use = self.role_id
        current_mode = self.mode

        if not role_id_to_use and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.footer and embed.footer.text and "ROLE:" in embed.footer.text:
                try:
                    parts = embed.footer.text.split("|")
                    for p in parts:
                        if "ROLE:" in p:
                            role_id_to_use = int(p.replace("ROLE:", "").strip())
                        if "MODE:" in p:
                            current_mode = p.replace("MODE:", "").strip()
                except Exception:
                    pass

        if not role_id_to_use:
            return await interaction.response.send_message("❌ Role settings not found.", ephemeral=True)

        if current_mode == "button":
            role = interaction.guild.get_role(role_id_to_use)
            if role:
                if role in interaction.user.roles:
                    return await interaction.response.send_message("✨ You already have this role!", ephemeral=True)
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 Verification Successful!",
                        description=f"Welcome {interaction.user.mention} ✨\nYou have been given the **{role.name}** role.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ Bot permission error.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Role not found.", ephemeral=True)
        else:
            generated_code = str(random.randint(1000, 9999))
            modal = VerifyCodeModal(correct_code=generated_code, role_id=role_id_to_use)
            await interaction.response.send_modal(modal)

# ==========================================
# 🟣 Bot Events (สถานะเม็ดม่วง)
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ Bot is online: {bot.user.name}")
    bot.add_view(PersistentVerifyView())
    
    # 🟣 ตั้งค่าสถานะเป็น "สตรีมมิ่ง" (เม็ดม่วง)
    await bot.change_presence(
        activity=discord.Streaming(
            name="🛡️ Verification & Server Stats 24/7",
            url="https://www.twitch.tv/discord"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"✨ Synced {len(synced)} commands.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ==========================================
# 📖 Command: Help (ภาษาอังกฤษ)
# ==========================================
@bot.tree.command(name="help", description="📖 Display available commands and bot features")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Command Guide",
        description="Here is a list of all available commands for this server:",
        color=0x9B59B6
    )
    
    embed.add_field(
        name="🛡️ `/setup-verify`",
        value="Set up a verification message with button or code mode (Admin only).",
        inline=False
    )
    
    embed.add_field(
        name="📊 `/membercount`",
        value="Display total members, human users, and bots count in the server.",
        inline=False
    )
    
    embed.add_field(
        name="📖 `/help`",
        value="Show this command help panel.",
        inline=False
    )
    
    embed.set_footer(text="Verification & Utility Bot • 24/7 Active", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# 📊 Command: Member Count (นับจำนวนคน)
# ==========================================
@bot.tree.command(name="membercount", description="📊 Show total members, humans, and bots in this server")
async def member_count(interaction: discord.Interaction):
    guild = interaction.guild
    
    total_members = guild.member_count
    humans = len([m for m in guild.members if not m.bot])
    bots = len([m for m in guild.members if m.bot])
    
    embed = discord.Embed(
        title=f"📊 Server Member Statistics - {guild.name}",
        color=0x3498DB
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
        
    embed.add_field(name="👥 Total Members", value=f"**{total_members:,}**", inline=True)
    embed.add_field(name="🧑 Humans", value=f"**{humans:,}**", inline=True)
    embed.add_field(name="🤖 Bots", value=f"**{bots:,}**", inline=True)
    
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ==========================================
# 📜 Command: ตั้งค่ายืนยันตัวตน
# ==========================================
@bot.tree.command(name="setup-verify", description="🛡️ Create a verification panel (Admin only)")
@app_commands.describe(
    mode="Mode: button (Instant role) or code (4-digit random code)",
    role="Role to give to verified users",
    title="Embed title",
    description="Embed description (Optional)",
    image_url="Embed image URL (Optional)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="🔘 Button Mode (Instant Role)", value="button"),
    app_commands.Choice(name="🔐 Random Code Mode (4-Digits)", value="code")
])
@app_commands.default_permissions(administrator=True)
async def setup_verify(
    interaction: discord.Interaction, 
    mode: app_commands.Choice[str],
    role: discord.Role, 
    title: str, 
    description: str = None, 
    image_url: str = None
):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ Allowed only on the main server.", ephemeral=True)

    if not description:
        if mode.value == "button":
            description = "Click the **Click to Verify** button below to get verified and access the server ✨"
        else:
            description = "Click the **Click to Verify** button below, then enter the 4-digit code to get verified ✨"

    embed = discord.Embed(
        title=title,
        description=f"{description}\n\n🎁 **Role granted:** {role.mention}",
        color=0x9B59B6
    )
    
    if image_url:
        embed.set_image(url=image_url)

    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text=f"Verification System | MODE:{mode.value} | ROLE:{role.id}", icon_url=bot.user.display_avatar.url)

    view = PersistentVerifyView(mode=mode.value, role_id=role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Verification setup created successfully!", ephemeral=True)

# ==========================================
# 🚀 Run Bot
# ==========================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ DISCORD_TOKEN not found in Environment Variables")
