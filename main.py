import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# ----------------- ส่วนของ Web Server (Flask) -----------------
app = Flask('')

@app.route('/')
def home():
    return "Voice Bot is running 24/7!"

# ----------------- ส่วนของ Discord Bot -----------------
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # 1. ตั้งค่าสถานะบอท (แถบสีม่วง / Streaming หรือ Playing)
    # สามารถเปลี่ยนข้อความด้านล่างนี้ได้ตามต้องการ
    activity = discord.Streaming(
        name="กำลังออนแอร์ 24 ชม. 🎧", 
        url="https://www.twitch.tv/discord" # ลิงก์นี้จะทำให้แถบขึ้นเป็นสีม่วงสวยงาม
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print("Bot status set to streaming (purple banner).")

    # 2. ระบบเข้าห้องเสียงอัตโนมัติ 24 ชม. (ดึงจาก Environment Variable ชื่อ VOICE_CHANNEL_ID)
    channel_id_str = os.environ.get("VOICE_CHANNEL_ID")
    if channel_id_str:
        try:
            channel_id = int(channel_id_str)
            channel = bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                if not channel.guild.voice_client:
                    await channel.connect()
                    print(f"Auto-connected to voice channel: {channel.name}")
        except Exception as e:
            print(f"Failed to auto-connect to voice channel: {e}")

# คำสั่ง Slash Command: /join (เลือกห้องได้เอง)
@bot.tree.command(name="join", description="เลือกช่องเสียงเพื่อให้บอทเข้าไปสิง")
@app_commands.describe(channel="เลือกห้องเสียงที่ต้องการให้บอทเข้าไป")
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel):
    voice_client = interaction.guild.voice_client
    try:
        if voice_client:
            await voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f'✅ บอทเข้ามาที่ห้องเสียง **{channel.name}** เรียบร้อยแล้ว!', ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e}', ephemeral=True)

# คำสั่ง Slash Command: /leave
@bot.tree.command(name="leave", description="สั่งให้บอทออกจากห้องเสียง")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message('👋 บอทออกจากห้องเสียงแล้ว', ephemeral=False)
    else:
        await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

# ฟังก์ชันรันบอท
def run_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: Please set DISCORD_TOKEN in environment variables.")

# เริ่มต้นรันบอทใน Background Thread ผ่าน Gunicorn
if not hasattr(app, "bot_started"):
    app.bot_started = True
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
