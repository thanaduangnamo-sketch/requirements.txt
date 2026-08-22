import os
import asyncio
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# ==================================================
# 🌐 WEB SERVER FOR RENDER
# ==================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Status: Active 24/7"

# ==================================================
# ⚙️ BOT INITIALIZATION
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
VERIFY_CONFIG = {}

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator or (interaction.user.id == interaction.guild.owner_id)

# ==================================================
# 🔐 VERIFICATION UI
# ==================================================
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ยืนยันตัวตน (Verify)", 
        style=discord.ButtonStyle.success, 
        emoji="✅", 
        custom_id="persistent_verify_button"
    )
    async def verify_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = VERIFY_CONFIG.get(interaction.guild_id)
        if not role_id:
            await interaction.response.send_message("❌ เซิร์ฟเวอร์นี้ยังไม่ได้ตั้งค่ายศยืนยันตัวตน", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ ไม่พบบทบาทที่ตั้งค่าไว้", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ คุณผ่านการยืนยันตัวตนไปแล้ว!", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ ยืนยันตัวตนสำเร็จ! ได้รับยศ {role.mention} เรียบร้อย", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์แจกยศนี้ (กรุณาย้ายยศบอทให้อยู่สูงกว่ายศที่จะแจก)", ephemeral=True)

# ==================================================
# 🤖 BOT EVENTS & PURPLE STATUS
# ==================================================
@bot.event
async def on_ready():
    bot.add_view(VerifyView())
    try:
        await bot.tree.sync()
        print("✅ Commands Synced")
    except Exception as e:
        print(f"❌ Sync Error: {e}")

    purple_status = discord.Streaming(
        name="ออนไลน์ 24 ชม. 💜", 
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(activity=purple_status)
    print(f"⚡ BOT IS ONLINE: {bot.user}")

# ==================================================
# 🔐 COMMANDS
# ==================================================
@bot.tree.command(name="setup_verify", description="[Admin] ตั้งค่าระบบยืนยันตัวตน")
@app_commands.default_permissions(administrator=True)
async def setup_verify(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
    if not is_admin(interaction):
        await interaction.response.send_message("⛔ สิทธิ์ไม่เพียงพอ", ephemeral=True)
        return

    VERIFY_CONFIG[interaction.guild_id] = role.id
    embed = discord.Embed(
        title="🔒 ยืนยันตัวตนเพื่อเข้าถึงเซิร์ฟเวอร์",
        description="กรุณากดปุ่ม **\"ยืนยันตัวตน (Verify)\"** ด้านล่างนี้เพื่อรับยศเข้าใช้งาน",
        color=discord.Color.purple()
    )
    await channel.send(embed=embed, view=VerifyView())
    await interaction.response.send_message(f"✅ ส่งระบบยืนยันตัวตนไปที่ {channel.mention} เรียบร้อย!", ephemeral=True)

# ==================================================
# 🔄 RUNNER
# ==================================================
def start_bot():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.start(token.strip()))

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
