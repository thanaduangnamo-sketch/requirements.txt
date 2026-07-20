import os
import discord
from discord.ext import commands
from colorama import Fore, init

# เริ่มทำงานระบบ Colorama (ถ้าในโค้ดเดิมมีการใช้งาน)
init(autoreset=True)

# --- [จุดแก้ไขที่ 1: ลบ os.system('cls') ออกเพื่อไม่ให้พังบน Linux] ---
# แทนที่จะใช้ cls เราจะใช้ฟังก์ชันที่รองรับทั้ง Windows และ Linux หรือไม่รันเลยบน Server
def clear_screen():
    # บน Render (Linux) จะไม่สั่งล้างหน้าจอเพื่อป้องกันคำสั่งไม่ทำงาน
    if os.name == 'nt':
        os.system('cls')

clear_screen()

# แสดงข้อความต้อนรับบนหน้า Log ของ Render
print(f"{Fore.LIGHTCYAN_EX}[System] Bot is starting up on Render...")

# --- [จุดแก้ไขที่ 2: เปลี่ยนมาดึง Token จาก Environment Variable] ---
# โค้ดเดิม: token = input(...) -> ลบออกแล้วใช้บรรทัดล่างนี้แทน
token = os.environ.get("DISCORD_TOKEN")

# สร้างตัวแปรบอท (ปรับแต่ง intents และ prefix ตามโค้ดเดิมของคุณได้เลย)
# หมายเหตุ: discord.py เวอร์ชัน 1.7.3 (ตาม Log ของคุณ) บางครั้งอาจไม่ต้องใส่ intents หรือใส่แบบเจาะจง
intents = discord.Intents.default()
bot = commands.Bot(command_code="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{Fore.LIGHTGREEN_EX}[Ready] Connected to Discord successfully!")
    print(f"[Bot Account]: {bot.user.name} (ID: {bot.user.id})")
    print("-----------------------------------------")

# --- ใส่คำสั่ง (Commands) หรือกิจกรรม (Events) อื่น ๆ ของคุณต่อท้ายตรงนี้ได้เลย ---


# --- [จุดรันบอท] ---
if token:
    try:
        bot.run(token)
    except Exception as e:
        print(f"{Fore.LIGHTRED_EX}[Error] Cannot start bot: {e}")
else:
    print(f"{Fore.LIGHTRED_EX}[Error] DISCORD_TOKEN is missing! Please add it to Render's Environment Variables.")
