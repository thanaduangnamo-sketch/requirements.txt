import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from colorama import Fore, init

# เริ่มต้นระบบ colorama สำหรับแสดงสีข้อความ
init(autoreset=True)

# ========================================================
# 🟢 ส่วนที่ 1: ระบบเปิดพอร์ตหลอก (Bypass Web Service ของ Render)
# ========================================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_alive_server():
    # Render จะส่งพอร์ตมาให้ผ่าน Environment Variable ชื่อ PORT
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    print(f"{Fore.LIGHTBLUE_EX}[Web Server] Dummy port opened on port {port} to bypass Render check.")
    server.serve_forever()

# สั่งให้เว็บเซิร์ฟเวอร์หลอกทำงานเบื้องหลัง (Background Thread)
threading.Thread(target=run_alive_server, daemon=True).start()

# ========================================================
# 🟢 ส่วนที่ 2: ตั้งค่าบอท Discord และดึง Token จากระบบ
# ========================================================
print(f"{Fore.LIGHTCYAN_EX}[System] Bot is starting up on Render...")

# ดึง Token จากหน้า Environment ของ Render (ห้ามใช้ input())
token = os.environ.get("DISCORD_TOKEN")

# ตั้งค่า Intents สำหรับบอท
intents = discord.Intents.default()
intents.message_content = True  # เปิดใช้งานหากบอทจำเป็นต้องอ่านข้อความ

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{Fore.LIGHTGREEN_EX}[Ready] Connected to Discord successfully!")
    print(f"[Bot Account]: {bot.user.name}")
    print("-----------------------------------------")

# ========================================================
# 🟢 ส่วนที่ 3: โค้ดคำสั่งบอทของคุณ (Commands / Events)
# ========================================================

# พิมพ์หรือก๊อปปี้คำสั่ง (@bot.command) เดิมของคุณมาวางต่อตรงนี้ได้เลยครับ เช่น:
# @bot.command()
# async def ping(ctx):
#     await ctx.send("pong!")


# ========================================================
# 🟢 ส่วนที่ 4: สั่งรันบอท
# ========================================================
if token:
    try:
        bot.run(token)
    except Exception as e:
        print(f"{Fore.LIGHTRED_EX}[Error] Cannot start bot: {e}")
else:
    print(f"{Fore.LIGHTRED_EX}[Error] DISCORD_TOKEN is missing in Render Environment Variables.")
