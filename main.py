import discord
from discord.ext import commands
from discord.ui import View, Button
from captcha.image import ImageCaptcha
import random
import io
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

ROLE_ID = 1326066039481565225    
LOG_CHANNEL_ID = 1330377137089413130  
TOKEN = os.environ.get("DISCORD_TOKEN", "ใส่ Token ของบอทในนี้")

@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")

# โค้ดส่วนปุ่มกดและฟังก์ชันอื่นๆ ใช้โครงสร้างเดิมได้เลย เพียงเปลี่ยนคำว่า nextcord เป็น discord
