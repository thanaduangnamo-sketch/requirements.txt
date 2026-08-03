import nextcord
from nextcord import app_commands
from nextcord.ext import commands, tasks
from captcha.image import ImageCaptcha
import random
import io
import asyncio
import aiohttp
import os
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 ระบบเปิดเว็บจำลอง (Keep-Alive) สำหรับรัน 24 ชม.
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Aegis Bot System is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# ⚙️ ตั้งค่าพื้นฐานของบอทและ Intents
# ==========================================
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ดึง Token จาก Render Environment Variables (ตั้ง Key ว่า DISCORD_TOKEN ใน Render)
TOKEN = os.environ.get("DISCORD_TOKEN", "ใส่ในนี้เลยครับบ")

# ตัวแปรเก็บค่า Config ของแต่ละเซิร์ฟเวอร์
verify_config = {}
user_saved_roles = {}


# ==========================================
# 🛡️ 1. ระบบยืนยันตัวตน (Captcha + Countdown + DM + Log)
# ==========================================
class VerifyButton(View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @nextcord.ui.button(label="ยืนยันตัวตน", emoji="<:kb_members:1222593151449960549>", style=nextcord.ButtonStyle.secondary, custom_id="verify_start_aegis", row=1)
    async def verify(self, button: Button, interaction: nextcord.Interaction):
        config = verify_config.get(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ระบบยืนยันตัวตนยังไม่ได้ตั้งค่าในเซิร์ฟเวอร์นี้ กรุณาให้แอดมินใช้คำสั่ง `/aegis_verify` ก่อนครับ", ephemeral=True)
        
        role_id = config.get("role_id")
        already_role = interaction.guild.get_role(role_id)
        if already_role and already_role in interaction.user.roles:
            return await interaction.response.send_message("ℹ️ คุณได้ทำการยืนยันตัวตนไปแล้วเรียบร้อยครับ", ephemeral=True)

        await generate_captcha(interaction, self.guild_id)
        
    @nextcord.ui.button(label="👨‍💻 Terms of dev", style=nextcord.ButtonStyle.secondary, custom_id="verify_dev_aegis", row=3)
    async def show_dev_info(self, button: Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="👨‍💻 คนทำระบบ",
            description=">>> **📌 ผู้พัฒนา:**\n"
                        "- 👤 **[icewen_2]**\n"
                        "- 🛠 **เครื่องมือ:** `nextcord`, `captcha.image`\n"
                        "- 📅 **วันพัฒนา:** [14/02/2025]\n"
                        "- 🌐 **ติดต่อ:** [ใส่ ig : icesus_22]"
        )
        embed.set_footer(text="ขอบคุณที่ใช้ระบบ Aegis & icewen_2 ❤️")
        await interaction.response.send_message(embed=embed, ephemeral=True)  

    @nextcord.ui.button(label="วิธียืนยันตัวตน", emoji="<:kb_information:1217043424054874213>", style=nextcord.ButtonStyle.secondary, custom_id="verify_help_aegis", row=1)
    async def how_to_verify(self, button: Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="# ❓ วิธีการยืนยันตัวตน",
            description=(
                ">>> 1️⃣ กดปุ่ม **✅ ยืนยันตัวตน**\n"
                "2️⃣ บอทจะส่งรูป **Captcha ตัวเลข 4 หลัก**\n"
                "3️⃣ กดปุ่มตัวเลขให้ **ตรงกับตัวเลขในภาพ** ตามลำดับ\n"
                "4️⃣ ระบบจะทำการนับถอยหลังและตรวจสอบความถูกต้อง\n"
                "5️⃣ หากถูกต้อง บอทจะเพิ่มยศให้และส่งข้อความแจ้งเตือนทาง DM ทันที! ✅\n"
                "❌ ถ้ากรอกผิด ต้องเริ่มใหม่อีกครั้งกั้บผมม"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)  


async def generate_captcha(interaction: nextcord.Interaction, guild_id: int):
    captcha_text = "".join(str(random.randint(0, 9)) for _ in range(4))

    image = ImageCaptcha(width=180, height=80)
    image_data = image.generate(captcha_text)
    image_bytes = io.BytesIO(image_data.read())

    embed = nextcord.Embed(title="**🔒 ยืนยันตัวตน**", description="> กดตัวเลขให้ตรงกับ Captcha ด้านล่างกั้บบผม")
    file = nextcord.File(fp=image_bytes, filename="captcha.png")
    embed.set_image(url="attachment://captcha.png")

    view = CaptchaButtons(captcha_text, guild_id)
    await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)

class CaptchaButtons(View):
    def __init__(self, captcha_text, guild_id):
        super().__init__(timeout=None)
        self.captcha_text = captcha_text
        self.guild_id = guild_id
        self.user_input = ""

        for digit in captcha_text:
            self.add_item(NumberButton(digit, self))

class NumberButton(Button):
    def __init__(self, digit, parent_view):
        super().__init__(label=digit, style=nextcord.ButtonStyle.primary)
        self.digit = digit
        self.parent_view = parent_view

    async def callback(self, interaction: nextcord.Interaction):
        self.parent_view.user_input += self.digit

        embed = interaction.message.embeds[0]
        embed.description = f">>> **โค้ดที่คุณป้อน:** ```{self.parent_view.user_input}```\n\nกรุณากดตัวเลขให้ครบ 4 ตัว"

        # เมื่อกดครบ 4 ตัว
        if len(self.parent_view.user_input) >= 4:
            if self.parent_view.user_input == self.parent_view.captcha_text:
                # ⏳ ระบบนับถอยหลัง 5 4 3 2 1
                embed.description = ">>> ⏳ **กำลังตรวจสอบคำตอบ...**\n**5...**"
                await interaction.response.edit_message(embed=embed, view=None)

                for i in [4, 3, 2, 1]:
                    await asyncio.sleep(1)
                    embed.description = f">>> ⏳ **กำลังตรวจสอบคำตอบ...**\n**{i}...**"
                    await interaction.edit_original_message(embed=embed)
                
                await asyncio.sleep(1)

                # ทำการให้ยศและส่ง DM
                config = verify_config.get(self.parent_view.guild_id)
                if config:
                    role_id = config.get("role_id")
                    log_channel_id = config.get("log_channel_id")
                    role = interaction.guild.get_role(role_id)

                    if role:
                        try:
                            await interaction.user.add_roles(role)
                            
                            # ส่งข้อความหาผู้ใช้ทาง DM ส่วนตัว
                            try:
                                dm_embed = nextcord.Embed(
                                    title="🎉 ยืนยันตัวตนสำเร็จ!",
                                    description=f"ยินดีด้วยครับ คุณได้ผ่านการยืนยันตัวตนในเซิร์ฟเวอร์ **{interaction.guild.name}** และได้รับยศ **{role.name}** เรียบร้อยแล้ว!",
                                    color=nextcord.Color.green()
                                )
                                await interaction.user.send(embed=dm_embed)
                            except:
                                pass # กรณีผู้ใช้ปิดรับ DM

                            # อัปเดต Embed หน้าแชท
                            embed.description = ">>> ✅ **ยืนยันตัวตนสำเร็จ! (ตรวจสอบผลลัพธ์ทาง DM แล้ว)**"
                            embed.color = nextcord.Color.green()
                            await interaction.edit_original_message(embed=embed)

                            # ส่ง Log (ถ้ามีการตั้งค่าห้องไว้)
                            if log_channel_id:
                                log_channel = bot.get_channel(log_channel_id)
                                if log_channel:
                                    log_embed = nextcord.Embed(
                                        title="[ ✨ ] 🛡️ มีผู้ยืนยันตัวตนสำเร็จ",
                                        description=f">>> **👤 ผู้ใช้:** {interaction.user.mention} (`{interaction.user.id}`)\n**🎭 บทบาทที่ได้รับ:** {role.mention}",
                                        color=nextcord.Color.green()
                                    )
                                    await log_channel.send(embed=log_embed)
                        except Exception as e:
                            embed.description = f">>> ❌ เกิดข้อผิดพลาดในการให้ยศ: {e}"
                            embed.color = nextcord.Color.red()
                            await interaction.edit_original_message(embed=embed)
            else:
                # ❌ ถ้ากรอกผิด
                embed.description = "> ❌ **ตัวเลขไม่ถูกต้อง โปรดลองใหม่**"
                embed.color = nextcord.Color.red()
                self.parent_view.clear_items()
                await interaction.response.edit_message(embed=embed, view=self.parent_view)
                return

        if self.parent_view.user_input != self.parent_view.captcha_text:
            await interaction.response.edit_message(embed=embed, view=self.parent_view)


@bot.tree.command(name="aegis_verify", description="[ ✨ ] ส่งหน้าต่างระบบยืนยันตัวตน Captcha พร้อมเลือกยศและห้อง Log (ไม่บังคับ)")
@app_commands.describe(
    เลือกยศ="เลือกยศที่จะให้หลังจากยืนยันตัวตนสำเร็จ",
    ห้องแจ้งเตือน="เลือกห้องที่จะให้บอทส่ง Log แจ้งเตือน (ไม่บังคับ)",
    ลิงก์รูปภาพ="ลิงก์รูปภาพแบนเนอร์ GIF (ไม่บังคับ)"
)
@app_commands.default_permissions(administrator=True)
async def aegis_verify(interaction: nextcord.Interaction, เลือกยศ: nextcord.Role, ห้องแจ้งเตือน: nextcord.TextChannel = None, ลิงก์รูปภาพ: str = "https://i.pinimg.com/originals/29/49/e0/2949e0262e42def248f1c77c571bf9ab.gif"):
    verify_config[interaction.guild.id] = {
        "role_id": เลือกยศ.id,
        "log_channel_id": ห้องแจ้งเตือน.id if ห้องแจ้งเตือน else None
    }

    embed = nextcord.Embed(
        title="**🎄 | Verifications**", 
        description=(
            "✨ ・ ✨ 🇹‌🇭‌🇦‌🇮‌🇱‌🇦‌🇳‌🇩‌ ✨ ・ ✨\n"
            f"• กดปุ่มยืนยันตัวตนด้านล่างเพื่อเริ่มทำ Captcha\n"
            f"• ยืนยันสำเร็จจะได้รับยศ **{เลือกยศ.mention}** และแจ้งเตือนทาง DM\n"
            "• ใครไม่รู้ทำไง กดปุ่มวิธียืนยันตัวตน"
        ), 
        color=nextcord.Color.blue()
    )
    embed.set_image(url=ลิงก์รูปภาพ)
    
    await interaction.channel.send(embed=embed, view=VerifyButton(interaction.guild.id))
    log_text = f", ห้อง Log: {ห้องแจ้งเตือน.mention}" if ห้องแจ้งเตือน else ", ห้อง Log: (ไม่ได้ตั้งค่า)"
    await interaction.response.send_message(f"✅ ส่งแผงระบบยืนยันตัวตนเรียบร้อย! (ยศ: {เลือกยศ.mention}{log_text})", ephemeral=True)


# ==========================================
# 🎫 2. ระบบ Ticket (ติดต่อแอดมิน)
# ==========================================
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="ปิด Ticket", style=nextcord.ButtonStyle.danger, emoji="🔒", custom_id="aegis_persistent_close_ticket:button")
    async def close_ticket(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("🔒 กำลังปิดห้องนี้ใน 3 วินาที...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="สร้าง Ticket", style=nextcord.ButtonStyle.secondary, emoji="🎟️", custom_id="aegis_persistent_ticket:button")
    async def create_ticket(self, button: Button, interaction: nextcord.Interaction):
        guild, user = interaction.guild, interaction.user
        for channel in guild.text_channels:
            if channel.topic and f"ID: {user.id}" in channel.topic:
                return await interaction.response.send_message(f"❌ คุณมีห้องติดต่อเปิดอยู่แล้วครับ: {channel.mention}", ephemeral=True)

        category = nextcord.utils.get(guild.categories, name="🎫 AEGIS TICKETS") or await guild.create_category("🎫 AEGIS TICKETS")
        existing_tickets = [int(c.name.split("-")[1]) for c in guild.text_channels if c.name.startswith("ticket-") and c.name.split("-")[1].isdigit()]
        next_number = max(existing_tickets) + 1 if existing_tickets else 1

        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
            user: nextcord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: nextcord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"ticket-{next_number}", category=category, overwrites=overwrites, topic=f"ID: {user.id}")
        
        embed = nextcord.Embed(title=f"📩 เปิด Ticket #{next_number} สำเร็จ", description=f"{user.mention} แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อแอดมินไว้ได้เลยครับ!", color=0x2b2d31)
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ สร้างห้องติดต่อแอดมินให้แล้ว: {ticket_channel.mention}", ephemeral=True)

@bot.tree.command(name="aegis_ticket", description="[ ✨ ] สร้างระบบ Ticket สำหรับติดต่อแอดมินดีไซน์หรูหรา")
@app_commands.describe(รูปภาพ="อัปโหลดรูปภาพแบนเนอร์", ลิงก์รูปภาพ="ลิงก์ URL รูปภาพ")
async def aegis_ticket(interaction: nextcord.Interaction, รูปภาพ: nextcord.Attachment = None, ลิงก์รูปภาพ: str = None):
    embed = nextcord.Embed(
        title="🎟️  ระบบ Ticket",
        description="━━━━━━━━━━━━━━━━━━━━━━\n> \"ทุกปัญหา มีทางออก\"\n> \"ทีมงานพร้อมช่วยเหลือคุณ\"\n━━━━━━━━━━━━━━━━━━━━━━\n\n**กดปุ่มด้านล่างเพื่อสร้าง Ticket**",
        color=0x2b2d31
    )
    if รูปภาพ: embed.set_image(url=รูปภาพ.url)
    elif ลิงก์รูปภาพ: embed.set_image(url=ลิงก์รูปภาพ)
    
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Ticket เรียบร้อย", ephemeral=True)


# ==========================================
# 🛡️ 3. ระบบเซฟและคืนยศ (Save & Restore Roles)
# ==========================================
class SaveRestoreRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="เซฟยศของฉัน", style=nextcord.ButtonStyle.primary, emoji="🛡️", custom_id="aegis_save_role:button")
    async def save_roles(self, button: Button, interaction: nextcord.Interaction):
        user, guild = interaction.user, interaction.guild
        roles_to_save = [role.id for role in user.roles if role != guild.default_role and guild.me.top_role > role]
        user_saved_roles[user.id] = roles_to_save
        
        embed = nextcord.Embed(title="🛡️ สำเร็จ — บันทึกยศเรียบร้อย", description=f"✅ ทำการเซฟยศทั้งหมดของคุณจำนวน **{len(roles_to_save)} ยศ** เรียบร้อยแล้ว!", color=0xf1c40f)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="คืนยศของฉัน", style=nextcord.ButtonStyle.danger, emoji="🛠️", custom_id="aegis_restore_role:button")
    async def restore_roles(self, button: Button, interaction: nextcord.Interaction):
        user, guild = interaction.user, interaction.guild
        if user.id not in user_saved_roles or not user_saved_roles[user.id]:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลการเซฟยศของคุณ กรุณากด 'เซฟยศของฉัน' ก่อนครับ", ephemeral=True)

        saved_role_ids = user_saved_roles[user.id]
        roles_to_add = [guild.get_role(r_id) for r_id in saved_role_ids if guild.get_role(r_id) and guild.me.top_role > guild.get_role(r_id)]

        try:
            await user.add_roles(*roles_to_add)
            embed = nextcord.Embed(title="🛠️ สำเร็จ — คืนยศเรียบร้อย", description=f"✅ คืนยศให้คุณสำเร็จจำนวน **{len(roles_to_add)} ยศ** แล้วครับ!", color=0xf1c40f)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {e}", ephemeral=True)

@bot.tree.command(name="aegis_saveroles", description="[ ✨ ] สร้างระบบปุ่มกดเซฟและคืนยศอัตโนมัติสำหรับสมาชิก")
async def aegis_saveroles(interaction: nextcord.Interaction, ลิงก์รูปภาพ: str = "https://i.pinimg.com/736x/14/68/59/146859926bd33323535af3b8697b024d.jpg"):
    embed = nextcord.Embed(title="🛡️ ระบบเซฟและคืนยศ", description="กดปุ่มด้านล่างเพื่อจัดการยศของคุณได้เลย!", color=0xf1c40f)
    embed.set_image(url=ลิงก์รูปภาพ)
    await interaction.channel.send(embed=embed, view=SaveRestoreRoleView())
    await interaction.response.send_message("✅ สร้างหน้าต่างระบบเซฟและคืนยศเรียบร้อย", ephemeral=True)


# ==========================================
# 🌐 4. ระบบแปลภาษา
# ==========================================
class TranslateModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="🌐 ระบบแปลภาษาอัตโนมัติ")
        self.text_input = nextcord.ui.TextInput(label="ข้อความที่ต้องการแปล", style=nextcord.TextInputStyle.paragraph, required=True)
        self.add_item(self.text_input)

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        original_text = self.text_input.value.strip()
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={original_text}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                res_json = await resp.json()
                translated_text = "".join([item[0] for item in res_json[0]])
                detected_lang = res_json[2].upper()
        embed = nextcord.Embed(title="🌐 ผลการแปลภาษา", color=0x2ecc71)
        embed.add_field(name="📝 ต้นฉบับ", value=f"```{original_text}```", inline=False)
        embed.add_field(name=f"✨ ภาษาไทย (จาก: {detected_lang})", value=f"```{translated_text}```", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

class TranslateView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @nextcord.ui.button(label="แปลภาษา", style=nextcord.ButtonStyle.success, emoji="🌐", custom_id="aegis_translate:button")
    async def open_translate(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(TranslateModal())

@bot.tree.command(name="aegis_translate", description="[ ✨ ] เปิดหน้าต่างระบบแปลภาษาข้อความสากลเป็นไทย")
async def aegis_translate(interaction: nextcord.Interaction):
    embed = nextcord.Embed(title="🌐 TRANSLATE SYSTEM", description="กดปุ่มด้านล่างเพื่อแปลภาษาเป็นไทย", color=0x2ecc71)
    await interaction.channel.send(embed=embed, view=TranslateView())
    await interaction.response.send_message("✅ ส่งหน้าต่างแปลภาษาเรียบร้อย", ephemeral=True)


# ==========================================
# 🔍 5. ระบบ TOKEN CHECKER
# ==========================================
class TokenModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="TOKEN CHECKER")
        self.token_input = nextcord.ui.TextInput(label="กรอก Discord Token", style=nextcord.TextInputStyle.paragraph, required=True)
        self.add_item(self.token_input)

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = {"Authorization": self.token_input.value.strip(), "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Token ไม่ถูกต้องหรือหมดอายุ", ephemeral=True)
                data = await resp.json()
        
        embed = nextcord.Embed(title="✨ TOKEN CHECKER RESULT ✨", description="ส่งผลลัพธ์ให้คุณทาง DM", color=0xe74c3c)
        embed.add_field(name="🏷️ ผู้ใช้", value=f"`{data.get('username')}`", inline=True)
        embed.add_field(name="📧 อีเมล", value=f"`{data.get('email', 'ซ่อนอยู่')}`", inline=True)
        try:
            await interaction.user.send(embed=embed)
            await interaction.followup.send("✅ ส่งผลลัพธ์ไปที่ DM ของคุณแล้ว!", ephemeral=True)
        except:
            await interaction.followup.send("❌ ไม่สามารถส่ง DM ได้ กรุณาเปิดรับข้อความส่วนตัว", ephemeral=True)

class TokenCheckerView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @nextcord.ui.button(label="TOKEN CHECKER", style=nextcord.ButtonStyle.danger, emoji="🔍", custom_id="aegis_token_checker:button")
    async def open_checker(self, button: Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(TokenModal())

@bot.tree.command(name="aegis_tokencheck", description="[ ✨ ] ตรวจสอบความถูกต้องของ Discord Token และส่งข้อมูลเข้า DM")
async def aegis_tokencheck(interaction: nextcord.Interaction):
    embed = nextcord.Embed(title="AEGIS — TOKEN CHECKER", description="ตรวจสอบ Token ปลอดภัย 100%", color=0xe74c3c)
    await interaction.channel.send(embed=embed, view=TokenCheckerView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Token Checker เรียบร้อย", ephemeral=True)


# ==========================================
# 🤖 6. Event & Status Loop (เปิดระบบทำงาน)
# ==========================================
@tasks.loop(minutes=1)
async def change_status():
    server_count = len(bot.guilds)
    statuses = [
        nextcord.Game(name=f"ให้บริการ {server_count} เซิร์ฟเวอร์"),
        nextcord.Game(name="ระบบยืนยันตัวตน Captcha & Ticket พร้อมใช้งาน"),
        nextcord.Game(name="ระบบความปลอดภัย Aegis")
    ]
    if not hasattr(change_status, "index"): change_status.index = 0
    await bot.change_presence(status=nextcord.Status.online, activity=statuses[change_status.index])
    change_status.index = (change_status.index + 1) % len(statuses)

@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    bot.add_view(TranslateView())
    bot.add_view(TokenCheckerView())
    bot.add_view(SaveRestoreRoleView())
    
    await bot.tree.sync()
    if not change_status.is_running(): change_status.start()

@bot.event
async def on_member_remove(member: nextcord.Member):
    roles = [role.id for role in member.roles if role != member.guild.default_role and member.guild.me.top_role > role]
    if roles: user_saved_roles[member.id] = roles


# ==========================================
# 🚀 รันบอท
# ==========================================
if __name__ == "__main__":
    if not TOKEN or TOKEN == "ใส่ในนี้เลยครับบ":
        print("❌ ERROR: กรุณาใส่ BOT_TOKEN ของคุณใน Environment Variables (DISCORD_TOKEN) ของ Render ก่อนรันบอท")
    else:
        keep_alive()
        bot.run(TOKEN)
