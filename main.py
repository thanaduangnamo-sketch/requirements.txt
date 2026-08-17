import os
import io
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from aiohttp import web
from PIL import Image
import easyocr

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ชื่อยศที่ต้องการมอบเมื่อส่งรูปผ่าน
SUBSCRIBER_ROLE_NAME = "Subscribed"

# โหลด EasyOCR Reader (รองรับภาษาไทย และ อังกฤษ)
print("⏳ กำลังโหลดระบบ OCR (EasyOCR)...")
reader = easyocr.Reader(['th', 'en'], gpu=False)
print("✅ ระบบ OCR พร้อมใช้งานแล้ว!")

# ----------------- Dummy Web Server For Render Port Check -----------------
async def handle_dummy_request(request):
    return web.Response(text="Bot is running!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_dummy_request)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ----------------- Function ตรวจสอบรูปภาพ -----------------
def process_ocr_image(image_bytes):
    """ฟังก์ชันอ่านข้อความในภาพแบบ Synchronous เพื่อนำไปรันใน Executor"""
    image = Image.open(io.BytesIO(image_bytes))
    results = reader.readtext(image_bytes, detail=0)
    full_text = " ".join(results).lower()
    return full_text

async def check_youtube_subscription_image(attachment):
    # ตรวจสอบว่าเป็นไฟล์รูปภาพเท่านั้น
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        return False, "ไม่ใช่รูปภาพ", "กรุณาส่งเป็นไฟล์รูปภาพหลักฐานเท่านั้นครับ"

    try:
        image_bytes = await attachment.read()
        
        # รัน OCR ใน Thread แยกเพื่อไม่ให้บอทค้าง
        loop = asyncio.get_running_loop()
        extracted_text = await loop.run_in_executor(None, process_ocr_image, image_bytes)

        # คำสำคัญสำหรับระบุช่อง
        target_channel = "@tv1rvmsgvcm"
        channel_name = "john42th"

        # เช็กว่ารูปนี้เป็นหน้าช่อง YouTube ที่กำหนดหรือไม่
        has_channel_handle = target_channel in extracted_text
        has_channel_name = channel_name in extracted_text

        if not (has_channel_handle or has_channel_name):
            return False, "ผิดช่อง", f"❌ ไม่พบชื่อช่อง `{target_channel}` ในรูปภาพที่คุณส่งมา"

        # กรณีที่ 1: เจ้าของช่อง (มีปุ่มปรับแต่งช่อง/จัดการวิดีโอ)
        owner_keywords = ["ปรับแต่งช่อง", "จัดการวิดีโอ", "customize channel", "manage videos"]
        is_owner = any(kw in extracted_text for kw in owner_keywords)

        # กรณีที่ 2: ติดตามแล้ว
        sub_keywords = ["ติดตามแล้ว", "subscribed"]
        is_subscribed = any(kw in extracted_text for kw in sub_keywords)

        if is_owner:
            return True, "เจ้าของช่อง", "✅ ตรวจสอบสำเร็จ! คุณเป็น **เจ้าของช่อง**"
        elif is_subscribed:
            return True, "ติดตามแล้ว", "✅ ตรวจสอบสำเร็จ! ตรวจพบหลักฐาน **การกดติดตาม** เรียบร้อย"
        else:
            return False, "ไม่ได้กดติดตาม", "❌ ในรูปยังไม่ได้ขึ้นสถานะ **ติดตามแล้ว** หรือ **ปรับแต่งช่อง** กรุณาตรวจสอบรูปภาพอีกครั้ง"

    except Exception as e:
        print(f"OCR Error: {e}")
        return False, "เกิดข้อผิดพลาด", "❌ ไม่สามารถอ่านข้อมูลจากรูปภาพได้ กรุณาส่งรูปที่คมชัดขึ้น"

# ----------------- Helper Function: มอบหรือสร้างยศอัตโนมัติ -----------------
async def assign_or_create_role(guild: discord.Guild, member: discord.Member, role_name: str):
    role = discord.utils.get(guild.roles, name=role_name)
    created_new = False

    if not role:
        try:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.green(),
                reason="สร้างยศให้อัตโนมัติสำหรับการยืนยันการติดตาม YouTube"
            )
            created_new = True
        except discord.Forbidden:
            return False, "❌ บอทไม่มีสิทธิ์สร้างยศ (กรุณาเช็ก Bot Permissions)", False

    try:
        await member.add_roles(role)
        return True, f"🎉 มอบยศ **{role.name}** ให้เรียบร้อยแล้ว!", created_new
    except discord.Forbidden:
        return False, "❌ บอทไม่มีสิทธิ์มอบยศ (ตำแหน่ง Role ของบอทต้องอยู่สูงกว่ายศที่จะมอบ)", False

# ----------------- Event: ตรวจจับรูปในแชท -----------------
@bot.event
async def on_message(message: discord.Message):
    # ข้ามข้อความจากบอทเอง
    if message.author.bot:
        return

    # ถ้ามีไฟล์แนบส่งเข้ามา
    if message.attachments:
        for attachment in message.attachments:
            # ตรวจเฉพาะไฟล์รูปภาพเท่านั้น
            if attachment.content_type and attachment.content_type.startswith("image/"):
                status_msg = await message.channel.send("🔍 กำลังสแกนและตรวจสอบรูปภาพหลักฐาน...")
                
                success, reason, result_text = await check_youtube_subscription_image(attachment)
                
                if success:
                    # ใส่ Emoji ติ๊กถูกที่ข้อความเดิมของผู้ใช้
                    try:
                        await message.add_reaction("✅")
                    except Exception:
                        pass
                    
                    # มอบยศให้อัตโนมัติ
                    role_success, role_msg, created_new = await assign_or_create_role(
                        message.guild, 
                        message.author, 
                        SUBSCRIBER_ROLE_NAME
                    )

                    embed = discord.Embed(
                        title="✅ ยืนยันการติดตามสำเร็จ!",
                        description=f"{result_text}\n\n{role_msg}",
                        color=discord.Color.green()
                    )
                    if created_new:
                        embed.set_footer(text=f"สร้างยศ {SUBSCRIBER_ROLE_NAME} ใหม่ในเซิร์ฟเวอร์ให้อัตโนมัติ")

                    await status_msg.edit(content=None, embed=embed)
                else:
                    try:
                        await message.add_reaction("❌")
                    except Exception:
                        pass

                    embed = discord.Embed(
                        title="❌ ไม่ผ่านการตรวจสอบ",
                        description=result_text,
                        color=discord.Color.red()
                    )
                    await status_msg.edit(content=None, embed=embed)
                break  # ทำงานเฉพาะรูปแรก

    await bot.process_commands(message)

# ----------------- On Ready -----------------
@bot.event
async def on_ready():
    print(f"Bot Online: {bot.user.name}")
    await start_dummy_server()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Sync Global Commands เรียบร้อย ({len(synced)} คำสั่ง)")
    except Exception as e:
        print(f"Sync error: {e}")

if __name__ == "__main__":
    if BOT_TOKEN:
        bot.run(BOT_TOKEN)
    else:
        print("Error: ไม่พบ DISCORD_TOKEN ใน Environment Variables")
