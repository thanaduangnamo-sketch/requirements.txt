import os
import discord
from discord.ext import commands

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Bot is ready on Render!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# ดึง Token จาก Environment Variable บน Render
TOKEN = os.environ.get("DISCORD_TOKEN")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_TOKEN not found in environment variables!")
