import os
import asyncio
import threading
import discord
from discord.ext import commands
from flask import Flask

# ==================================================
# 🌐 WEB SERVER (FLASK)
# ==================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Status: Active 24/7"

# ==================================================
# ⚙️ DISCORD BOT SETUP
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    purple_status = discord.Streaming(
        name="ออนไลน์ 24 ชม. 💜", 
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(activity=purple_status)
    print(f"⚡ BOT ONLINE: {bot.user}")

# ==================================================
# 🔄 BACKGROUND BOT RUNNER
# ==================================================
def start_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ERROR: DISCORD_TOKEN is missing!")
        return
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot.start(token.strip()))

# สั่งรันบอทใน Background Thread ทันทีที่ไฟล์ถูกโหลด
bot_thread = threading.Thread(target=start_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
