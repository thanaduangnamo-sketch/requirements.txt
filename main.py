import os
import threading
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
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
        print("Slash commands synced successfully.")

bot = VoiceBot()

# ลูปสำหรับเปลี่ยนสีสถานะบอททุกๆ 1 นาที (วนไป: เขียว -> เหลือง -> แดง)
@tasks.loop(minutes=1)
async def change_bot_status():
    statuses = [
        (discord.Status.online, discord.Streaming(name="🟢 ออนไลน์ 24 ชม. | ฟังเพลง", url="https://www.twitch.tv/discord")),
        (discord.Status.idle, discord.Streaming(name="🟡 สถานะว่าง | พักผ่อน", url="https://www.twitch.tv/discord")),
        (discord.Status.do_not_disturb, discord.Streaming(name="🔴 ห้ามรบกวน | กำลังสตรีม", url="https://www.twitch.tv/discord"))
    ]
    
    # วนลูปเปลี่ยนสถานะทีละแบบ
    for status_type, activity in statuses:
        await bot.change_presence(status=status_type, activity=activity)
        await asyncio.sleep(20) # เปลี่ยนสถานะทุกๆ 20 วินาทีภายในลูป 1 นาทีเพื่อให้ครบรวดเร็ว หรือจะปรับตามชอบได้ครับ

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # เริ่มต้นทำงานลูปเปลี่ยนสีสถานะ
    if not change_bot_status.is_running():
        change_bot_status.start()

    # ระบบเข้าห้องเสียงอัตโนมัติ (ดึง ID จาก Environment Variable: VOICE_CHANNEL_ID)
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

# คำสั่ง Slash Command: /join (เลือกห้องเสียงจากเมนูดรอปดาวน์ได้เองทันที)
@bot.tree.command(name="join", description="เลือกช่องเสียงเพื่อให้บอทเข้าไปสิง")
@app_commands.describe(channel="เลือกห้องเสียงที่ต้องการให้บอทเข้าไป")
async def join(interaction: discord.Interaction, channel: discord.VoiceChannel):
    voice_client = interaction.guild.voice_client
    try:
        if voice_client:
            await voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f'🎧 บอทเข้ามาที่ห้องเสียง **{channel.name}** เรียบร้อยแล้ว!', ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e}', ephemeral=True)

# คำสั่ง Slash Command: /leave (สั่งให้บอทออกจากห้องเสียง)
@bot.tree.command(name="leave", description="สั่งให้บอทออกจากช่องเสียงปัจจุบัน")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message('👋 บอทออกจากห้องเสียงเรียบร้อยแล้ว', ephemeral=False)
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
