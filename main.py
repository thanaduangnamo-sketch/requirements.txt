import discord
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

# ⚠️ เอา Token อันใหม่ที่คุณมี มาวางแทนที่ข้อความภาษาไทยในเครื่องหมายคำพูดได้เลยครับ
bot.run('token')
