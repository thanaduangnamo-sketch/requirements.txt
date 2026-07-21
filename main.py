import os
import json
import random
import re
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp

MAIN_GUILD_ID = 1522224772258332792

# ==========================================
# 🌐 Web Server หลอกพอร์ตสำหรับ Hosting
# ==========================================
class AliveServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("🤖 บอททำงานปกติ!".encode("utf-8"))

def run_alive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("", port), AliveServer)
    server.serve_forever()

threading.Thread(target=run_alive_server, daemon=True).start()

# ==========================================
# 📁 ระบบ JSON Storage
# ==========================================
SETTINGS_FILE = "guild_settings.json"
BACKUP_FILE = "guild_backups.json"

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# ==========================================
# 🤖 Discord Bot Setup & Streaming Status
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

URL_REGEX = r"(https?://[^\s]+|discord\.gg/[^\s]+|discord\.com/invite/[^\s]+|www\.[^\s]+|[a-zA-Z0-0]+\.(com|net|org|gg|xyz|co|th|io|me))"

# ==========================================
# 🎵 Music Player Configuration
# ==========================================
music_queues = {}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)

def play_next_song(guild_id, interaction_channel):
    if guild_id in music_queues and len(music_queues[guild_id]) > 0:
        song = music_queues[guild_id].pop(0)
        guild = bot.get_guild(guild_id)
        voice_client = guild.voice_client

        if voice_client:
            coro = YTDLSource.from_url(song['url'], loop=bot.loop)
            future = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                player = future.result()
                voice_client.play(player, after=lambda e: play_next_song(guild_id, interaction_channel))
                
                embed = discord.Embed(
                    title="🎵 กำลังเล่นเพลง",
                    description=f"**[{player.title}]({song['url']})**\n⏱️ ความยาว: `{player.duration} วินาที`",
                    color=discord.Color.purple()
                )
                asyncio.run_coroutine_threadsafe(interaction_channel.send(embed=embed), bot.loop)
            except Exception as e:
                print(f"❌ Playback Error: {e}")
                play_next_song(guild_id, interaction_channel)

# ==========================================
# 🧩 Verify Modal & View
# ==========================================
class VerifyCodeModal(discord.ui.Modal, title="🔐 ยืนยันตัวตนด้วยรหัสผ่าน"):
    def __init__(self, correct_code: str, role_id: int):
        super().__init__()
        self.correct_code = correct_code
        self.role_id = role_id

        self.code_input = discord.ui.TextInput(
            label=f"🔢 พิมพ์รหัสผ่านนี้: {correct_code}",
            placeholder="กรอกตัวเลข 4 หลักตามที่เห็นข้างบน...",
            min_length=4,
            max_length=4,
            required=True
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_code = self.code_input.value.strip()

        if user_code == self.correct_code:
            role = interaction.guild.get_role(self.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ โปรดย้ายยศบอทขึ้นไปข้างบน", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ รหัสผ่านไม่ถูกต้อง!",
                description="กรุณากดปุ่มเพื่อรับรหัสผ่านใหม่แล้วลองอีกครั้ง",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class PersistentVerifyView(discord.ui.View):
    def __init__(self, mode: str = "code", role_id: int = None):
        super().__init__(timeout=None)
        self.mode = mode
        self.role_id = role_id

    @discord.ui.button(label="กดเพื่อยืนยันตัวตน", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="persistent_verify_btn")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id_to_use = self.role_id
        current_mode = self.mode

        if not role_id_to_use and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.footer and embed.footer.text:
                if "ROLE:" in embed.footer.text:
                    try:
                        parts = embed.footer.text.split("|")
                        for p in parts:
                            if "ROLE:" in p:
                                role_id_to_use = int(p.replace("ROLE:", "").strip())
                            if "MODE:" in p:
                                current_mode = p.replace("MODE:", "").strip()
                    except Exception:
                        pass

        if not role_id_to_use:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลยศในการตั้งค่า", ephemeral=True)

        if current_mode == "button":
            role = interaction.guild.get_role(role_id_to_use)
            if role:
                if role in interaction.user.roles:
                    return await interaction.response.send_message("✨ คุณมียศนี้อยู่แล้วครับ!", ephemeral=True)
                try:
                    await interaction.user.add_roles(role)
                    embed = discord.Embed(
                        title="🎉 ยืนยันตัวตนสำเร็จ!",
                        description=f"ยินดีต้อนรับ {interaction.user.mention} ✨\nคุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ บอทมียศต่ำกว่ายศที่จะมอบ", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศในระบบ", ephemeral=True)
        else:
            generated_code = str(random.randint(1000, 9999))
            modal = VerifyCodeModal(correct_code=generated_code, role_id=role_id_to_use)
            await interaction.response.send_modal(modal)

# ==========================================
# 🔔 Bot Events & Status
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user.name}")
    bot.add_view(PersistentVerifyView())
    
    # 🟣 ตั้งค่าสถานะเป็น "เม็ดม่วง" (Streaming On Twitch)
    await bot.change_presence(
        activity=discord.Streaming(
            name="🟣 ระบบจัดการดิสคอร์ด & เพลง 24/7",
            url="https://www.twitch.tv/discord"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"✨ ซิงค์คำสั่งสำเร็จ: {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"❌ ซิงค์คำสั่งล้มเหลว: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    settings = load_data(SETTINGS_FILE)
    anti_link_enabled = settings.get("anti_link_enabled", True)

    if anti_link_enabled:
        if re.search(URL_REGEX, message.content, re.IGNORECASE):
            author = message.author
            is_admin = author.guild_permissions.administrator or author.guild_permissions.manage_messages
            user_roles_count = len([r for r in author.roles if not r.is_default()])

            if not is_admin and user_roles_count < 5:
                try:
                    await message.delete()
                    warn_msg = await message.channel.send(
                        f"⚠️ {author.mention} ห้ามส่งลิงก์! (ต้องมียศอย่างน้อย 5 ยศขึ้นไปจึงจะส่งลิงก์ได้)"
                    )
                    await asyncio.sleep(5)
                    await warn_msg.delete()
                except Exception:
                    pass
                return

    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild: discord.Guild):
    settings = load_data(SETTINGS_FILE)
    log_channel_id = settings.get("bot_join_log_channel")

    if log_channel_id:
        log_channel = bot.get_channel(int(log_channel_id))
        if log_channel:
            owner_text = f"{guild.owner.name} ({guild.owner.mention})" if guild.owner else "ไม่พบข้อมูล"
            embed = discord.Embed(
                title="🎉 แจ้งเตือน: บอทเข้าเซิร์ฟเวอร์ใหม่",
                color=0x992D22
            )
            embed.add_field(name="🏰 เซิร์ฟเวอร์", value=f"**{guild.name}**", inline=True)
            embed.add_field(name="🆔 Guild ID", value=f"`{guild.id}`", inline=True)
            embed.add_field(name="👑 เจ้าของ", value=owner_text, inline=False)
            embed.add_field(name="👥 สมาชิก", value=f"`{guild.member_count:,}` คน", inline=True)
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text=f"🌐 รวมทั้งหมด: {len(bot.guilds)} เซิร์ฟเวอร์")
            
            try:
                await log_channel.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_member_join(member: discord.Member):
    settings = load_data(SETTINGS_FILE)
    auto_kick_enabled = settings.get("auto_kick_unverified", False)
    verify_role_id = settings.get("verify_role_id")

    if auto_kick_enabled and verify_role_id:
        await asyncio.sleep(600)
        
        guild = member.guild
        current_member = guild.get_member(member.id)
        
        if current_member:
            role = guild.get_role(int(verify_role_id))
            if role and role not in current_member.roles:
                try:
                    await current_member.kick(reason="ไม่อยืนยันตัวตนภายใน 10 นาที")
                    print(f"👢 เตะ {current_member.name} ออกแล้ว (ไม่อยืนยันตัวตน)")
                except Exception as e:
                    print(f"❌ ไม่สามารถเตะ {current_member.name} ได้: {e}")

# ==========================================
# 📜 คำสั่งระบบหมวดหมู่ภาษาไทย (Slash Commands)
# ==========================================

# ------------------------------------------
# 🛡️ หมวดหมู่ที่ 1: ระบบยืนยันตัวตน (Verify)
# ------------------------------------------
@bot.tree.command(name="ตั้งค่า-ยืนยันตัวตน", description="🛡️ สร้างระบบยืนยันตัวตน (เลือกแบบปุ่มกด หรือ สุ่มรหัสได้)")
@app_commands.describe(
    mode="เลือกรูปแบบ: button (กดรับยศทันที) หรือ code (กดแล้วกรอกรหัสสุ่ม 4 หลัก)",
    role="เลือกยศที่จะให้ผู้ใช้งานหลังยืนยันสำเร็จ",
    title="หัวข้อข้อความประกาศ",
    description="รายละเอียดเพิ่มเติม (เว้นว่างไว้ได้)",
    image_url="ลิงก์รูปภาพแปะ Embed (เว้นว่างไว้ได้)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="🔘 ปุ่มกดรับยศทันที (Button Mode)", value="button"),
    app_commands.Choice(name="🔐 กรอกรหัสสุ่ม 4 หลัก (Random Code Mode)", value="code")
])
@app_commands.default_permissions(administrator=True)
async def setup_verify(
    interaction: discord.Interaction, 
    mode: app_commands.Choice[str],
    role: discord.Role, 
    title: str, 
    description: str = None, 
    image_url: str = None
):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    if not description:
        if mode.value == "button":
            description = "กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับยศเข้าใช้งานเซิร์ฟเวอร์ได้ทันที ✨"
        else:
            description = "กดปุ่ม **ยืนยันตัวตน** ด้านล่างเพื่อรับรหัสผ่านสุ่ม 4 หลัก แล้วกรอกให้ถูกต้องเพื่อรับยศ ✨"

    embed = discord.Embed(
        title=title,
        description=f"{description}\n\n🎁 **ยศที่จะได้รับ:** {role.mention}",
        color=0x9B59B6
    )
    
    if image_url:
        embed.set_image(url=image_url)

    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
        
    embed.set_footer(text=f"Verification System | MODE:{mode.value} | ROLE:{role.id}", icon_url=bot.user.display_avatar.url)

    view = PersistentVerifyView(mode=mode.value, role_id=role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ สร้างระบบยืนยันตัวตนแบบ **{mode.name}** เรียบร้อยแล้ว!", ephemeral=True)


# ------------------------------------------
# 💾 หมวดหมู่ที่ 2: ระบบ Save / Copy ดิสคอร์ด
# ------------------------------------------
@bot.tree.command(name="บันทึก-ดิสคอร์ด", description="💾 สำรองข้อมูลโครงสร้างเซิร์ฟเวอร์ (ยศ และ หมวดหมู่/ช่อง)")
@app_commands.describe(backup_name="ชื่อไฟล์สำรองข้อมูล (เช่น backup-v1)")
@app_commands.default_permissions(administrator=True)
async def save_guild(interaction: discord.Interaction, backup_name: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    roles_data = []
    for r in guild.roles:
        if not r.is_default() and not r.managed:
            roles_data.append({
                "name": r.name,
                "color": r.color.value,
                "permissions": r.permissions.value,
                "hoist": r.hoist,
                "mentionable": r.mentionable
            })

    categories_data = []
    for cat in guild.categories:
        channels_in_cat = []
        for ch in cat.channels:
            channels_in_cat.append({
                "name": ch.name,
                "type": str(ch.type)
            })
        categories_data.append({
            "name": cat.name,
            "channels": channels_in_cat
        })

    backups = load_data(BACKUP_FILE)
    backups[backup_name] = {
        "guild_id": guild.id,
        "guild_name": guild.name,
        "roles": roles_data,
        "categories": categories_data
    }
    save_data(BACKUP_FILE, backups)

    embed = discord.Embed(
        title="💾 บันทึกโครงสร้างดิสคอร์ดสำเร็จ!",
        description=f"เซฟข้อมูลในชื่อ: **`{backup_name}`** เรียบร้อยแล้วครับ\n• จำนวนยศ: `{len(roles_data)}` ยศ\n• จำนวนหมวดหมู่: `{len(categories_data)}` หมวดหมู่",
        color=discord.Color.purple()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="ดึงข้อมูล-ดิสคอร์ด", description="📥 คัดลอกโครงสร้างยศและหมวดหมู่ช่องจากไฟล์สำรอง")
@app_commands.describe(backup_name="ระบุชื่อไฟล์สำรองที่เคยเซฟไว้")
@app_commands.default_permissions(administrator=True)
async def load_guild(interaction: discord.Interaction, backup_name: str):
    await interaction.response.defer(ephemeral=True)
    backups = load_data(BACKUP_FILE)

    if backup_name not in backups:
        return await interaction.followup.send("❌ ไม่พบชื่อไฟล์สำรองข้อมูลนี้ในระบบ!", ephemeral=True)

    backup = backups[backup_name]
    guild = interaction.guild

    # 1. สร้างยศ
    roles_created = 0
    for r_info in backup["roles"]:
        if not discord.utils.get(guild.roles, name=r_info["name"]):
            try:
                await guild.create_role(
                    name=r_info["name"],
                    color=discord.Color(r_info["color"]),
                    permissions=discord.Permissions(r_info["permissions"]),
                    hoist=r_info["hoist"],
                    mentionable=r_info["mentionable"]
                )
                roles_created += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass

    # 2. สร้างหมวดหมู่และช่องข้อความ/เสียง
    cats_created = 0
    for c_info in backup["categories"]:
        cat = discord.utils.get(guild.categories, name=c_info["name"])
        if not cat:
            try:
                cat = await guild.create_category(name=c_info["name"])
                cats_created += 1
            except Exception:
                continue

        for ch_info in c_info["channels"]:
            if ch_info["type"] == "text":
                if not discord.utils.get(cat.text_channels, name=ch_info["name"]):
                    await guild.create_text_channel(name=ch_info["name"], category=cat)
            elif ch_info["type"] == "voice":
                if not discord.utils.get(cat.voice_channels, name=ch_info["name"]):
                    await guild.create_voice_channel(name=ch_info["name"], category=cat)
            await asyncio.sleep(0.3)

    embed = discord.Embed(
        title="📥 คัดลอกโครงสร้างดิสคอร์ดสำเร็จ!",
        description=f"นำเข้าจาก **`{backup_name}`** เรียบร้อยแล้ว\n• สร้างยศใหม่: `{roles_created}` ยศ\n• สร้างหมวดหมู่ใหม่: `{cats_created}` หมวดหมู่",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# ------------------------------------------
# 🎵 หมวดหมู่ที่ 3: ระบบเปิดเพลง (Music)
# ------------------------------------------
@bot.tree.command(name="เล่นเพลง", description="🎵 เปิดเพลงจาก YouTube (พิมพ์ชื่อเพลง หรือ วางลิงก์)")
@app_commands.describe(query="ค้นหาชื่อเพลงหรือวางลิงก์ YouTube")
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ คุณต้องเชื่อมต่อห้องเสียง (Voice Channel) ก่อนครับ!", ephemeral=True)

    await interaction.response.defer()

    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if not voice_client:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    guild_id = interaction.guild_id
    if guild_id not in music_queues:
        music_queues[guild_id] = []

    try:
        loop = bot.loop or asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if 'entries' in info:
            info = info['entries'][0]

        title = info.get('title', 'Unknown Title')
        webpage_url = info.get('webpage_url', query)

        music_queues[guild_id].append({'url': webpage_url, 'title': title})

        if not voice_client.is_playing() and not voice_client.is_paused():
            play_next_song(guild_id, interaction.channel)
            embed = discord.Embed(
                title="🔍 ค้นพบเพลง",
                description=f"กำลังเตรียมเล่น: **[{title}]({webpage_url})**",
                color=discord.Color.purple()
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="📥 เพิ่มเข้าคิวเรียบร้อย",
                description=f"**[{title}]({webpage_url})**\nลำดับคิวที่: `{len(music_queues[guild_id])}`",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการดึงเพลง: {e}")

@bot.tree.command(name="ข้ามเพลง", description="⏭️ ข้ามเพลงปัจจุบันไปเล่นเพลงถัดไป")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("⏭️ ข้ามเพลงเรียบร้อยแล้ว!")
    else:
        await interaction.response.send_message("❌ ไม่มีเพลงกำลังเล่นอยู่ครับ", ephemeral=True)

@bot.tree.command(name="หยุดเพลง", description="⏹️ หยุดเล่นเพลง ล้างคิว และออกจากห้องเสียง")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id in music_queues:
        music_queues[guild_id].clear()

    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("⏹️ หยุดเพลงและออกจากห้องเสียงเรียบร้อยครับ!")
    else:
        await interaction.response.send_message("❌ บอทไม่ได้อยู่ในห้องเสียง", ephemeral=True)

@bot.tree.command(name="คิวเพลง", description="📜 แสดงรายการคิวเพลงที่กำลังรอเล่น")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in music_queues or len(music_queues[guild_id]) == 0:
        return await interaction.response.send_message("📜 ไม่มีรายการเพลงในคิวครับ", ephemeral=True)

    queue_list = "\n".join([f"`{i+1}.` {song['title']}" for i, song in enumerate(music_queues[guild_id][:10])])
    
    embed = discord.Embed(
        title="📜 รายการคิวเพลง",
        description=queue_list,
        color=discord.Color.purple()
    )
    if len(music_queues[guild_id]) > 10:
        embed.set_footer(text=f"และอีก {len(music_queues[guild_id]) - 10} เพลง...")

    await interaction.response.send_message(embed=embed)


# ------------------------------------------
# ⚙️ หมวดหมู่ที่ 4: ตั้งค่าระบบ & ความปลอดภัย
# ------------------------------------------
@bot.tree.command(name="ตั้งค่า-ช่องแจ้งเตือนบอท", description="🔔 ตั้งค่าช่องรับแจ้งเตือนเมื่อดึงบอทเข้าเซิร์ฟเวอร์ใหม่")
@app_commands.describe(channel="เลือกช่องข้อความ")
@app_commands.default_permissions(administrator=True)
async def set_logchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_data(SETTINGS_FILE)
    settings["bot_join_log_channel"] = str(channel.id)
    save_data(SETTINGS_FILE, settings)

    embed = discord.Embed(
        title="✅ บันทึกสำเร็จ",
        description=f"ตั้งค่าช่องแจ้งเตือนเป็น {channel.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ตรวจสอบ-การตั้งค่า", description="⚙️ ตรวจสอบสถานะการตั้งค่าระบบบอทในปัจจุบัน")
@app_commands.default_permissions(administrator=True)
async def check_config(interaction: discord.Interaction):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_data(SETTINGS_FILE)
    log_channel_id = settings.get("bot_join_log_channel")
    
    if log_channel_id:
        ch = bot.get_channel(int(log_channel_id))
        ch_text = ch.mention if ch else f"ID: `{log_channel_id}` (ไม่พบช่องข้อความ)"
        
        embed = discord.Embed(
            title="⚙️ ตรวจสอบการตั้งค่าระบบปัจจุบัน",
            description=f"📢 **ช่องรับแจ้งเตือน Log:** {ch_text}",
            color=discord.Color.purple()
        )
    else:
        embed = discord.Embed(
            title="⚙️ ตรวจสอบการตั้งค่าระบบปัจจุบัน",
            description="⚠️ ยังไม่ได้ตั้งค่าช่องรับแจ้งเตือน (สามารถตั้งค่าด้วย `/ตั้งค่า-ช่องแจ้งเตือนบอท`)",
            color=discord.Color.gold()
        )
        
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="เปิดปิด-เตะคนไม่อยืนยัน", description="⏱️ เปิด/ปิด ระบบเตะคนไม่อยืนยันตัวตนภายใน 10 นาที")
@app_commands.describe(status="เลือกเปิดหรือปิดระบบ", verify_role="เลือกยศยืนยันตัวตนเพื่อตรวจสอบ")
@app_commands.default_permissions(administrator=True)
async def toggle_autokick(interaction: discord.Interaction, status: bool, verify_role: discord.Role = None):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_data(SETTINGS_FILE)
    settings["auto_kick_unverified"] = status
    if verify_role:
        settings["verify_role_id"] = str(verify_role.id)
    save_data(SETTINGS_FILE, settings)

    status_str = "🟢 เปิดใช้งาน" if status else "🔴 ปิดใช้งาน"
    role_str = f"\n🎯 ยศที่ใช้เช็ค: {verify_role.mention}" if verify_role else ""

    embed = discord.Embed(
        title="⚙️ ตั้งค่าระบบเตะเลท 10 นาที",
        description=f"สถานะปัจจุบัน: **{status_str}**{role_str}",
        color=discord.Color.green() if status else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="เปิดปิด-กันส่งลิงก์", description="🚫 เปิด/ปิด ระบบป้องกันการส่งลิงก์ (สำหรับผู้มียศต่ำกว่า 5 ยศ)")
@app_commands.describe(status="เลือกเปิดหรือปิดระบบห้ามส่งลิงก์")
@app_commands.default_permissions(administrator=True)
async def toggle_antilink(interaction: discord.Interaction, status: bool):
    if interaction.guild_id != MAIN_GUILD_ID:
        return await interaction.response.send_message("❌ อนุญาตเฉพาะเซิร์ฟเวอร์หลักเท่านั้น", ephemeral=True)

    settings = load_data(SETTINGS_FILE)
    settings["anti_link_enabled"] = status
    save_data(SETTINGS_FILE, settings)

    status_str = "🟢 เปิดใช้งาน (ห้ามส่งลิงก์ถ้ามียศน้อยกว่า 5 ยศ)" if status else "🔴 ปิดใช้งาน (อนุญาตให้ส่งลิงก์ได้ทุกคน)"

    embed = discord.Embed(
        title="⚙️ ตั้งค่าระบบป้องกันลิงก์",
        description=f"สถานะปัจจุบัน: **{status_str}**",
        color=discord.Color.green() if status else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ลบข้อความ", description="🧹 ลบข้อความในช่องปัจจุบันตามจำนวนที่กำหนด (1-100)")
@app_commands.describe(amount="ระบุจำนวนข้อความที่ต้องการลบ 1-100")
@app_commands.default_permissions(manage_messages=True)
async def clear_messages(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        return await interaction.response.send_message("❌ ระบุ 1-100 เท่านั้น", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    
    embed = discord.Embed(
        title="🧹 ลบเรียบร้อย",
        description=f"ลบไปทั้งหมด **{len(deleted)}** ข้อความ",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==========================================
# 🚀 Start Bot
# ==========================================
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("❌ ไม่พบ DISCORD_TOKEN")
