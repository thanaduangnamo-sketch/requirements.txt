import asyncio
import os
from threading import Thread
import discord
from discord.ext import commands
from flask import Flask

# --- [ส่วน Keep Alive สำหรับ Render + UptimeRobot] ---
app = Flask('')

@app.route('/')
def home():
    return 'Bot is online and active 24/7!'

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# --- [ตั้งค่า บอทตัวเดียว] ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # สำคัญ: เปิดไว้สำหรับแจกยศและจัดการสมาชิก

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    # Sync คำสั่ง Slash Commands (/) ทั้งหมด
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    print(f"🟢 Logged in as: {bot.user.name} ({bot.user.id})")

# โหลดไฟล์ Cogs ทั้งหมดในโฟลเดอร์ cogs
async def load_extensions():
    if os.path.exists('./cogs'):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"📦 Loaded cog: {filename}")

async def main():
    keep_alive()
    await load_extensions()
    
    # ดึง Token จาก Environment Variable ตัวเดียว
    token = os.environ.get('BOT_TOKEN')
    await bot.start(token)

if __name__ == '__main__':
    asyncio.run(main())
