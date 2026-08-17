import os
import io
import json
import asyncio
import socket
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

import aiohttp
import websockets
import discord
from urllib.parse import urlparse
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from PIL import Image
import easyocr

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

BANNER_IMAGE_URL = "https://media.discordapp.net/attachments/1373550875435470869/1415999280262676492/e5b3508e-ccc8-43f9-a693-276517c1cc47.gif?ex=6a8231d8&is=6a80e058&hm=af48d1b3a893fabeebb73ffaa3215e130fd10ac2c4f4a2fc500d2e9f05f903fd&=&width=384&height=216"
DEFAULT_STREAMING_NAME = "ระบบรับตรา HypeSquad 🏆"
DEFAULT_STREAMING_URL = "https://www.twitch.tv/discord"
SUBSCRIBER_ROLE_NAME = "Subscribed"

active_user_streams = {}
pending_selections = {}

# ----------------- 1. Web Server สำหรับ Render (เปิดพอร์ตทันที) -----------------

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Bot is running successfully on Render!")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    print(f"✅ Web server listening on port {port} (Render Port Passed)")
    server.serve_forever()

# ----------------- 2. Helper Functions & Roles -----------------

def get_discord_headers(token: str):
    return {
        "Authorization": token.strip(),
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

async def assign_or_create_role(guild: discord.Guild, member: discord.Member, role_name: str):
    role = discord.utils.get(guild.roles, name=role_name)
    created_new = False

    if not role:
        try:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.blue(),
                reason="สร้างยศให้อัตโนมัติ"
            )
            created_new = True
        except discord.Forbidden:
            return False, "❌ บอทไม่มีสิทธิ์สร้างยศ (กรุณาเช็ก Bot Permissions)", False

    try:
        await member.add_roles(role)
        return True, f"✅ มอบยศ **{role.name}** เรียบร้อยแล้ว!", created_new
    except discord.Forbidden:
        return False, "❌ บอทไม่มีสิทธิ์มอบยศ (ตำแหน่ง Role บอทต้องอยู่สูงกว่ายศที่แจก)", False

# ----------------- 3. HypeSquad & Streaming Systems -----------------

async def set_hypesquad_house(token: str, house_id: int):
    url = "https://discord.com/api/v9/hypesquad/online"
    payload = {"house_id": house_id}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=get_discord_headers(token), json=payload) as resp:
            return resp.status

async def leave_hypesquad(token: str):
    url = "https://discord.com/api/v9/hypesquad/online"
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=get_discord_headers(token)) as resp:
            return resp.status

async def start_user_streaming_task(token: str, status_text: str):
    gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    payload_auth = {
        "op": 2,
        "d": {
            "token": token,
            "capabilities": 125,
            "properties": {"$os": "Windows", "$browser": "Chrome", "$device": ""},
            "presence": {
                "activities": [{"name": status_text, "type": 1, "url": "https://www.twitch.tv/discord"}],
                "status": "online", "since": 0, "afk": False
            }
        }
    }
    while True:
        try:
            async with websockets.connect(gateway_url, extra_headers=headers) as ws:
                hello_raw = await ws.recv()
                hello_data = json.loads(hello_raw)
                heartbeat_interval = hello_data["d"]["heartbeat_interval"] / 1000
                await ws.send(json.dumps(payload_auth))

                async def keep_alive():
                    while True:
                        await asyncio.sleep(heartbeat_interval)
                        await ws.send(json.dumps({"op": 1, "d": None}))

                heartbeat_task = asyncio.create_task(keep_alive())
                try:
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("op") in (7, 9):
                            break
                finally:
                    heartbeat_task.cancel()
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(5)

# ----------------- 4. Fast OCR Engine (Lazy Loaded) -----------------

reader_instance = None

def get_ocr_reader():
    global reader_instance
    if reader_instance is None:
        print("⏳ กำลังโหลดระบบ OCR เข้าสู่ Memory (ทำงานเฉพาะครั้งแรก)...")
        reader_instance = easyocr.Reader(['th', 'en'], gpu=False)
        print("✅ ระบบ OCR พร้อมใช้งาน!")
    return reader_instance

def process_ocr_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    ocr = get_ocr_reader()
    results = ocr.readtext(image_bytes, detail=0)
    return " ".join(results).lower()

async def check_youtube_subscription_image(attachment):
    if not attachment.content_type or not attachment.content_type.startswith("image/"):
        return False, "ไม่ใช่รูปภาพ", "กรุณาส่งเป็นไฟล์รูปภาพหลักฐานเท่านั้นครับ"

    try:
        image_bytes = await attachment.read()
        loop = asyncio.get_running_loop()
        extracted_text = await loop.run_in_executor(None, process_ocr_image, image_bytes)

        target_channel = "@tv1rvmsgvcm"
        channel_name = "john42th"

        if not (target_channel in extracted_text or channel_name in extracted_text):
            return False, "ผิดช่อง", f"❌ ไม่พบชื่อช่อง `{target_channel}` ในรูปภาพที่คุณส่งมา"

        if any(kw in extracted_text for kw in ["ปรับแต่งช่อง", "จัดการวิดีโอ", "customize channel", "manage videos"]):
            return True, "เจ้าของช่อง", "✅ ตรวจสอบสำเร็จ! คุณเป็น **เจ้าของช่อง**"
        elif any(kw in extracted_text for kw in ["ติดตามแล้ว", "subscribed"]):
            return True, "ติดตามแล้ว", "✅ ตรวจสอบสำเร็จ! ตรวจพบหลักฐาน **การกดติดตาม** เรียบร้อย"
        else:
            return False, "ไม่ได้กดติดตาม", "❌ ในรูปยังไม่ได้ขึ้นสถานะ **ติดตามแล้ว** หรือ **ปรับแต่งช่อง**"
    except Exception:
        return False, "เกิดข้อผิดพลาด", "❌ ไม่สามารถอ่านข้อมูลจากรูปภาพได้"

# ----------------- 5. Region / Province Auto-Role Data -----------------

PROVINCES_DATA = {
    "central": {"name": "ภาคกลาง", "items": ["กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "พระนครศรีอยุธยา", "นครปฐม", "สมุทรสาคร"]},
    "north": {"name": "ภาคเหนือ", "items": ["เชียงใหม่", "เชียงราย", "ลำปาง", "ลำพูน", "แม่ฮ่องสอน", "น่าน", "แพร่", "พิษณุโลก"]},
    "ne": {"name": "ภาคตะวันออกเฉียงเหนือ", "items": ["นครราชสีมา", "ขอนแก่น", "อุดรธานี", "อุบลราชธานี", "บุรีรัมย์", "ร้อยเอ็ด", "ศรีสะเกษ"]},
    "east": {"name": "ภาคตะวันออก", "items": ["ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "สระแก้ว"]},
    "west": {"name": "ภาคตะวันตก", "items": ["กาญจนบุรี", "ตาก", "เพชรบุรี", "ประจวบคีรีขันธ์", "ราชบุรี"]},
    "south": {"name": "ภาคใต้", "items": ["ภูเก็ต", "สุราษฎร์ธานี", "สงขลา", "กระบี่", "นครศรีธรรมราช", "พังงา", "ตรัง", "หาดใหญ่/อื่น ๆ"]}
}

# ----------------- Modals & UI Components -----------------

class HypeSquadTokenModal(discord.ui.Modal, title="🔑 กรอก User Token"):
    token_input = discord.ui.TextInput(label="🔑 : User Token", placeholder="โทเค่นผู้ใช้งานของคุณ", required=True)
    def __init__(self, action: str):
        super().__init__()
        self.action = action

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        token = self.token_input.value.strip()
        if self.action == "set":
            house_id = pending_selections.get(interaction.user.id)
            if not house_id:
                await interaction.followup.send("❌ กรุณาเลือกบ้าน HypeSquad ในเมนูก่อนครับ", ephemeral=True)
                return
            status = await set_hypesquad_house(token, house_id)
            if status in (200, 204):
                await interaction.followup.send("✅ รับตราสำเร็จเรียบร้อยแล้ว!", ephemeral=True)
            else:
                await interaction.followup.send("❌ โทเค่นไม่ถูกต้อง หรือเกิดข้อผิดพลาด", ephemeral=True)
        elif self.action == "leave":
            status = await leave_hypesquad(token)
            if status in (200, 204):
                await interaction.followup.send("✅ ลบตราเรียบร้อยแล้ว!", ephemeral=True)

class UserStreamEnableModal(discord.ui.Modal, title="🦋 เปิดใช้งานสถานะสตรีมมิ่ง"):
    token_input = discord.ui.TextInput(label="🔑 User Token", placeholder="กรอก User Token", required=True)
    status_text = discord.ui.TextInput(label="🎮 ข้อความสถานะ", placeholder="เช่น Live Now...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        if user_id in active_user_streams:
            active_user_streams[user_id].cancel()
        task = asyncio.create_task(start_user_streaming_task(self.token_input.value.strip(), self.status_text.value.strip()))
        active_user_streams[user_id] = task
        await interaction.followup.send(f"🟣 เปิดสถานะสตรีมมิ่ง **{self.status_text.value.strip()}** เรียบร้อยแล้ว!", ephemeral=True)

class UserStreamDisableModal(discord.ui.Modal, title="💦 ปิดใช้งานสถานะสตรีมมิ่ง"):
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        if user_id in active_user_streams:
            active_user_streams[user_id].cancel()
            del active_user_streams[user_id]
            await interaction.followup.send("✅ ปิดสถานะสตรีมมิ่งเรียบร้อยแล้ว!", ephemeral=True)

class ProvinceSelect(discord.ui.Select):
    def __init__(self, region_key: str):
        provinces = PROVINCES_DATA.get(region_key, {}).get("items", [])
        options = [discord.SelectOption(label=prov, value=prov, emoji="📍") for prov in provinces]
        super().__init__(placeholder="📍 เลือกจังหวัดของคุณ", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success, msg, created_new = await assign_or_create_role(interaction.guild, interaction.user, self.values[0])
        if success and created_new:
            msg += " *(สร้างยศใหม่ให้อัตโนมัติ)*"
        await interaction.followup.send(msg, ephemeral=True)

class ProvinceView(discord.ui.View):
    def __init__(self, region_key: str):
        super().__init__(timeout=180)
        self.add_item(ProvinceSelect(region_key))

class RegionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="ภาคกลาง", value="central", emoji="🏢"),
            discord.SelectOption(label="ภาคเหนือ", value="north", emoji="⛰️"),
            discord.SelectOption(label="ภาคตะวันออกเฉียงเหนือ", value="ne", emoji="🌾"),
            discord.SelectOption(label="ภาคตะวันออก", value="east", emoji="🏖️"),
            discord.SelectOption(label="ภาคตะวันตก", value="west", emoji="🏞️"),
            discord.SelectOption(label="ภาคใต้", value="south", emoji="🌊"),
        ]
        super().__init__(placeholder="🔻 เลือกภูมิภาคของคุณ", min_values=1, max_values=1, options=options, custom_id="region_select_main")

    async def callback(self, interaction: discord.Interaction):
        region_key = self.values[0]
        view = ProvinceView(region_key)
        await interaction.response.send_message(f"📍 คุณเลือก **{PROVINCES_DATA[region_key]['name']}** กรุณาเลือกจังหวัดของคุณ:", view=view, ephemeral=True)

class RegionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RegionSelect())

class HypeSquadSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="HypeSquad Bravery", value="1", emoji="🔥"),
            discord.SelectOption(label="HypeSquad Brilliance", value="2", emoji="⚡"),
            discord.SelectOption(label="HypeSquad Balance", value="3", emoji="💥"),
        ]
        super().__init__(placeholder="[ 🏆 เลือกบ้าน HypeSquad ]", min_values=1, max_values=1, options=options, custom_id="hypesquad_select_menu")

    async def callback(self, interaction: discord.Interaction):
        pending_selections[interaction.user.id] = int(self.values[0])
        await interaction.response.send_modal(HypeSquadTokenModal(action="set"))

class HypeSquadView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HypeSquadSelect())

class StreamPanelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="เปิดทำสถานะ", value="enable_stream", emoji="🦋"),
            discord.SelectOption(label="ปิดทำสถานะ", value="disable_stream", emoji="💦")
        ]
        super().__init__(placeholder="• ตัวเลือกสถานะ •", min_values=1, max_values=1, options=options, custom_id="stream_panel_select_menu")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "enable_stream":
            await interaction.response.send_modal(UserStreamEnableModal())
        else:
            await interaction.response.send_modal(UserStreamDisableModal())

class StreamPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StreamPanelSelect())

# ----------------- 6. Events & Commands -----------------

@bot.event
async def on_ready():
    print(f"Bot Online: {bot.user.name}")
    streaming_activity = discord.Streaming(name=DEFAULT_STREAMING_NAME, url=DEFAULT_STREAMING_URL)
    await bot.change_presence(activity=streaming_activity)

    bot.add_view(HypeSquadView())
    bot.add_view(StreamPanelView())
    bot.add_view(RegionPanelView())
    try:
        await bot.tree.sync()
        print("✅ Sync Commands เรียบร้อย")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                status_msg = await message.channel.send("🔍 กำลังสแกนและตรวจสอบรูปภาพหลักฐาน...")
                success, reason, result_text = await check_youtube_subscription_image(attachment)
                
                if success:
                    try:
                        await message.add_reaction("✅")
                    except Exception:
                        pass
                    
                    role_success, role_msg, created_new = await assign_or_create_role(message.guild, message.author, SUBSCRIBER_ROLE_NAME)
                    embed = discord.Embed(title="✅ ยืนยันการติดตามสำเร็จ!", description=f"{result_text}\n\n{role_msg}", color=discord.Color.green())
                    await status_msg.edit(content=None, embed=embed)
                else:
                    try:
                        await message.add_reaction("❌")
                    except Exception:
                        pass
                    embed = discord.Embed(title="❌ ไม่ผ่านการตรวจสอบ", description=result_text, color=discord.Color.red())
                    await status_msg.edit(content=None, embed=embed)
                break

    await bot.process_commands(message)

# Commands สำหรับเรียกแผงเมนูต่าง ๆ
@bot.command(name="setup_region")
@commands.has_permissions(administrator=True)
async def cmd_setup_region(ctx):
    embed = discord.Embed(title="🇹🇭 เลือกจังหวัดของคุณ", description="เลือกภูมิภาคและจังหวัดเพื่อรับยศอัตโนมัติ", color=discord.Color.gold())
    await ctx.send(embed=embed, view=RegionPanelView())

@bot.command(name="setup_hypesquad")
@commands.has_permissions(administrator=True)
async def cmd_setup_hypesquad(ctx):
    embed = discord.Embed(title="🏆 ระบบรับตรา HypeSquad", color=discord.Color.blue())
    embed.set_image(url=BANNER_IMAGE_URL)
    await ctx.send(embed=embed, view=HypeSquadView())

@bot.command(name="setup_stream")
@commands.has_permissions(administrator=True)
async def cmd_setup_stream(ctx):
    embed = discord.Embed(description="🌟 **ระบบทำสถานะสตรีมมิ่ง 24 ชม.**", color=discord.Color.purple())
    embed.set_image(url=BANNER_IMAGE_URL)
    await ctx.send(embed=embed, view=StreamPanelView())

if __name__ == "__main__":
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()

    if BOT_TOKEN:
        try:
            bot.run(BOT_TOKEN)
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการรัน Discord Bot: {e}", file=sys.stderr)
    else:
        print("❌ Error: ไม่พบ DISCORD_TOKEN ใน Environment Variables", file=sys.stderr)
        while True:
            time.sleep(3600)
