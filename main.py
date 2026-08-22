import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# ==================================================
# 🌐 WEB SERVER FOR RENDER (KEEP-ALIVE)
# ==================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot status: ONLINE 24/7"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==================================================
# ⚙️ BOT SETUP & INTENTS
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==================================================
# 🤖 BOT EVENTS & PURPLE STATUS
# ==================================================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sync completed: {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

    # ตั้งค่าสถานะออนไลน์เป็นสีม่วง (Streaming)
    purple_status = discord.Streaming(
        name="ออนไลน์ 24 ชม. 💜", 
        url="https://www.twitch.tv/discord"
    )
    await bot.change_presence(activity=purple_status)
    print(f"⚡ BOT IS NOW ONLINE: {bot.user}")

# ==================================================
# 🚀 BOT RUNNER
# ==================================================
if __name__ == "__main__":
    keep_alive()
    
    # ดึง Token จาก Environment Variables ของ Render
    TOKEN = os.getenv("DISCORD_TOKEN")
    
    if not TOKEN:
        print("❌ ERROR: Key 'DISCORD_TOKEN' not found in Render Environment!")
    else:
        try:
            bot.run(TOKEN.strip())
        except discord.errors.LoginFailure:
            print("❌ ERROR: Invalid Discord Token! Check your token in Render Environment.")
        except Exception as e:
            print(f"❌ ERROR: {e}")
