import asyncio
import os
from threading import Thread
import discord
from discord.ext import commands
from flask import Flask

# ==========================================
# 1. สร้าง Web Server (Flask) สำหรับให้ UptimeRobot ยิง Ping กันหลับ
# ==========================================
app = Flask('')


@app.route('/')
def home():
  # เมื่อ UptimeRobot ยิงเข้ามาที่ URL จะได้รับข้อความนี้ตอบกลับ
  return 'Bots are online and running 24/7!'


def run_web():
  # Render จะส่งพอร์ตมาทาง Environment Variable ชื่อ PORT
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  # รัน Web Server แยกเป็น Background Thread ไม่ให้ไปบล็อกการทำงานของบอท
  t = Thread(target=run_web)
  t.daemon = True
  t.start()


# ==========================================
# 2. ตั้งค่าบอท Discord (สร้าง Intents)
# ==========================================
intents = discord.Intents.default()
intents.message_content = True  # เปิดรับอ่านข้อความ (ถ้าต้องการใช้ Prefix Command)

# สร้าง Instance ของบอทแต่ละตัว (อยากได้กี่ตัวเพิ่มตรงนี้)
bot1 = commands.Bot(command_prefix='!', intents=intents)
bot2 = commands.Bot(command_prefix='?', intents=intents)


# ==========================================
# 3. คำสั่ง & Events ของ บอทตัวที่ 1
# ==========================================
@bot1.event
async def on_ready():
  print(f'✅ บอทตัวที่ 1 ออนไลน์แล้ว: {bot1.user}')


@bot1.command()
async def ping1(ctx):
  await ctx.send('Pong! จากบอทตัวที่ 1 🟢')


# ==========================================
# 4. คำสั่ง & Events ของ บอทตัวที่ 2
# ==========================================
@bot2.event
async def on_ready():
  print(f'✅ บอทตัวที่ 2 ออนไลน์แล้ว: {bot2.user}')


@bot2.command()
async def ping2(ctx):
  await ctx.send('Pong! จากบอทตัวที่ 2 🔵')


# ==========================================
# 5. ฟังก์ชันสั่งรันบอททุกตัวพร้อมกันด้วย asyncio
# ==========================================
async def main():
  # ดึง Token จาก Environment Variables บน Render
  token_1 = os.environ.get('TOKEN_BOT_1')
  token_2 = os.environ.get('TOKEN_BOT_2')

  # เริ่มรัน Web Server กันหลับก่อน
  keep_alive()

  # สั่งรันบอททั้งสองตัวพร้อมกัน
  await asyncio.gather(bot1.start(token_1), bot2.start(token_2))


# เริ่มต้นการทำงานของโปรแกรม
if __name__ == '__main__':
  asyncio.run(main())
