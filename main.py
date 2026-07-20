import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🟢 บอทออนไลน์แล้ว: {bot.user.name}')
    await bot.change_presence(
        status=discord.Status.dnd, 
        activity=discord.Game(name="ระบบเปิดใช้งาน 24 ชม.")
    )

bot.run(os.environ.get('DISCORD_TOKEN'))
