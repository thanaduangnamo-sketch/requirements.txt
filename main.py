import os
import threading
import discord
from discord.ext import commands
from flask import Flask

# ----------------- ส่วนของ Web Server (Flask) -----------------
app = Flask('')

@app.route('/')
def home():
    return "Voice Bot is running!"

# ----------------- ส่วนของ Discord Bot -----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True  # สำคัญสำหรับตรวจจับและใช้งานระบบเสียง

bot = commands.Bot(command_prefix='/', intents=intents)

# กำหนด ID ของช่องเสียงที่ต้องการให้บอทเข้าไปสิง (แทนที่ด้วย ID ช่องเสียงของคุณ)
VOICE_CHANNEL_ID = int(os.environ.get("VOICE_CHANNEL_ID", "123456789012345678"))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # สั่งให้บอทเข้าห้องเสียงทันทีที่เปิดระบบ
    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if channel and isinstance(channel, discord.VoiceChannel):
        try:
            if not channel.guild.voice_client:
                await channel.connect()
                print(f"Connected to voice channel: {channel.name}")
        except Exception as e:
            print(f"Failed to connect to voice: {e}")
    else:
        print("Voice Channel ID not found or invalid.")

@bot.command()
async def join(ctx):
    """คำสั่งพิมพ์ /join เพื่อให้บอทตามเข้ามาในห้องเสียงที่คุณอยู่"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f'เข้ามาในห้อง {channel.name} แล้ว!')
    else:
        await ctx.send('คุณต้องเข้าห้องเสียงก่อนใช้งานคำสั่งนี้!')

@bot.command()
async def leave(ctx):
    """คำสั่งพิมพ์ /leave ให้บอทออกจากห้องเสียง"""
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send('ออกจากห้องเสียงแล้ว!')
    else:
        await ctx.send('บไม่ได้อยู่ในห้องเสียง!')

# ฟังก์ชันรันบอท Discord แยก Thread
def run_bot():
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: Please set DISCORD_TOKEN in environment variables.")

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
