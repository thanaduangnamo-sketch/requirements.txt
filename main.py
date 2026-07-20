import discord
import os
from discord.ext import commands

# เปิดสิทธิ์บอทแบบข้ามปัญหา (ดึงมาหมดทุกสิทธิ์)
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🟢 บอทออนไลน์แล้วครับ')
    await bot.change_presence(
        status=discord.Status.dnd, 
        activity=discord.Game(name="ระบบเปิดใช้งาน 24 ชม.")
    )

# ดึงค่าจาก Environment Variable ที่ชื่อ token บน Render มาใช้เลย ไม่ต้องรอพิมพ์
token = os.environ.get("token")
