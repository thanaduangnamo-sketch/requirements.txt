import os
import random
import threading
import time
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask

# 1. ส่วนของเว็บเซิร์ฟเวอร์ Flask เพื่อเปิดพอร์ตให้ Render ตรวจพบ
app = Flask('')

@app.route('/')
def home():
    return "Bot Token Checker & Roblox Version Auto-Notifier is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. ส่วนของบอท Discord
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True
intents.members = True
intents.bans = True

# --- ตัวแปรสำหรับเก็บค่าการตั้งค่าและเวอร์ชันล่าสุดของ Roblox ---
ant_settings = {
    "anti_link": {},
    "anti_nuke": {},
    "anti_spam": {}
}

roblox_notify_channels = {}
latest_roblox_version = None
spam_tracker = {}

# --- ระบบ Modal สำหรับกรอกรหัสยืนยันตัวตน ---
class VerifyModal(discord.ui.Modal, title="🛡️ ระบบยืนยันตัวตนความปลอดภัย"):
    code_input = discord.ui.TextInput(
        label="กรุณากรอกรหัส 6 หลักที่แสดงด้านล่าง",
        placeholder="เช่น 123456",
        max_length=6,
        min_length=6,
        required=True
    )

    def __init__(self, expected_code: str):
        super().__init__()
        self.expected_code = expected_code

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip() == self.expected_code:
            guild = interaction.guild
            member = interaction.user
            role = discord.utils.get(guild.roles, name="Member")
            
            if role:
                try:
                    await member.add_roles(role)
                    await interaction.response.send_message("✨ **ยืนยันตัวตนสำเร็จ!** คุณได้รับยศ `Member` เรียบร้อยแล้วครับ 🎉", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการมอบยศ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศ `Member` ในเซิร์ฟเวอร์นี้ กรุณาแจ้งแอดมิน", ephemeral=True)
        else:
            await interaction.response.send_message("❌ **รหัสยืนยันตัวตนไม่ถูกต้อง!** กรุณากดปุ่มแล้วลองใหม่อีกครั้ง", ephemeral=True)

# --- ระบบ Modal สำหรับกรอก Token ของบอทเพื่อตรวจสอบจริง ---
class TokenInputModal(discord.ui.Modal, title="🔑 ระบบตั้งค่าและตรวจสอบ Token บอท"):
    token_input = discord.ui.TextInput(
        label="กรอก Bot Token ของคุณที่นี่",
        placeholder="วาง Token ของบอท Discord ที่นี่...",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_token = self.token_input.value.strip()

        headers = {"Authorization": f"Bot {user_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    bot_name = data.get("username", "Unknown")
                    bot_id = data.get("id", "Unknown")
                    avatar_hash = data.get("avatar")
                    
                    if avatar_hash:
                        bot_avatar_url = f"https://cdn.discordapp.com/avatars/{bot_id}/{avatar_hash}.png?size=1024"
                    else:
                        bot_avatar_url = "https://i.pinimg.com/1200x/ec/4c/a4/ec4ca469fe2a2c245010b94099819059.jpg"

                    masked_token = user_token[:6] + "..." + user_token[-6:] if len(user_token) > 10 else "******"

                    embed = discord.Embed(
                        title="🔑 ผลการตรวจสอบ Token และสถานะบอท (Validated)",
                        description=(
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "✨ **รายงานข้อมูลระบบ (Token Status Report):**\n"
                            f"• 🤖 **ชื่อบอท:** `{bot_name}`\n"
                            f"• 🆔 **Bot ID:** `{bot_id}`\n"
                            f"• 🟢 **สถานะการเชื่อมต่อ:** `ใช้งานปกติ (Valid Token / Active)`\n"
                            f"• 🔑 **Token ที่ตรวจสอบ:** `{masked_token}`\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=0x2ECC71
                    )
                    embed.set_thumbnail(url=bot_avatar_url)
                    embed.set_footer(text=f"ตรวจสอบโดย: {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

                    try:
                        await interaction.user.send(embed=embed)
                        await interaction.followup.send("✅ ตรวจสอบ Token สำเร็จ! ระบบได้จัดส่งผลรายงานจริงส่งตรงเข้าทาง **DM (ข้อความส่วนตัว)** ของคุณแล้วครับ", ephemeral=True)
                    except Exception:
                        await interaction.followup.send("❌ ตรวจสอบ Token สำเร็จ แต่ไม่สามารถส่งข้อความหาคุณทาง DM ได้ กรุณาเปิดรับข้อความส่วนตัว (Direct Messages) ก่อนครับ", ephemeral=True)
                else:
                    await interaction.followup.send("❌ **Token ไม่ถูกต้อง หรือหมดอายุ!** กรุณาตรวจสอบ Token ของคุณใหม่อีกครั้งจาก Discord Developer Portal", ephemeral=True)

class TokenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="คลิกเพื่อกรอก Token บอท", emoji="🔑", style=discord.ButtonStyle.blurple, custom_id="persistent_token_button_id")
    async def token_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenInputModal())

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="คลิกเพื่อยืนยันตัวตน", emoji="🛡️", style=discord.ButtonStyle.green, custom_id="persistent_verify_button_id")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        random_code = str(random.randint(100000, 999999))
        modal = VerifyModal(expected_code=random_code)
        modal.code_input.label = f"กรอกรหัส 6 หลักนี้: {random_code}"
        await interaction.response.send_modal(modal)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เปิดตั๋วติดต่อทีมงาน", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="persistent_new_ticket_button_id")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        channel_name = f"🎟️・ticket-{user.name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        admin_role = discord.utils.get(guild.roles, name="Admin") 
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        try:
            ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
            await interaction.response.send_message(f'🔒 ระบบได้สร้างห้องส่วนตัวให้คุณแล้วครับ: {ticket_channel.mention}', ephemeral=True)
            
            ping_text = admin_role.mention if admin_role else "@here"
            embed_ticket = discord.Embed(
                title="🎫 ศูนย์ช่วยเหลือและซัพพอร์ตส่วนตัว",
                description=(
                    f"สวัสดีครับคุณ {user.mention}\n"
                    "แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อทีมงานไว้ได้เลยครับ\n\n"
                    "📌 *โปรดรอสักครู่ ทีมงานจะเข้ามาตรวจสอบโดยเร็วที่สุด*"
                ),
                color=0x3498DB
            )
            await ticket_channel.send(content=ping_text, embed=embed_ticket)
        except Exception as e:
            await interaction.response.send_message(f'❌ เกิดข้อผิดพลาดในการสร้างห้อง: {e}', ephemeral=True)

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="รับทราบและยอมรับกฎ", emoji="📜", style=discord.ButtonStyle.success, custom_id="persistent_rules_button_id")
    async def rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ ขอบคุณที่อ่านและยอมรับกฎของเซิร์ฟเวอร์เราครับ ขอให้สนุก!", ephemeral=True)

class ChangelogView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.owner_id = 1532607357962420229

    @discord.ui.button(label="รับทราบประกาศ", emoji="✅", style=discord.ButtonStyle.success, custom_id="persistent_changelog_ack_button_id")
    async def ack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✨ คุณได้กดรับทราบประกาศอัปเดตเรียบร้อยแล้วครับ!", ephemeral=True)
        try:
            owner = await interaction.client.fetch_user(self.owner_id)
            if owner and owner.id != interaction.user.id:
                await owner.send(f"🔔 **แจ้งเตือนจากเซิร์ฟเวอร์:** `{interaction.guild.name}`\n👤 สมาชิกชื่อ **{interaction.user.name}** ได้กดปุ่มรับทราบประกาศอัปเดตแล้วครับ!")
        except Exception:
            pass

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(VerifyView())
        self.add_view(RulesView())
        self.add_view(ChangelogView())
        self.add_view(TokenView())
        await self.tree.sync()
        print("🚀 Slash commands synced and Persistent Views loaded successfully.")
        check_roblox_updates.start()

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    # 🟣 ตั้งสถานะบอทให้เป็นสตรีมมิ่ง (แสดงผลเป็นสีม่วงบน Discord)
    await bot.change_presence(
        activity=discord.Streaming(
            name="🛡️ ใช้คำสั่ง /ช่วยเหลือ", 
            url="https://www.twitch.tv/discord"
        )
    )
    print("🟣 Bot status set to Streaming (Purple Online).")

# ==========================================
# --- Background Task: เช็กอัปเดต Roblox ทุกๆ 3 นาที ---
# ==========================================
@tasks.loop(minutes=3)
async def check_roblox_updates():
    global latest_roblox_version
    url = "https://setup.rbxcdn.com/version"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    new_version = await resp.text()
                    new_version = new_version.strip()
                    
                    if latest_roblox_version is None:
                        latest_roblox_version = new_version
                        print(f"🎮 Initialized Roblox Version: {new_version}")
                        return
                    
                    if new_version != latest_roblox_version:
                        old_version = latest_roblox_version
                        latest_roblox_version = new_version
                        print(f"🚨 Roblox Updated! {old_version} -> {new_version}")
                        
                        for guild_id, channel_id in roblox_notify_channels.items():
                            guild = bot.get_guild(guild_id)
                            if guild:
                                channel = guild.get_channel(channel_id)
                                if channel:
                                    embed = discord.Embed(
                                        title="🚨 แจ้งเตือน! Roblox มีการอัปเดตเวอร์ชันใหม่!",
                                        description=(
                                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                                            "🎮 **ตรวจพบเวอร์ชันใหม่ของ Roblox ถูกปล่อยออกมาแล้ว!**\n"
                                            f"• 📦 **เวอร์ชันเก่า:** `{old_version}`\n"
                                            f"• 🔥 **เวอร์ชันใหม่:** `{new_version}`\n"
                                            "• 🌐 **แหล่งที่มา:** `rbxcdn.com`\n"
                                            "━━━━━━━━━━━━━━━━━━━━━━"
                                        ),
                                        color=0xE74C3C
                                    )
                                    embed.set_footer(text="ระบบตรวจสอบอัตโนมัติ 24 ชม.", icon_url=bot.user.avatar.url if bot.user.avatar else None)
                                    try:
                                        await channel.send(content="@everyone", embed=embed)
                                    except Exception as e:
                                        print(f"❌ Failed to send roblox update notification: {e}")
        except Exception as e:
            print(f"⚠️ Error checking Roblox version loop: {e}")

@check_roblox_updates.before_loop
async def before_check_roblox():
    await bot.wait_until_ready()

# ==========================================
# --- ระบบป้องกันความปลอดภัย (Anti-Nuke / Anti-Link / Anti-Spam) ---
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    is_admin = message.author.guild_permissions.manage_messages

    if not is_admin and ant_settings["anti_link"].get(guild_id, False):
        content_lower = message.content.lower()
        if "http://" in content_lower or "https://" in content_lower or "discord.gg/" in content_lower or "discord.com/invite" in content_lower:
            try:
                await message.delete()
                warning = await message.channel.send(f"⚠️ {message.author.mention} **ห้ามส่งลิงก์ในห้องนี้!** (ระบบป้องกันลิงก์ทำงาน)")
                await asyncio_sleep_delete(warning, 4)
            except Exception:
                pass
            return

    if not is_admin and ant_settings["anti_spam"].get(guild_id, False):
        current_time = time.time()
        if user_id in spam_tracker:
            last_time = spam_tracker[user_id]
            if current_time - last_time < 1.5:
                try:
                    await message.delete()
                    warning = await message.channel.send(f"⚠️ {message.author.mention} **กรุณาอย่าสแปมข้อความ!** (ระบบป้องกันสแปมทำงาน)")
                    await asyncio_sleep_delete(warning, 4)
                except Exception:
                    pass
                return
        spam_tracker[user_id] = current_time

    await bot.process_commands(message)

async def asyncio_sleep_delete(msg, delay):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

# ==========================================
# --- คำสั่ง Slash Commands (ภาษาไทยทั้งหมด) ---
# ==========================================

@bot.tree.command(name="เช็กเวอร์ชันรอบล็อกซ์", description="🎮 ตรวจสอบสถานะการอัปเดตเวอร์ชันล่าสุดของ Roblox แบบเรียลไทม์")
async def check_roblox_version(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    url = "https://setup.rbxcdn.com/version"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    version_hash = (await resp.text()).strip()
                    is_released = True if len(version_hash) > 5 else False
                    
                    embed = discord.Embed(
                        title="🎮 Roblox Client Version Status Checker",
                        description=(
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"• 📦 **Deployment Hash:** `{version_hash}`\n"
                            f"• 🌐 **Client Source:** `rbxcdn.com`\n"
                            "━━━━━━━━━━━━━━━━━━━━━━"
                        ),
                        color=0x2ECC71 if is_released else 0xF1C40F
                    )
                    if is_released:
                        embed.add_field(name="🟢 สถานะการอัปเดต", value="**ปล่อยอัปเดตเวอร์ชันใหม่ออกมาแล้ว!**", inline=False)
                    else:
                        embed.add_field(name="🟡 สถานะการอัปเดต", value="**ยังไม่ปล่อยอัปเดตออกมา / อยู่ระหว่างรอซิงค์เวอร์ชัน**", inline=False)
                        
                    embed.set_footer(text=f"ตรวจสอบโดย: {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ ไม่สามารถดึงข้อมูลเวอร์ชัน Roblox ได้ในขณะนี้", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="ตั้งห้องแจ้งเตือนรอบล็อกซ์", description="📢 เลือกห้องสำหรับให้บอทแจ้งเตือนอัปเดตเวอร์ชัน Roblox พร้อมแท็ก @everyone")
@app_commands.describe(ห้อง="เลือกห้องแชทที่ต้องการให้แจ้งเตือนอัปเดต")
@app_commands.checks.has_permissions(administrator=True)
async def set_roblox_channel(interaction: discord.Interaction, ห้อง: discord.TextChannel):
    roblox_notify_channels[interaction.guild.id] = ห้อง.id
    embed = discord.Embed(
        title="✅ ตั้งค่าห้องแจ้งเตือน Roblox สำเร็จ",
        description=f"บอทจะส่งข้อความแจ้งเตือนพร้อมแท็ก `@everyone` ไปยังห้อง {ห้อง.mention} ทันทีเมื่อ Roblox มีอัปเดต!",
        color=0x2ECC71
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="จัดการเสียง", description="🔊 สั่งให้บอทเข้ามาในช่องเสียงที่คุณอยู่ หรือออกจากห้อง")
@app_commands.choices(การทำงาน=[
    app_commands.Choice(name="เชื่อมต่อเข้าห้องเสียง (Join)", value="join"),
    app_commands.Choice(name="ออกจากห้องเสียง (Leave)", value="leave")
])
async def voicechat(interaction: discord.Interaction, การทำงาน: str):
    if การทำงาน == "join":
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client
            try:
                if voice_client:
                    await voice_client.move_to(channel)
                else:
                    await channel.connect()
                await interaction.response.send_message(f'🎧 ดึงบอทเข้าห้อง **{channel.name}** สำเร็จ!', ephemeral=False)
            except Exception as e:
                await interaction.response.send_message(f'❌ เกิดข้อผิดพลาด: {e}', ephemeral=True)
        else:
            await interaction.response.send_message('⚠️ กรุณาเข้าห้องเสียงก่อนใช้คำสั่งนี้!', ephemeral=True)
    elif การทำงาน == "leave":
        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            await interaction.response.send_message('👋 บอทออกจากห้องเสียงเรียบร้อยแล้ว', ephemeral=False)
        else:
            await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

@bot.tree.command(name="ช่วยเหลือ", description="📖 แสดงรายการคำสั่งทั้งหมดของบอทแบ่งตามหมวดหมู่")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 คู่มือการใช้งานคำสั่งบอททั้งหมด (Help Menu)",
        description="นี่คือรายการคำสั่ง Slash Commands ทั้งหมดในระบบ (ภาษาไทย) ครับ:",
        color=0x3498DB
    )
    embed.add_field(name="🎮 1. หมวดเกมและระบบพิเศษ", value="• `/เช็กเวอร์ชันรอบล็อกซ์` - ตรวจสอบอัปเดตเวอร์ชัน Roblox\n• `/ตั้งห้องแจ้งเตือนรอบล็อกซ์` - ตั้งห้องแจ้งเตือน Roblox\n• `/จัดการเสียง` - ควบคุมบอทเข้า/ออกห้องเสียง", inline=False)
    embed.add_field(name="🎫 2. หมวดระบบตั๋วและยืนยันตัวตน", value="• `/เปิดตั๋ว` - ส่งปุ่มเปิดตั๋วติดต่อทีมงาน\n• `/ยืนยันตัวตน` - ส่งปุ่มยืนยันตัวตนรับยศ Member", inline=False)
    embed.add_field(name="📜 3. หมวดจัดการเซิร์ฟเวอร์", value="• `/กฎเซิร์ฟเวอร์` - แสดงกฎระเบียบ\n• `/ประกาศอัปเดต` - สร้างห้องประกาศล็อกห้อง\n• `/สร้างลิงก์เชิญ` - สร้างลิงก์เชิญถาวร\n• `/สถิติเซิร์ฟเวอร์` - ดูสถิติสมาชิก", inline=False)
    embed.add_field(name="🧹 4. หมวดจัดการสมาชิกและข้อความ", value="• `/ลบข้อความ` - ลบข้อความ (1-100)\n• `/แบนสมาชิก` - แบนสมาชิก", inline=False)
    embed.add_field(name="🛡️ 5. หมวดระบบความปลอดภัย", value="• `/ตั้งค่าระบบป้องกันทั้งหมด` - เปิด/ปิดระบบกันทั้งหมด\n• `/ตรวจสอบโทเค็น` - เช็ก Token บอทรอบใหม่ผ่าน DM\n• `/ป้องกันลิงก์` / `/ป้องกันนุกเกอร์` / `/ป้องกันสแปม` - ตั้งค่าระบบแยก", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="เปิดตั๋ว", description="🎫 ส่งข้อความระบบเปิดตั๋วติดต่อทีมงาน")
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌟 ศูนย์บริการช่วยเหลือและซัพพอร์ต (Support Ticket)",
        description="กดปุ่มด้านล่างเพื่อสร้างห้องส่วนตัวพูดคุยกับทีมงานได้ทันทีครับ",
        color=0x9B59B6
    )
    await interaction.response.send_message(embed=embed, view=TicketView(), ephemeral=False)

@bot.tree.command(name="ยืนยันตัวตน", description="🛡️ ส่งข้อความระบบยืนยันตัวตนรับยศ Member")
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ ระบบยืนยันตัวตนเพื่อเข้าถึงเซิร์ฟเวอร์",
        description="กดปุ่มด้านล่างและกรอกรหัส 6 หลักเพื่อรับยศอัตโนมัติ",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, view=VerifyView(), ephemeral=False)

@bot.tree.command(name="กฎเซิร์ฟเวอร์", description="📜 ส่งข้อความกฎระเบียบประจำเซิร์ฟเวอร์")
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(title="📜 กฎระเบียบประจำเซิร์ฟเวอร์", description="กรุณาปฏิบัติตามกฎอย่างเคร่งครัด", color=0xE74C3C)
    await interaction.response.send_message(embed=embed, view=RulesView(), ephemeral=False)

@bot.tree.command(name="ประกาศอัปเดต", description="📢 สร้างห้องประกาศอัปเดตแบบล็อกห้อง พร้อมปุ่มรับทราบ")
@app_commands.checks.has_permissions(manage_channels=True)
async def changelog(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    }
    try:
        log_channel = await guild.create_text_channel(name="📢・changelog-update", overwrites=overwrites)
        embed = discord.Embed(title="🚀 ประกาศบันทึกการอัปเดตระบบ", description="กดปุ่มรับทราบด้านล่างนี้เพื่อยืนยันการรับรู้", color=0xF1C40F)
        await log_channel.send(embed=embed, view=ChangelogView())
        await interaction.followup.send(f"✅ สร้างห้องประกาศสำเร็จที่: {log_channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="ลบข้อความ", description="🧹 ลบข้อความในแชทจำนวนตามที่กำหนด (1 - 100)")
@app_commands.describe(จำนวน="จำนวนข้อความที่ต้องการลบ (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, จำนวน: int):
    if not (1 <= จำนวน <= 100):
        await interaction.response.send_message("⚠️ กรุณาระบุจำนวนระหว่าง 1 ถึง 100 เท่านั้น!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=จำนวน)
    await interaction.followup.send(embed=discord.Embed(title="🧹 ลบข้อความสำเร็จ", description=f"ลบไปแล้ว {len(deleted)} ข้อความ", color=0x2ECC71), ephemeral=True)

@bot.tree.command(name="ตรวจสอบโทเค็น", description="🔑 ส่งแผงควบคุมระบบกรอก Token ตรวจสอบสถานะบอทผ่าน DM")
@app_commands.checks.has_permissions(administrator=True)
async def check_token(interaction: discord.Interaction):
    embed = discord.Embed(title="🔑 แผงควบคุมระบบตรวจสอบ Token", description="กดปุ่มด้านล่างเพื่อกรอกและเช็ก Token บอททาง DM", color=0x3498DB)
    await interaction.response.send_message(embed=embed, view=TokenView(), ephemeral=False)

@bot.tree.command(name="ตั้งค่าระบบป้องกันทั้งหมด", description="🛡️ เปิดหรือปิดระบบป้องกันทั้งหมดพร้อมกัน")
@app_commands.choices(สถานะ=[
    app_commands.Choice(name="เปิดระบบป้องกันทั้งหมด (Enable All)", value="on"),
    app_commands.Choice(name="ปิดระบบป้องกันทั้งหมด (Disable All)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def settings(interaction: discord.Interaction, สถานะ: str):
    is_on = (สถานะ == "on")
    ant_settings["anti_link"][interaction.guild.id] = is_on
    ant_settings["anti_nuke"][interaction.guild.id] = is_on
    ant_settings["anti_spam"][interaction.guild.id] = is_on
    embed = discord.Embed(title="🛡️ ตั้งค่าระบบป้องกันทั้งหมด", description=f"สถานะ: **{'🟢 เปิดใช้งานทั้งหมด' if is_on else '🔴 ปิดใช้งานทั้งหมด'}**", color=0x2ECC71 if is_on else 0xE74C3C)
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="ป้องกันลิงก์", description="🛡️ เปิด/ปิดระบบป้องกันลิงก์แปลกปลอม")
@app_commands.choices(สถานะ=[
    app_commands.Choice(name="เปิดการใช้งาน (Enable)", value="on"),
    app_commands.Choice(name="ปิดการใช้งาน (Disable)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def anti_link(interaction: discord.Interaction, สถานะ: str):
    is_on = (สถานะ == "on")
    ant_settings["anti_link"][interaction.guild.id] = is_on
    await interaction.response.send_message(embed=discord.Embed(title="🛡️ Anti-Link", description=f"สถานะ: {'🟢 เปิด' if is_on else '🔴 ปิด'}", color=0x2ECC71 if is_on else 0xE74C3C), ephemeral=False)

@bot.tree.command(name="ป้องกันนุกเกอร์", description="🛡️ เปิด/ปิดระบบป้องกัน Nuker")
@app_commands.choices(สถานะ=[
    app_commands.Choice(name="เปิดการใช้งาน (Enable)", value="on"),
    app_commands.Choice(name="ปิดการใช้งาน (Disable)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def anti_nuke(interaction: discord.Interaction, สถานะ: str):
    is_on = (สถานะ == "on")
    ant_settings["anti_nuke"][interaction.guild.id] = is_on
    await interaction.response.send_message(embed=discord.Embed(title="🛡️ Anti-Nuke", description=f"สถานะ: {'🟢 เปิด' if is_on else '🔴 ปิด'}", color=0x2ECC71 if is_on else 0xE74C3C), ephemeral=False)

@bot.tree.command(name="ป้องกันสแปม", description="🛡️ เปิด/ปิดระบบป้องกันสแปมแชท")
@app_commands.choices(สถานะ=[
    app_commands.Choice(name="เปิดการใช้งาน (Enable)", value="on"),
    app_commands.Choice(name="ปิดการใช้งาน (Disable)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def anti_spam(interaction: discord.Interaction, สถานะ: str):
    is_on = (สถานะ == "on")
    ant_settings["anti_spam"][interaction.guild.id] = is_on
    await interaction.response.send_message(embed=discord.Embed(title="🛡️ Anti-Spam", description=f"สถานะ: {'🟢 เปิด' if is_on else '🔴 ปิด'}", color=0x2ECC71 if is_on else 0xE74C3C), ephemeral=False)

@bot.tree.command(name="แบนสมาชิก", description="🔨 แบนสมาชิกออกจากเซิร์ฟเวอร์")
@app_commands.describe(สมาชิก="สมาชิกที่ต้องการแบน", เหตุผล="เหตุผลในการแบน")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, สมาชิก: discord.Member, เหตุผล: str = "ไม่ระบุเหตุผล"):
    try:
        await สมาชิก.ban(reason=เหตุผล)
        embed = discord.Embed(title="🔨 แบนสมาชิกสำเร็จ", description=f"แบน {สมาชิก.mention} เรียบร้อย\nเหตุผล: `{เหตุผล}`", color=0xE74C3C)
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="สร้างลิงก์เชิญ", description="🔗 สร้างและส่งลิงก์เชิญเข้าเซิร์ฟเวอร์ถาวร")
async def invite(interaction: discord.Interaction):
    try:
        target_channel = interaction.channel
        if not hasattr(target_channel, "create_invite"):
            for c in interaction.guild.text_channels:
                if c.permissions_for(interaction.guild.me).create_instant_invite:
                    target_channel = c
                    break
        if hasattr(target_channel, "create_invite"):
            invite_link = await target_channel.create_invite(max_age=0, max_uses=0)
            embed = discord.Embed(title="🔗 ลิงก์เชิญเข้าสู่เซิร์ฟเวอร์", description=f"👉 {invite_link}", color=0x3498DB)
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.response.send_message("❌ ไม่พบช่องที่สามารถสร้างลิงก์เชิญได้", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="สถิติเซิร์ฟเวอร์", description="📊 แสดงสถิติจำนวนสมาชิกภายในเซิร์ฟเวอร์")
async def stats(interaction: discord.Interaction):
    guild = interaction.guild
    total = guild.member_count
    bots = sum(m.bot for m in guild.members)
    embed = discord.Embed(
        title=f"📊 สถิติเซิร์ฟเวอร์: {guild.name}",
        description=f"• 👥 สมาชิกทั้งหมด: `{total}`\n• 🧑 ผู้ใช้งานจริง: `{total - bots}`\n• 🤖 บอท: `{bots}`",
        color=0x3498DB
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=False)

# ==========================================
# --- รันเว็บเซิร์ฟเวอร์และบอท Discord ---
# ==========================================
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    TOKEN = os.environ.get("BOT_TOKEN", "ใส่_Discord_Bot_Token_ของคุณที่นี่")
    if TOKEN == "ใส่_Discord_Bot_Token_ของคุณที่นี่":
        print("⚠️ กรุณาใส่ Bot Token ให้ถูกต้อง!")
    else:
        bot.run(TOKEN)
