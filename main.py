import os

import json

import asyncio

import aiohttp

import websockets

import socket

import discord

from urllib.parse import urlparse

from discord.ext import commands

from discord import app_commands

from dotenv import load_dotenv



load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_TOKEN")



intents = discord.Intents.default()

intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



BANNER_IMAGE_URL = "https://media.discordapp.net/attachments/1373550875435470869/1415999280262676492/e5b3508e-ccc8-43f9-a693-276517c1cc47.gif?ex=6a8231d8&is=6a80e058&hm=af48d1b3a893fabeebb73ffaa3215e130fd10ac2c4f4a2fc500d2e9f05f903fd&=&width=384&height=216"

DEFAULT_STREAMING_NAME = "ระบบรับตรา HypeSquad 🏆"

DEFAULT_STREAMING_URL = "https://www.twitch.tv/discord"



active_user_streams = {}

pending_selections = {}



# ----------------- Helper Functions -----------------



def get_discord_headers(token: str):

    return {

        "Authorization": token.strip(),

        "Content-Type": "application/json",

        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    }



# --- HypeSquad API Functions ---



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



# --- WebSocket Streaming (แก้ปัญหาเม็ดม่วงหลุดภายใน 10 นาที) ---



async def start_user_streaming_task(token: str, status_text: str):

    """

    วนลูปการเชื่อมต่อ WebSocket แบบอ่าน Message ตลอดเวลา 

    พร้อมส่ง Heartbeat ตามรอบและ Auto-Reconnect หากสัญญาณหลุด

    """

    gateway_url = "wss://gateway.discord.gg/?v=9&encoding=json"

    headers = {

        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    }



    payload_auth = {

        "op": 2,

        "d": {

            "token": token,

            "capabilities": 125,

            "properties": {

                "$os": "Windows",

                "$browser": "Chrome",

                "$device": ""

            },

            "presence": {

                "activities": [{

                    "name": status_text,

                    "type": 1,

                    "url": "https://www.twitch.tv/discord"

                }],

                "status": "online",

                "since": 0,

                "afk": False

            }

        }

    }



    while True:

        try:

            async with websockets.connect(gateway_url, extra_headers=headers) as ws:

                # รับ Hello Payload เพื่อเอาเวลา Heartbeat

                hello_raw = await ws.recv()

                hello_data = json.loads(hello_raw)

                heartbeat_interval = hello_data["d"]["heartbeat_interval"] / 1000



                # ส่ง ยืนยันตัวตน

                await ws.send(json.dumps(payload_auth))



                # Task สำหรับส่ง Heartbeat สม่ำเสมอ

                async def keep_alive():

                    while True:

                        await asyncio.sleep(heartbeat_interval)

                        await ws.send(json.dumps({"op": 1, "d": None}))



                heartbeat_task = asyncio.create_task(keep_alive())



                try:

                    # คอยรับและอ่านข้อมูลจาก Discord เพื่อไม่ให้สายหลุด (Socket Overflow)

                    async for message in ws:

                        data = json.loads(message)

                        if data.get("op") in (7, 9):  # Discord ขอให้ Reconnect

                            break

                finally:

                    heartbeat_task.cancel()



        except asyncio.CancelledError:

            break  # ผู้ใช้กดปิดสถานะ

        except Exception as e:

            print(f"Stream WebSocket error: {e}. Reconnecting in 5 seconds...")

            await asyncio.sleep(5)



# ----------------- Website Safety Inspector Logic -----------------



async def analyze_website_safety(url_input: str):

    """วิเคราะห์ความปลอดภัยของเว็บ โครงสร้าง SSL, IP, Redirects และโดเมนเสี่ยง"""

    if not url_input.startswith(("http://", "https://")):

        url_input = "https://" + url_input



    parsed = urlparse(url_input)

    domain = parsed.netloc or parsed.path.split('/')[0]

    domain = domain.split(':')[0]  # เอาพอร์ตออกถ้ามี



    risk_score = 0

    warnings = []

    highlights = []



    # 1. เช็กความเสี่ยงของโดเมน / คำต้องสงสัย

    suspicious_keywords = ["free-nitro", "discord-gift", "steam-promo", "free-robux", "login-verify", "claim-reward", "gift-card"]

    if any(keyword in domain.lower() for keyword in suspicious_keywords):

        risk_score += 40

        warnings.append("⚠️ โดเมนมีคำเสี่ยงสูงต่อการหลอกลวง (Phishing/Scam)")



    # เช็กโดเมนย่อลิงก์

    shorteners = ["bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "v.gd"]

    if domain.lower() in shorteners:

        risk_score += 15

        warnings.append("ℹ️ เป็นบริการย่อลิงก์ อาจมีการซ่อน URL ปลายทางจริง")



    # เช็กว่าใช้ IP Address แทน Domain หรือไม่

    try:

        socket.inet_aton(domain)

        risk_score += 30

        warnings.append("⚠️ ใช้ IP Address ตรงๆ แทนชื่อโดเมน (เสี่ยงสูง)")

    except socket.error:

        pass



    # เช็ก TLD ทางการ (.go.th, .gov, .edu, .ac.th, .co.th)

    official_tlds = [".go.th", ".gov", ".edu", ".ac.th", ".or.th", ".co.th", ".gov.us", ".edu.au"]

    if any(domain.lower().endswith(tld) for tld in official_tlds):

        highlights.append("🏛️ เป็นโดเมนระดับองค์กร/หน่วยงานรัฐบาล/การศึกษา (ทางการ)")

        risk_score -= 30



    # 2. เช็ก HTTP Response, SSL, Redirect

    status_code = None

    final_url = url_input

    is_https = url_input.startswith("https://")

    server_ip = "ไม่พบข้อมูล"

    ip_country = "ไม่ระบุ"

    isp_info = "ไม่ระบุ"



    if not is_https:

        risk_score += 20

        warnings.append("⚠️ เว็บไซต์ไม่มีการเข้ารหัสความปลอดภัย SSL (HTTP)")



    headers_req = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:

        timeout = aiohttp.ClientTimeout(total=8)

        async with aiohttp.ClientSession(timeout=timeout) as session:

            async with session.get(url_input, headers=headers_req, allow_redirects=True) as resp:

                status_code = resp.status

                final_url = str(resp.url)

                if len(resp.history) > 0:

                    warnings.append(f"🔄 มีการเปลี่ยนเส้นทาง (Redirect) {len(resp.history)} ครั้ง")

    except Exception as e:

        warnings.append(f"❌ ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ ({type(e).__name__})")

        risk_score += 25



    # 3. ดึงข้อมูล IP และสถานที่ตั้งเซิร์ฟเวอร์

    try:

        ip = socket.gethostbyname(domain)

        server_ip = ip

        async with aiohttp.ClientSession() as session:

            async with session.get(f"http://ip-api.com/json/{ip}?fields=country,isp,status") as resp_ip:

                if resp_ip.status == 200:

                    ip_data = await resp_ip.json()

                    if ip_data.get("status") == "success":

                        ip_country = ip_data.get("country", "ไม่ระบุ")

                        isp_info = ip_data.get("isp", "ไม่ระบุ")

    except Exception:

        pass



    # สรุปประเมินความน่าเชื่อถือ

    if risk_score <= 0:

        trust_level = "🟢 **มีความน่าเชื่อถือสูง / ปลอดภัย**"

        color = discord.Color.green()

    elif risk_score <= 25:

        trust_level = "🟡 **ปานกลาง / ควรตรวจสอบข้อมูลเพิ่มเติม**"

        color = discord.Color.gold()

    else:

        trust_level = "🔴 **มีความเสี่ยงสูง / อาจเป็นเว็บอันตราย**"

        color = discord.Color.red()



    embed = discord.Embed(

        title=f"🔎 ผลการตรวจสอบเว็บไซต์: {domain}",

        description=f"**ระดับความน่าเชื่อถือ:** {trust_level}\n**URL ปลายทาง:** `{final_url}`",

        color=color

    )



    embed.add_field(name="🌐 โครงสร้างและโปรโตคอล", value=f"• **การเข้ารหัส:** {'✅ HTTPS (SSL)' if is_https else '❌ HTTP (ไม่มี SSL)'}\n• **Status Code:** `{status_code or 'ไม่ตอบสนอง'}`\n• **ชื่อโดเมนหลัก:** `{domain}`", inline=False)

    embed.add_field(name="📍 ข้อมูลเซิร์ฟเวอร์ (Hosting)", value=f"• **IP Address:** `{server_ip}`\n• **ประเทศที่ตั้ง:** {ip_country}\n• **ผู้ให้บริการ (ISP):** {isp_info}", inline=False)



    if highlights:

        embed.add_field(name="✅ ข้อมูลสนับสนุนความน่าเชื่อถือ", value="\n".join(highlights), inline=False)



    if warnings:

        embed.add_field(name="⚠️ ข้อควรระวัง / ความเสี่ยงที่พบ", value="\n".join(warnings), inline=False)

    else:

        embed.add_field(name="🛡️ ความปลอดภัยเพิ่มเติม", value="ไม่พบคำต้องสงสัย พฤติกรรมเสี่ยง หรือรูปแบบ Phishing ในโดเมนนี้", inline=False)



    embed.set_footer(text="คำเตือน: โปรดอย่ากรอกรหัสผ่านหรือข้อมูลส่วนตัวบนเว็บไซต์ที่ไม่รู้จัก")

    return embed



# ----------------- Modals -----------------



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

                house_names = {1: "Bravery 🔥", 2: "Brilliance ⚡", 3: "Balance 💥"}

                await interaction.followup.send(f"✅ รับตราบ้าน **{house_names.get(house_id)}** สำเร็จเรียบร้อยแล้ว!", ephemeral=True)

            elif status == 401:

                await interaction.followup.send("❌ **User Token ไม่ถูกต้อง**", ephemeral=True)

            else:

                await interaction.followup.send(f"⚠️ เกิดข้อผิดพลาด (Error: {status})", ephemeral=True)

        elif self.action == "leave":

            status = await leave_hypesquad(token)

            if status in (200, 204):

                await interaction.followup.send("✅ ลบตรา HypeSquad ออกเรียบร้อยแล้ว!", ephemeral=True)

            elif status == 401:

                await interaction.followup.send("❌ **User Token ไม่ถูกต้อง**", ephemeral=True)

            else:

                await interaction.followup.send(f"⚠️ เกิดข้อผิดพลาด (Error: {status})", ephemeral=True)



class UserStreamEnableModal(discord.ui.Modal, title="🦋 เปิดใช้งานระบบสถานะสตรีมมิ่ง"):

    token_input = discord.ui.TextInput(label="🔑 User Token", placeholder="กรอก User Token ของคุณ", required=True)

    status_text = discord.ui.TextInput(label="🎮 ข้อความสถานะที่ต้องการแสดง", placeholder="เช่น Live Now / กำลังสตรีมมิ่ง...", required=True)



    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        token = self.token_input.value.strip()

        text = self.status_text.value.strip()

        user_id = interaction.user.id



        if user_id in active_user_streams:

            active_user_streams[user_id].cancel()



        task = asyncio.create_task(start_user_streaming_task(token, text))

        active_user_streams[user_id] = task



        await interaction.followup.send(f"🟣 เปิดสถานะสตรีมมิ่งเม็ดม่วง **{text}** เรียบร้อยแล้ว! (เปิดค้างไว้ยาวๆ ไม่หลุดแล้วครับ)", ephemeral=True)



class UserStreamDisableModal(discord.ui.Modal, title="💦 ปิดใช้งานระบบสถานะสตรีมมิ่ง"):

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id



        if user_id in active_user_streams:

            active_user_streams[user_id].cancel()

            del active_user_streams[user_id]

            await interaction.followup.send("✅ ปิดสถานะสตรีมมิ่งเรียบร้อยแล้ว!", ephemeral=True)

        else:

            await interaction.followup.send("⚠️ ไม่พบสถานะสตรีมมิ่งที่กำลังทำงานอยู่ของคุณ", ephemeral=True)



# ----------------- UI Views -----------------



class HypeSquadSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(label="HypeSquad Bravery", value="1", description="สมัครเข้าบ้านผู้กล้าหาญ", emoji="🔥"),

            discord.SelectOption(label="HypeSquad Brilliance", value="2", description="สมัครเข้าบ้านผู้ฉลาด", emoji="⚡"),

            discord.SelectOption(label="HypeSquad Balance", value="3", description="สมัครเข้าบ้านผู้สมดุล", emoji="💥"),

            discord.SelectOption(label="ล้างตัวเลือกใหม่", value="reset", emoji="🔄")

        ]

        super().__init__(placeholder="[ 🏆 เลือกบ้าน HypeSquad ที่ต้องการ ]", min_values=1, max_values=1, options=options, custom_id="hypesquad_select_menu")



    async def callback(self, interaction: discord.Interaction):

        selected = self.values[0]

        if selected == "reset":

            pending_selections.pop(interaction.user.id, None)

            await interaction.response.send_message("🔄 ล้างตัวเลือกเรียบร้อยแล้ว", ephemeral=True)

        else:

            pending_selections[interaction.user.id] = int(selected)

            await interaction.response.send_modal(HypeSquadTokenModal(action="set"))



class HypeSquadView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(HypeSquadSelect())



    @discord.ui.button(label="c HypeSquad คืออะไร? 3", style=discord.ButtonStyle.primary, custom_id="btn_hypesquad_info")

    async def btn_info(self, interaction: discord.Interaction, button: discord.ui.Button):

        info_embed = discord.Embed(

            title="🏆 HypeSquad คืออะไร?",

            description="**HypeSquad** คือเข็มกลัดประจำบ้านของ Discord ที่จะแสดงอยู่บนหน้าโปรไฟล์ของคุณ",

            color=discord.Color.blue()

        )

        await interaction.response.send_message(embed=info_embed, ephemeral=True)



    @discord.ui.button(label="c ลบตราออก 3", style=discord.ButtonStyle.danger, custom_id="btn_hypesquad_leave")

    async def btn_leave(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_modal(HypeSquadTokenModal(action="leave"))



class StreamPanelSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(label="เปิดทำสถานะ", value="enable_stream", description="เปิดใช้งานระบบสถานะสตรีมมิ่ง (เม็ดม่วง 🟣)", emoji="🦋"),

            discord.SelectOption(label="ปิดทำสถานะ", value="disable_stream", description="ปิดใช้งานระบบสถานะสตรีมมิ่ง", emoji="💦")

        ]

        super().__init__(placeholder="• ตัวเลือกเพิ่มเติม •", min_values=1, max_values=1, options=options, custom_id="stream_panel_select_menu")



    async def callback(self, interaction: discord.Interaction):

        if self.values[0] == "enable_stream":

            await interaction.response.send_modal(UserStreamEnableModal())

        elif self.values[0] == "disable_stream":

            await interaction.response.send_modal(UserStreamDisableModal())



class StreamPanelView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(StreamPanelSelect())



# ----------------- Helper Embed Functions -----------------



def create_hypesquad_embed():

    embed = discord.Embed(

        title="<a:4_:1519289486209454241> ระบบรับตรา",

        description="**HypeSquad Badges**\n\n**Bravery** - สำหรับผู้กล้าหาญ\n**Brilliance** - สำหรับผู้ฉลาด\n**Balance** - สำหรับผู้สมดุล",

        color=discord.Color.from_rgb(47, 49, 54)

    )

    embed.set_image(url=BANNER_IMAGE_URL)

    return embed



def create_stream_panel_embed():

    embed = discord.Embed(

        description=(

            "+ . * 🌟 **ระบบทำสถานะสตรีมมิ่ง**\n"

            "+ . * 🦋 **บริการทำสถานะสตรีมมิ่งฟรี**\n"

            "+ . * 🦋 **ออนไลน์ตลอด 24 ชม.**\n"

            "+ . * 🦋 **ดึงข้อมูลการทำสถานะ**\n"

            "+ . * 🦋 **จัดการระบบสถานะ**"

        ),

        color=discord.Color.from_rgb(47, 49, 54)

    )

    embed.set_image(url=BANNER_IMAGE_URL)

    return embed



# ----------------- Events & Commands -----------------



@bot.event

async def on_ready():

    print(f"Bot Online: {bot.user.name}")

    streaming_activity = discord.Streaming(name=DEFAULT_STREAMING_NAME, url=DEFAULT_STREAMING_URL)

    await bot.change_presence(activity=streaming_activity)



    bot.add_view(HypeSquadView())

    bot.add_view(StreamPanelView())

    try:

        synced = await bot.tree.sync()

        print(f"✅ Sync Global Commands เรียบร้อย ({len(synced)} คำสั่ง)")

    except Exception as e:

        print(f"Sync error: {e}")



# --- คำสั่งเช็กความปลอดภัยของเว็บ ---



@bot.command(name="checkweb", aliases=["checkurl", "webinfo"])

async def cmd_checkweb(ctx, url: str):

    """คำสั่งแบบพิมพ์ !checkweb <ลิงก์เว็บ>"""

    msg = await ctx.send("⏳ กำลังตรวจสอบโครงสร้างและความปลอดภัยของเว็บไซต์...")

    embed = await analyze_website_safety(url)

    await msg.edit(content=None, embed=embed)



@bot.tree.command(name="checkweb", description="ตรวจสอบความปลอดภัยและความน่าเชื่อถือของเว็บไซต์")

@app_commands.describe(url="ใส่ URL หรือชื่อโดเมนเว็บไซต์ที่ต้องการเช็ก")

async def setup_checkweb(interaction: discord.Interaction, url: str):

    """Slash Command /checkweb <url>"""

    await interaction.response.defer()

    embed = await analyze_website_safety(url)

    await interaction.followup.send(embed=embed)



# --- คำสั่งเดิมสำหรับแผงควบคุม ---



@bot.command(name="setup_stream", aliases=["stream_panel"])

@commands.has_permissions(administrator=True)

async def cmd_setup_stream(ctx):

    embed = create_stream_panel_embed()

    await ctx.send(embed=embed, view=StreamPanelView())



@bot.tree.command(name="setup_stream", description="ส่งแผงควบคุมระบบทำสถานะสตรีมมิ่ง")

@app_commands.checks.has_permissions(administrator=True)

async def setup_stream(interaction: discord.Interaction):

    embed = create_stream_panel_embed()

    await interaction.channel.send(embed=embed, view=StreamPanelView())

    await interaction.response.send_message("✅ ส่งแผงระบบทำสถานะสตรีมมิ่งเรียบร้อยแล้ว!", ephemeral=True)



@bot.command(name="setup_hypesquad", aliases=["hypesquad"])

@commands.has_permissions(administrator=True)

async def cmd_setup_hypesquad(ctx):

    embed = create_hypesquad_embed()

    await ctx.send(embed=embed, view=HypeSquadView())



@bot.tree.command(name="setup_hypesquad", description="ส่งแผงควบคุมระบบรับตรา HypeSquad")

@app_commands.checks.has_permissions(administrator=True)

async def setup_hypesquad(interaction: discord.Interaction):

    embed = create_hypesquad_embed()

    await interaction.channel.send(embed=embed, view=HypeSquadView())

    await interaction.response.send_message("✅ ส่งแผงรับตรา HypeSquad เรียบร้อยแล้ว!", ephemeral=True)



bot.run(BOT_TOKEN) 
