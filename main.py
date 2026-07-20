import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from colorama import Fore, init

init(autoreset=True)

# --- 🟢 [ส่วนที่ 1: โค้ดหลอกพอร์ต Render แผนฟรี] ---
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    print(f"{Fore.LIGHTBLUE_EX}[Web Server] Dummy port opened on port {port} to bypass Render check.")
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()


# --- 🟢 [ส่วนที่ 2: ดึง Token จาก Environment และรันบอท] ---
print(f"{Fore.LIGHTCYAN_EX}[System] Bot is starting up on Render...")
token = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
# หากใช้ discord.py เวอร์ชันเก่า (1.7.3) และไม่มีความจำเป็นต้องใช้ intents ตัวใหม่ สามารถปรับบรรทัดนี้ตามโค้ดเดิมได้ครับ
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{Fore.LIGHTGREEN_EX}[Ready] Connected to Discord successfully!")
    print(f"[Bot Account]: {bot.user.name}")
    print("-----------------------------------------")

# --- โค้ดคำสั่ง (Commands/Events) เดิมของคุณทั้งหมด ก๊อปมาวางต่อตรงนี้ได้เลย ---


if token:
    try:
        bot.run(token)
    except Exception as e:
        print(f"{Fore.LIGHTRED_EX}[Error] Cannot start bot: {e}")
else:
    print(f"{Fore.LIGHTRED_EX}[Error] DISCORD_TOKEN is missing in Environment Variables.")
