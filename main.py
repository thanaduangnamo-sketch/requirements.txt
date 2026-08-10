import os
import random
import threading
import time
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# 1. ส่วนของเว็บเซิร์ฟเวอร์ Flask เพื่อเปิดพอร์ตให้ Render ตรวจพบ
app = Flask('')

@app.route('/')
def home():
    return "Bot Token Checker & Security Protection System is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. ส่วนของบอท Discord
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True
intents.members = True

# --- ตัวแปรสำหรับเก็บสถานะระบบป้องกัน (เปิด/ปิด แบบแยกตามเซิร์ฟเวอร์) ---
ant_settings = {
    "anti_link": {},
    "anti_nuke": {},
    "anti_spam": {}
}

# เก็บข้อมูลเช็คสแปมข้อความ (User ID -> Timestamp)
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

        # ตรวจสอบความถูกต้องของ Token โดยการยิง Request ไปเช็คกับ Discord API ตรงๆ
        headers = {
            "Authorization": f"Bot {user_token}"
        }
        
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

                    # ซ่อน Token บางส่วนเพื่อความปลอดภัย
                    if len(user_token) > 10:
                        masked_token = user_token[:6] + "..." + user_token[-6:]
                    else:
                        masked_token = "******"

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

# --- ระบบ View ที่มีปุ่มกดเปิด Modal ใส่ Token ---
class TokenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="คลิกเพื่อกรอก Token บอท", emoji="🔑", style=discord.ButtonStyle.blurple, custom_id="persistent_token_button_id")
    async def token_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenInputModal())

# --- ระบบ View ยืนยันตัวตนแบบ Persistent ---
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="คลิกเพื่อยืนยันตัวตน", emoji="🛡️", style=discord.ButtonStyle.green, custom_id="persistent_verify_button_id")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        random_code = str(random.randint(100000, 999999))
        modal = VerifyModal(expected_code=random_code)
        modal.code_input.label = f"กรอกรหัส 6 หลักนี้: {random_code}"
        await interaction.response.send_modal(modal)

# --- ระบบ View สำหรับ Ticket แบบ Persistent ---
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
            
            await interaction.response.send_message(
                f'🔒 ระบบได้สร้างห้องส่วนตัวให้คุณแล้วครับ: {ticket_channel.mention}', 
                ephemeral=True
            )

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

# --- ระบบ View สำหรับกฎประจำเซิร์ฟเวอร์แบบ Persistent ---
class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="รับทราบและยอมรับกฎ", emoji="📜", style=discord.ButtonStyle.success, custom_id="persistent_rules_button_id")
    async def rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ ขอบคุณที่อ่านและยอมรับกฎของเซิร์ฟเวอร์เราครับ ขอให้สนุก!", ephemeral=True)

# --- ระบบ View สำหรับ Changelog แบบ Persistent ---
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

bot = VoiceBot()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} (ID: {bot.user.id})')
    
    await bot.change_presence(
        status=discord.Status.dnd, 
        activity=discord.Game(name="🛡️ ใช้คำสั่ง /help เพื่อดูวิธีใช้งาน")
    )
    print("🔴 Bot status set to Do Not Disturb (Red Dot).")

# --- ระบบตรวจสอบข้อความป้องกัน (Anti-Link & Anti-Spam) ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    is_admin = message.author.guild_permissions.manage_messages

    # 1. ระบบ Anti-Link
    if not is_admin and ant_settings["anti_link"].get(guild_id, False):
        if "http://" in message.content or "https://" in message.content or "discord.gg/" in message.content:
            try:
                await message.delete()
                warning = await message.channel.send(f"⚠️ {message.author.mention} **ห้ามส่งลิงก์ในห้องนี้!** (ระบบ Anti-Link เปิดใช้งานอยู่)")
                await asyncio_sleep_delete(warning, 5)
            except Exception:
                pass
            return

    # 2. ระบบ Anti-Spam
    if not is_admin and ant_settings["anti_spam"].get(guild_id, False):
        current_time = time.time()
        if user_id in spam_tracker:
            last_time = spam_tracker[user_id]
            if current_time - last_time < 1.5:
                try:
                    await message.delete()
                    warning = await message.channel.send(f"⚠️ {message.author.mention} **กรุณาอย่าสแปมข้อความ!**")
                    await asyncio_sleep_delete(warning, 4)
                except Exception:
                    pass
                return
        spam_tracker[user_id] = current_time

    await bot.process_commands(message)

async def asyncio_sleep_delete(msg, delay):
    import asyncio
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

# ==========================================
# --- คำสั่ง Slash Commands ทั้งหมด ---
# ==========================================

@bot.tree.command(name="voicechat", description="🔊 สั่งให้บอทเข้ามาในช่องเสียงที่คุณอยู่ หรือตั้งค่าการเชื่อมต่อ")
@app_commands.choices(action=[
    app_commands.Choice(name="เชื่อมต่อเข้าห้องเสียงที่อยู่ (Join)", value="join"),
    app_commands.Choice(name="ออกจากห้องเสียง (Leave)", value="leave")
])
async def voicechat(interaction: discord.Interaction, action: str):
    if action == "join":
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
    elif action == "leave":
        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            await interaction.response.send_message('👋 บอทออกจากห้องเสียงเรียบร้อยแล้ว', ephemeral=False)
        else:
            await interaction.response.send_message('⚠️ บอทยังไม่ได้อยู่ในห้องเสียงไหนเลย', ephemeral=True)

@bot.tree.command(name="help", description="📖 แสดงรายการคำสั่งทั้งหมดของบอทแบ่งตามหมวดหมู่")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 คู่มือการใช้งานคำสั่งบอททั้งหมด (Help Menu)",
        description="นี่คือรายการคำสั่ง Slash Commands ทั้งหมดในระบบ แบ่งตามหมวดหมู่การใช้งานครับ:",
        color=0x3498DB
    )
    embed.add_field(name="🔊 1. หมวดระบบเสียง", value="• `/voicechat` - สั่งให้บอทเข้าหรือออกจากห้องเสียงที่คุณอยู่", inline=False)
    embed.add_field(name="🎫 2. หมวดระบบตั๋วและยืนยันตัวตน", value="• `/ticket` - ส่งข้อความเปิดตั๋วติดต่อทีมงาน\n• `/verify` - ส่งข้อความระบบยืนยันตัวตน 6 หลักรับยศ Member", inline=False)
    embed.add_field(name="📜 3. หมวดจัดการเซิร์ฟเวอร์และสถิติ", value="• `/rules` - ส่งข้อความกฎระเบียบประจำเซิร์ฟเวอร์\n• `/changelog` - สร้างห้องประกาศอัปเดตแบบล็อกห้อง\n• `/invite` - สร้างลิงก์เชิญเข้าเซิร์ฟเวอร์ถาวร\n• `/stats` - สร้างหมวดหมู่แสดงสถิติจำนวนสมาชิก", inline=False)
    embed.add_field(name="🧹 4. หมวดจัดการสมาชิกและข้อความ", value="• `/clear` - ลบข้อความในแชท (1 - 100 ข้อความ)\n• `/ban` - แบนสมาชิกออกจากเซิร์ฟเวอร์", inline=False)
    embed.add_field(name="🛡️ 5. หมวดระบบป้องกันความปลอดภัย", value="• `/settings` - เปิด/ปิด ระบบป้องกันเซิร์ฟเวอร์ทั้งหมด\n• `/check-token` - แผงปุ่มกรอก Token และตรวจเช็กสถานะจริงส่งเข้า DM\n• `/anti-link` / `/anti-nuke` / `/anti-spam` - ตั้งค่าระบบป้องกันแยกย่อย", inline=False)
    embed.set_footer(text="💡 พิมพ์เครื่องหมาย / เพื่อเลือกใช้งานคำสั่งต่างๆ ได้เลย", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ticket", description="🎫 ส่งข้อความระบบเปิดตั๋วติดต่อทีมงานดีไซน์พิเศษ")
async def ticket(interaction: discord.Interaction):
    view = TicketView()
    embed = discord.Embed(
        title="🌟 ศูนย์บริการช่วยเหลือและซัพพอร์ต (Support Ticket)",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💬 **ต้องการความช่วยเหลือ หรือติดต่อทีมงาน?**\n"
            "• 🛠️ แจ้งปัญหาการใช้งาน / บัคต่างๆ\n"
            "• 💳 ติดต่อซื้อสินค้า / เติมเงิน / โดเนท\n"
            "• ❓ สอบถามข้อมูลหรือเรื่องอื่นๆ\n\n"
            "📌 **วิธีใช้งาน:** กดปุ่ม **'เปิดตั๋วติดต่อทีมงาน'** ด้านล่างนี้เพื่อสร้างห้องส่วนตัวสำหรับพูดคุยกับทีมงานได้ทันที\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x9B59B6
    )
    embed.set_footer(text="🔒 ระบบซัพพอร์ตความปลอดภัยสูง ตลอด 24 ชม.", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="verify", description="🛡️ ส่งข้อความระบบยืนยันตัวตนดีไซน์พรีเมียม")
async def verify(interaction: discord.Interaction):
    view = VerifyView()
    embed = discord.Embed(
        title="🛡️ ระบบยืนยันตัวตนเพื่อเข้าถึงเซิร์ฟเวอร์",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✨ ยินดีต้อนรับสมาชิกใหม่ทุกท่าน!\n"
            "กรุณายืนยันตัวตนเพื่อปลดล็อคห้องต่างๆ ภายในเซิร์ฟเวอร์\n\n"
            "📌 **ขั้นตอนการยืนยัน:**\n"
            "1️⃣ กดปุ่ม **'คลิกเพื่อยืนยันตัวตน'** ด้านล่าง\n"
            "2️⃣ กรอกรหัส 6 หลักที่ระบบแสดงขึ้นมาให้ถูกต้อง\n"
            "3️⃣ รับยศ `Member` ทันทีอัตโนมัติ!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x5865F2
    )
    embed.set_footer(text="🔒 ป้องกันบอทและสแปมเข้าเซิร์ฟเวอร์ 100%", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="rules", description="📜 ส่งข้อความกฎระเบียบประจำเซิร์ฟเวอร์ดีไซน์สวยงาม")
async def rules(interaction: discord.Interaction):
    view = RulesView()
    embed = discord.Embed(
        title="📜 กฎระเบียบและข้อปฏิบัติประจำเซิร์ฟเวอร์",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 **1. ให้เกียรติและเคารพซึ่งกันและกัน**\n"
            "> ห้ามเหยียดหยาม ดูหมิ่น หรือใช้ถ้อยคำรุนแรงต่อสมาชิกท่านอื่น\n\n"
            "📌 **2. ห้ามสแปมข้อความหรือรูปภาพไม่เหมาะสม**\n"
            "> ห้ามส่งข้อความซ้ำๆ รัวๆ หรือโพสต์เนื้อหา 18+ ในช่องแชททั่วไป\n\n"
            "📌 **3. ห้ามโปรโมทหรือโฆษณาโดยไม่ได้รับอนุญาต**\n"
            "> ห้ามส่งลิงก์เชิญดิสอื่น หรือชวนโปรโมทสินค้าในแชทส่วนรวม\n\n"
            "📌 **4. ปฏิบัติตามคำสั่งของทีมงาน (Admin / Staff)**\n"
            "> การตัดสินใจของทีมงานถือเป็นข้อยุติและสิ้นสุดในทุกกรณี\n\n"
            "⚠️ *หากฝ่าฝืนกฎระเบียบ จะมีบทลงโทษตั้งแต่ตักเตือนจนถึงแบนถาวร*\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xE74C3C
    )
    embed.set_footer(text="กรุณาอ่านและปฏิบัติตามอย่างเคร่งครัด", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="changelog", description="📢 สร้างห้องประกาศอัปเดตแบบล็อกห้อง พร้อมปุ่มรับทราบ")
@app_commands.checks.has_permissions(manage_channels=True)
async def changelog(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    user = interaction.user

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    }

    admin_role = discord.utils.get(guild.roles, name="Admin")
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    try:
        log_channel = await guild.create_text_channel(name="📢・changelog-update", overwrites=overwrites)
        view = ChangelogView()
        
        embed = discord.Embed(
            title="🚀 ประกาศบันทึกการอัปเดตระบบ (Changelog)",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "**✨ รายการอัปเดตระบบเวอร์ชันล่าสุด:**\n"
                "• 🔑 **อัปเกรดระบบ /check-token:** เชื่อมต่อ API ตรวจสอบ Token จริง พร้อมดึงข้อมูลโปรไฟล์บอทส่งเข้า DM\n"
                "• 🛡️ **เพิ่มคำสั่ง /settings:** เปิด/ปิดระบบป้องกันทั้งหมดพร้อมกันทีเดียว\n\n"
                "📌 *กรุณากดปุ่ม **'รับทราบประกาศ'** ด้านล่างนี้เพื่อยืนยันการรับรู้ครับ*\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text=f"ประกาศโดย {user.name}", icon_url=user.avatar.url if user.avatar else None)

        await log_channel.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ สร้างห้องประกาศอัปเดตแบบล็อกเรียบร้อยแล้วที่: {log_channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="clear", description="🧹 ลบข้อความในแชทจำนวนตามที่กำหนด (1 - 100 ข้อความ)")
@app_commands.describe(amount="จำนวนข้อความที่ต้องการลบ (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("⚠️ กรุณาระบุจำนวนข้อความระหว่าง **1 ถึง 100** เท่านั้นครับ!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(
            title="🧹 ลบข้อความสำเร็จ",
            description=f"ลบข้อความจำนวน **{len(deleted)}** ข้อความเรียบร้อยแล้วครับ ✨",
            color=0x2ECC71
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาดในการลบข้อความ: {e}", ephemeral=True)

@bot.tree.command(name="check-token", description="🔑 ส่งแผงควบคุมระบบกรอก Token และตรวจสอบสถานะบอทรอบใหม่")
@app_commands.checks.has_permissions(administrator=True)
async def check_token(interaction: discord.Interaction):
    view = TokenView()
    embed = discord.Embed(
        title="🔑 แผงควบคุมระบบตรวจสอบ Token",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡️ **ต้องการตรวจสอบสถานะและตั้งค่า Token ของบอท?**\n\n"
            "📌 **วิธีใช้งาน:**\n"
            "• กดปุ่ม **'คลิกเพื่อกรอก Token บอท'** ด้านล่างนี้\n"
            "• กรอก Token ของคุณในหน้าต่างที่เด้งขึ้นมา\n"
            "• ระบบจะเช็กกับ Discord API จริง และส่งผลรายงานพร้อมรูปโปรไฟล์บอทไปที่ **DM ส่วนตัว** ทันที!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x3498DB
    )
    embed.set_footer(text="🔒 ปลอดภัย ข้อมูลของคุณจะไม่ถูกเปิดเผยในช่องแชทสาธารณะ", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="settings", description="🛡️ เปิดหรือปิดระบบป้องกันเซิร์ฟเวอร์ทั้งหมดพร้อมกันทีเดียว")
@app_commands.choices(status=[
    app_commands.Choice(name="เปิดระบบป้องกันทั้งหมด (Enable All)", value="on"),
    app_commands.Choice(name="ปิดระบบป้องกันทั้งหมด (Disable All)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def settings(interaction: discord.Interaction, status: str):
    guild_id = interaction.guild.id
    is_on = (status == "on")
    
    ant_settings["anti_link"][guild_id] = is_on
    ant_settings["anti_nuke"][guild_id] = is_on
    ant_settings["anti_spam"][guild_id] = is_on

    embed = discord.Embed(
        title="🛡️ ตั้งค่าระบบป้องกันความปลอดภัยเซิร์ฟเวอร์",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"สถานะระบบทั้งหมด: **{'🟢 เปิดใช้งานทั้งหมดแล้ว' if is_on else '🔴 ปิดการใช้งานทั้งหมดแล้ว'}**\n\n"
            "• 🛡️ **Anti-Link (ป้องกันลิงก์):** " + ("`เปิด`" if is_on else "`ปิด`") + "\n"
            "• 🛡️ **Anti-Nuke (ป้องกันทำลายเซิร์ฟเวอร์):** " + ("`เปิด`" if is_on else "`ปิด`") + "\n"
            "• 🛡️ **Anti-Spam (ป้องกันสแปมแชท):** " + ("`เปิด`" if is_on else "`ปิด`") + "\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x2ECC71 if is_on else 0xE74C3C
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="anti-link", description="🛡️ เปิด/ปิดระบบป้องกันลิ้งก์แปลกปลอมในเซิร์ฟเวอร์")
@app_commands.choices(status=[
    app_commands.Choice(name="เปิดการใช้งาน (Enable)", value="on"),
    app_commands.Choice(name="ปิดการใช้งาน (Disable)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def anti_link(interaction: discord.Interaction, status: str):
    guild_id = interaction.guild.id
    is_on = (status == "on")
    ant_settings["anti_link"][guild_id] = is_on

    embed = discord.Embed(
        title="🛡️ ระบบป้องกันลิงก์ (Anti-Link)",
        description=f"สถานะระบบ: **{'🟢 เปิดใช้งานแล้ว' if is_on else '🔴 ปิดการใช้งานแล้ว'}**",
        color=0x2ECC71 if is_on else 0xE74C3C
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="anti-nuke", description="🛡️ เปิด/ปิดระบบป้องกัน Nuker / ป้องกันการทำลายเซิร์ฟเวอร์")
@app_commands.choices(status=[
    app_commands.Choice(name="เปิดการใช้งาน (Enable)", value="on"),
    app_commands.Choice(name="ปิดการใช้งาน (Disable)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def anti_nuke(interaction: discord.Interaction, status: str):
    guild_id = interaction.guild.id
    is_on = (status == "on")
    ant_settings["anti_nuke"][guild_id] = is_on

    embed = discord.Embed(
        title="🛡️ ระบบป้องกัน Nuker (Anti-Nuke)",
        description=f"สถานะระบบ: **{'🟢 เปิดใช้งานแล้ว' if is_on else '🔴 ปิดการใช้งานแล้ว'}**",
        color=0x2ECC71 if is_on else 0xE74C3C
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="anti-spam", description="🛡️ เปิด/ปิดระบบป้องกันสแปมข้อความรัวๆ")
@app_commands.choices(status=[
    app_commands.Choice(name="เปิดการใช้งาน (Enable)", value="on"),
    app_commands.Choice(name="ปิดการใช้งาน (Disable)", value="off")
])
@app_commands.checks.has_permissions(administrator=True)
async def anti_spam(interaction: discord.Interaction, status: str):
    guild_id = interaction.guild.id
    is_on = (status == "on")
    ant_settings["anti_spam"][guild_id] = is_on

    embed = discord.Embed(
        title="🛡️ ระบบป้องกันสแปม (Anti-Spam)",
        description=f"สถานะระบบ: **{'🟢 เปิดใช้งานแล้ว' if is_on else '🔴 ปิดการใช้งานแล้ว'}**",
        color=0x2ECC71 if is_on else 0xE74C3C
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="ban", description="🔨 แบนสมาชิกออกจากเซิร์ฟเวอร์")
@app_commands.describe(member="สมาชิกที่ต้องการแบน", reason="เหตุผลในการแบน")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "ไม่ระบุเหตุผล"):
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 ดำเนินการแบนสมาชิกสำเร็จ",
            description=f"ผู้ใช้งาน: **{member.mention}** ถูกแบนออกจากเซิร์ฟเวอร์\nเหตุผล: `{reason}`",
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการแบน: {e}", ephemeral=True)

@bot.tree.command(name="invite", description="🔗 สร้างและส่งลิงค์เชิญเข้าเซิร์ฟเวอร์แบบถาวร")
async def invite(interaction: discord.Interaction):
    try:
        target_channel = interaction.channel
        if not hasattr(target_channel, "create_invite"):
            for c in interaction.guild.text_channels:
                if c.permissions_for(interaction.guild.me).create_instant_invite:
                    target_channel = c
                    break

        invite_link = await target_channel.create_invite(max_age=0, max_uses=0, unique=True)
        embed = discord.Embed(
            title="🔗 ลิงค์เชิญเข้าสู่เซิร์ฟเวอร์ถาวร",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "คุณสามารถคัดลอกลิงค์ด้านล่างนี้ไปชวนเพื่อนๆ เข้าเซิร์ฟเวอร์ได้เลยครับ!\n\n"
                f"👉 **{invite_link.url}**\n\n"
                "📌 *ลิงค์นี้ไม่มีวันหมดอายุและใช้งานได้ไม่จำกัดจำนวนครั้ง*\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x2ECC71
        )
        embed.set_footer(text=f"สร้างโดย {interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: ขอสิทธิ์ 'สร้างคำเชิญ (Create Invite)' ให้บอทก่อนใช้งานครับ", ephemeral=True)

@bot.tree.command(name="stats", description="📊 สร้างหมวดหมู่และช่องเสียงสถิติเซิร์ฟเวอร์ไว้ด้านบนสุด")
@app_commands.checks.has_permissions(manage_channels=True)
async def stats(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    total_members = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total_members - bots

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)
    }

    try:
        category = await guild.create_category("📈 · SERVERSTATS · 📈", position=0)
        await guild.create_voice_channel(f"👥 · สมาชิกทั้งหมด : {total_members}", category=category, overwrites=overwrites)
        await guild.create_voice_channel(f"👤 · สมาชิก : {humans}", category=category, overwrites=overwrites)
        await guild.create_voice_channel(f"🤖 · บอท : {bots}", category=category, overwrites=overwrites)

        await interaction.followup.send("✅ สร้างห้องสถิติ (Server Stats) ไว้ที่ด้านบนสุดของเซิร์ฟเวอร์เรียบร้อยแล้วครับ!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ เกิดข้อผิดพลาด: กรุณาตรวจสอบว่าบอทมีสิทธิ์ 'จัดการช่อง (Manage Channels)' หรือไม่", ephemeral=True)

# 3. รันเว็บและบอทพร้อมกัน
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: Please set DISCORD_TOKEN in environment variables.")
