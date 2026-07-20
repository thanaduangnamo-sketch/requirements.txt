import discord
from discord.ext import commands

# ตั้งค่า Intents พื้นฐาน
intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🟢 บอทออนไลน์แล้วในชื่อ: {bot.user.name}')
    
    # 🔴 ตั้งค่าสถานะให้ออนเป็นสีแดง (Do Not Disturb)
    await bot.change_presence(
        status=discord.Status.dnd, 
        activity=discord.Game(name="ระบบเปิดใช้งาน 24 ชม.") # ข้อความใต้ชื่อบอท
    )

# ใส่ Token บอทของคุณที่นี่
bot.run('MTUyNjIxNDkxMzQ1MjgwMjEwOA.GPbNe9.Ez0mXlAUlLErQWngvBZwklXwXJEGO3vYBTJL54')
