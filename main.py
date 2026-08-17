import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 1. โหลดข้อมูลจากไฟล์ .env
load_dotenv()

# 2. สร้าง Web Server สั้นๆ เพื่อเปิด Port ให้ Render สแกนเจอ
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        # ปิดการแสดงผล log ของ HTTP Request เพื่อไม่ให้รก Console
        return

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    server.serve_forever()

# 3. ตั้งค่า Discord Bot Intents
intents = discord.Intents.default()
intents.message_content = True  # เปิดใช้งาน Message Content Intent

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Bot is ready and running!")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

# 4. ฟังก์ชันเริ่มต้นการทำงาน
def main():
    # รัน Web Server แยกไว้ใน Background Thread
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # ดึง Discord Token จาก Environment Variable
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("Error: ไม่พบ DISCORD_TOKEN ใน Environment Variables")

    # เริ่มรัน Discord Bot
    bot.run(token)

if __name__ == "__main__":
    main()
