import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
import threading

# ==================================================
# 🌐 WEB SERVER FOR RENDER (KEEP-ALIVE)
# ==================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: ONLINE 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==================================================
# ⚙️ BOT INITIALIZATION & INTENTS
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sync completed: {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

    # สถานะออนไลน์สีม่วง (Streaming)
    purple_status = discord.Streaming(
        name="ออนไลน์ 24 ชม. 💜", 
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(activity=purple_status)
    print(f"⚡ BOT IS NOW ONLINE: {bot.user}")

# ==================================================
# 🚀 MAIN ENTRY POINT
# ==================================================
async def main():
    # 1. เริ่มรัน Web Server แยก Thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. ดึง Token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ CRITICAL ERROR: Key 'DISCORD_TOKEN' is missing in Environment Variables!")
        return

    # 3. รันบอท
    try:
        await bot.start(token.strip())
    except discord.errors.LoginFailure:
        print("❌ CRITICAL ERROR: Invalid Discord Token!")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
