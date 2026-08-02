import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import aiohttp
from flask import Flask
from threading import Thread
import asyncio

# --- ระบบเปิดเว็บจำลองสำหรับ Render (ดึง Port อัตโนมัติ) ---
app = Flask('')

@app.route('/')
def home():
    return "Aegis Bot & Shop is running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------

# --- ดึง Token จาก Environment Variable อย่างปลอดภัย ---
token = os.environ.get("DISCORD_TOKEN")

if not token:
    print("❌ ERROR: ไม่พบ DISCORD_TOKEN กรุณาตั้งค่า Token ใน Environment Variables")
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ฐานข้อมูลจำลองสำหรับเก็บยศของผู้ใช้ (User ID -> List of Role IDs)
user_saved_roles = {}


# ==========================================
# 🛡️ ระบบเซฟและคืนยศ (Save & Restore Roles)
# ==========================================
class SaveRestoreRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศของฉัน", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="aegis_save_role:button")
    async def save_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        
        # กรองเอาเฉพาะยศที่บอทสามารถจัดการได้ และไม่ใช่ @everyone
        roles_to_save = [role.id for role in user.roles if role != guild.default_role and guild.me.top_role > role]
        
        user_saved_roles[user.id] = roles_to_save
        
        embed = discord.Embed(
            title="🛡️ สำเร็จ — บันทึกยศเรียบร้อย",
            description=f"✅ ทำการเซฟยศทั้งหมดของคุณจำนวน **{len(roles_to_save)} ยศ** เรียบร้อยแล้วครับ!",
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="คืนยศของฉัน", style=discord.ButtonStyle.danger, emoji="🛠️", custom_id="aegis_restore_role:button")
    async def restore_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild

        if user.id not in user_saved_roles or not user_saved_roles[user.id]:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลการเซฟยศของคุณในระบบ กรุณากด 'เซฟยศของฉัน' ก่อนครับ", ephemeral=True)

        saved_role_ids = user_saved_roles[user.id]
        roles_to_add = []
        failed_count = 0

        for r_id in saved_role_ids:
            role = guild.get_role(r_id)
            if role and guild.me.top_role > role:
                roles_to_add.append(role)
            else:
                failed_count += 1

        try:
            await user.add_roles(*roles_to_add)
            embed = discord.Embed(
                title="🛠️ สำเร็จ — คืนยศเรียบร้อย",
                description=f"✅ ทำการคืนยศให้คุณสำเร็จจำนวน **{len(roles_to_add)} ยศ** เรียบร้อยแล้วครับ!",
                color=0xf1c40f
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการคืนยศ: {e}", ephemeral=True)

    @discord.ui.button(label="โปรไฟล์ของฉัน", style=discord.ButtonStyle.secondary, emoji="👤", custom_id="aegis_profile_role:button")
    async def profile_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        
        saved_ids = user_saved_roles.get(user.id, [])
        saved_role_names = [guild.get_role(r_id).name for r_id in saved_ids if guild.get_role(r_id)]
        current_roles = [r.name for r in user.roles if r != guild.default_role]

        embed = discord.Embed(
            title=f"👤 โปรไฟล์ข้อมูลยศของ: {user.name}",
            description=(
                f"🛡️ **ยศที่เซฟไว้ในระบบ:** `{len(saved_ids)} ยศ`\n"
                f"📋 รายชื่อยศที่เซฟ: {', '.join(saved_role_names) if saved_role_names else 'ยังไม่มีการเซฟ'}\n\n"
                f"🏷️ **ยศปัจจุบันที่มี:** `{len(current_roles)} ยศ`\n"
                f"📋 รายชื่อยศปัจจุบัน: {', '.join(current_roles) if current_roles else 'ไม่มี'}"
            ),
            color=0xf1c40f
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="setup_saveroles", description="สร้างระบบปุ่มกดเซฟและคืนยศอัตโนมัติ")
@app_commands.describe(image_url="ใส่ลิงก์รูปภาพแบนเนอร์ (ไม่บังคับ)")
async def setup_saveroles_command(interaction: discord.Interaction, image_url: str = "https://i.pinimg.com/736x/14/68/59/146859926bd33323535af3b8697b024d.jpg"):
    embed = discord.Embed(
        title="🛡️ ระบบเซฟและคืนยศ",
        description=(
            "กดปุ่มด้านล่างเพื่อจัดการยศของคุณได้เลย!\n\n"
            "> 🛡️ **เซฟยศ** — บันทึกยศทั้งหมดที่คุณมีอยู่ตอนนี้\n"
            "> 🛠️ **คืนยศ** — กู้คืนยศที่คุณเคยเซฟไว้\n"
            "> 👤 **โปรไฟล์** — ตรวจสอบข้อมูลและยศของคุณ\n\n"
            "⚠️ **หมายเหตุ:** ระบบจะเซฟยศให้คุณอัตโนมัติเมื่อคุณออกจากเซิร์ฟเวอร์ด้วย"
        ),
        color=0xf1c40f
    )
    
    embed.set_image(url=image_url)
    embed.set_footer(text="Aegis Bot / Shop — Role Saver System")

    view = SaveRestoreRoleView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างหน้าต่างระบบเซฟและคืนยศ (พร้อมรูปภาพที่คุณกำหนด) เรียบร้อยแล้วครับ", ephemeral=True)


# ระบบเซฟยศอัตโนมัติเมื่อสมาชิกออกจากเซิร์ฟเวอร์
@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    roles_to_save = [role.id for role in member.roles if role != guild.default_role and guild.me.top_role > role]
    if roles_to_save:
        user_saved_roles[member.id] = roles_to_save
        print(f"📌 เซฟยศอัตโนมัติให้กับ {member.name} (ID: {member.id}) จำนวน {len(roles_to_save)} ยศเรียบร้อย")


# ==========================================
# 🧧 ระบบซื้อยศ VIP ด้วยซองอั่งเปา (Angpao VIP Shop)
# ==========================================
class AngpaoModal(discord.ui.Modal, title="🧧 แจ้งสลิปซองอั่งเปา TrueMoney"):
    link_input = discord.ui.TextInput(
        label="ลิงก์ซองอั่งเปา TrueMoney (Gift Link)",
        style=discord.TextStyle.short,
        placeholder="https://gift.truemoney.com/campaign/?v=...",
        required=True,
        max_length=150
    )

    def __init__(self, role_ids: list):
        super().__init__()
        self.role_ids = role_ids

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        link = self.link_input.value.strip()
        user = interaction.user
        guild = interaction.guild

        # ส่งข้อมูลซองและผู้ซื้อไปให้แอดมินตรวจสอบ
        embed = discord.Embed(
            title="🧧 มีคำสั่งซื้อยศ VIP (ซองอั่งเปา) ใหม่!",
            description=(
                f"👤 **ผู้ซื้อ:** {user.mention} (`{user.name}`)\n"
                f"🆔 **User ID:** `{user.id}`\n"
                f"🔗 **ลิงก์ซองอั่งเปา:** `{link}`\n\n"
                f"🏷️ **ยศที่เลือกซื้อ:**\n" + 
                "\n".join([f"• <@&{r_id}>" for r_id in self.role_ids if guild.get_role(r_id)])
            ),
            color=0x2ecc71
        )
        embed.set_footer(text="Aegis Bot / Shop — Angpao System")

        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ ส่งข้อมูลลิงก์ซองอั่งเปาให้ระบบ/แอดมินตรวจสอบเรียบร้อยแล้ว กรุณารอแอดมินตรวจสอบและกดยืนยันครับ!", ephemeral=True)


class BuyVipAngpaoView(discord.ui.View):
    def __init__(self, role_ids: list):
        super().__init__(timeout=None)
        self.role_ids = role_ids

    @discord.ui.button(label="🧧 เติมเงินซองอั่งเปาเพื่อรับยศ", style=discord.ButtonStyle.success, emoji="💸", custom_id="aegis_buy_vip_angpao:button")
    async def open_angpao_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AngpaoModal(self.role_ids)
        await interaction.response.send_modal(modal)


@bot.tree.command(name="buy_vip_angpao", description="ซื้อยศ VIP ด้วยซองอั่งเปา TrueMoney (เลือกยศได้สูงสุด 4 ยศ)")
@app_commands.describe(
    yศที่_1="เลือกยศหลักที่ต้องการรับ",
    yศที่_2="เลือกยศเสริมที่ 2 (ไม่บังคับ)",
    yศที่_3="เลือกยศเสริมที่ 3 (ไม่บังคับ)",
    yศที่_4="เลือกยศเสริมที่ 4 (ไม่บังคับ)"
)
async def buy_vip_angpao_command(
    interaction: discord.Interaction, 
    yศที่_1: discord.Role, 
    yศที่_2: discord.Role = None, 
    yศที่_3: discord.Role = None, 
    yศที่_4: discord.Role = None
):
    selected_roles = [yศที่_1]
    if yศที่_2: selected_roles.append(yศที่_2)
    if yศที่_3: selected_roles.append(yศที่_3)
    if yศที่_4: selected_roles.append(yศที่_4)

    role_ids = [role.id for role in selected_roles]
    role_names_str = ", ".join([f"**{role.name}**" for role in selected_roles])

    embed = discord.Embed(
        title="🧧 AEGIS SHOP — ซื้อยศ VIP ด้วยซองอั่งเปา",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 **ยศที่คุณเลือกซื้อ:**\n{role_names_str}\n\n"
            "📥 **วิธีชำระเงิน:**\n"
            "1. สร้างซองของขวัญ TrueMoney (แบบจำนวนเงินเท่ากัน หรือสุ่มตามราคาแพ็กเกจ)\n"
            "2. กดปุ่ม **'เติมเงินซองอั่งเปาเพื่อรับยศ'** สีเขียวด้านล่าง\n"
            "3. วางลิงก์ซองอั่งเปาในช่องกรอกข้อมูลแล้วกดส่ง\n"
            "4. รอระบบตรวจสอบและรับยศอัตโนมัติ/จากแอดมิน\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x7f8c8d  # โทนสีเทา
    )
    # อัปเดตลิงก์รูปภาพใหม่ตามที่คุณต้องการ
    embed.set_image(url="https://i.pinimg.com/236x/69/38/a8/6938a8608a33e27135a2d612d785641e.jpg")
    embed.set_footer(text="AEGIS BOT / SHOP — ANGPAO VIP SYSTEM")

    view = BuyVipAngpaoView(role_ids)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างหน้าต่างซื้อยศ VIP ด้วยซองอั่งเปาเรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 🟩 ระบบรับยศทั่วไป (เลือกยศผ่านคำสั่ง /setup_roles)
# ==========================================
class GeneralRoleView(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="【 ☁️ กดเพื่อรับ/คืนยศ 】", style=discord.ButtonStyle.success, emoji="🟢", custom_id="general_role_button:dynamic")
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)
        
        if not role:
            return await interaction.response.send_message("❌ ไม่พบยศนี้ในระบบเซิร์ฟเวอร์ กรุณาติดต่อแอดมิน", ephemeral=True)

        user = interaction.user

        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"🗑️ ทำการคืนยศ **{role.name}** เรียบร้อยแล้วครับ", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ คุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ!", ephemeral=True)


@bot.tree.command(name="setup_roles", description="สร้างระบบรับยศปุ่มกด โดยเลือกยศที่ต้องการได้ทันที")
@app_commands.describe(
    role="เลือกยศที่ต้องการให้ผู้ใช้งานได้รับเมื่อกดปุ่ม",
    image_url="ใส่ลิงก์รูปภาพแบนเนอร์ด้านใน Embed (ไม่บังคับ)"
)
async def setup_roles_command(interaction: discord.Interaction, role: discord.Role, image_url: str = "https://i.pinimg.com/736x/de/f8/80/def8807c89475990941ba4617b4cbc2e.jpg"):
    embed = discord.Embed(
        title="💬 Aegis Bot / Shop — ระบบรับยศทั่วไป",
        description=(
            ".•° 💧 𝓐𝓮𝓰𝓲𝓼 💧 °•.\n\n"
            f"🟢 : กดปุ่มด้านล่างเพื่อรับยศ **{role.name}**\n"
            "🟢 : กดปุ่มซ้ำ เพื่อคืนยศ\n\n"
            ".•° 💧 𝓐𝓮𝓰𝓲𝓼 💧 °•."
        ),
        color=0x2b2d31
    )
    
    if image_url:
        embed.set_image(url=image_url)
        
    embed.set_footer(text="© AEGIS BOT / SHOP")

    view = GeneralRoleView(role.id)
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ สร้างหน้าต่างระบบรับยศ (**{role.name}**) เรียบร้อยแล้วครับ", ephemeral=True)


# --- ระบบลูปเปลี่ยนสถานะทุกๆ 1 นาที ---
@tasks.loop(minutes=1)
async def change_status():
    server_count = len(bot.guilds)
    
    statuses = [
        discord.Game(name=f"Aegis Bot | ให้บริการ {server_count} เซิร์ฟเวอร์"),
        discord.Game(name="Aegis Shop | ระบบรับยศ & Ticket พร้อมใช้งาน"),
        discord.Game(name="Aegis | ระบบเซฟยศและจัดการเซิร์ฟเวอร์")
    ]
    
    if not hasattr(change_status, "index"):
        change_status.index = 0
    
    current_status = statuses[change_status.index]
    await bot.change_presence(status=discord.Status.online, activity=current_status)
    
    change_status.index = (change_status.index + 1) % len(statuses)


@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TranslateView())
    bot.add_view(TokenCheckerView())
    bot.add_view(SaveRestoreRoleView())
    
    server_count = len(bot.guilds)
    print(f"Logged in as {bot.user.name} (Aegis Bot System)")
    print(f"🌐 บอทกำลังให้บริการอยู่ทั้งหมด {server_count} เซิร์ฟเวอร์:")
    for guild in bot.guilds:
        print(f" - ชื่อเซิร์ฟเวอร์: {guild.name} | ID: {guild.id}")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    if not change_status.is_running():
        change_status.start()
        
    print("✅ Aegis Bot ออนไลน์และเริ่มระบบเรียบร้อยแล้วครับ")


# ==========================================
# 🛡️ ระบบแจ้งเตือนเมื่อมีคนดึงบอทเข้าเซิร์ฟเวอร์
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    if member.bot:
        guild = member.guild
        target_channel_id = 1533086872471994489
        target_channel = guild.get_channel(target_channel_id)

        if not target_channel:
            return

        inviter = "ไม่ทราบ (อาจใช้ลิงก์ OAuth2 ลับ หรือดึงตรง)"
        try:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
                if entry.target.id == member.id:
                    inviter = entry.user.mention
                    break
        except Exception as e:
            print(f"ไม่สามารถดึง Audit Log ได้: {e}")

        embed = discord.Embed(
            title="🚨 มีการเพิ่มบอท Aegis เข้าสู่เซิร์ฟเวอร์!",
            description=(
                f"🤖 **ชื่อบอท:** {member.mention} (`{member.name}`)\n"
                f"🆔 **Bot ID:** `{member.id}`\n"
                f"👤 **ผู้ที่ดึงเข้าเซิร์ฟ:** {inviter}\n\n"
                f"📅 **เวลา:** <t:{int(member.joined_at.timestamp())}:F>"
            ),
            color=0xe74c3c
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"เซิร์ฟเวอร์: {guild.name}", icon_url=guild.icon.url if guild.icon else None)

        await target_channel.send(embed=embed)


# ==========================================
# 🌐 ระบบแปลภาษา (Translate System)
# ==========================================
class TranslateModal(discord.ui.Modal, title="🌐 Aegis : ระบบแปลภาษาอัตโนมัติ"):
    text_input = discord.ui.TextInput(
        label="ข้อความที่ต้องการแปล",
        style=discord.TextStyle.paragraph,
        placeholder="พิมพ์ข้อความที่ต้องการแปลภาษาลงที่นี่...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        original_text = self.text_input.value.strip()

        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={original_text}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ เกิดข้อผิดพลาดในการเชื่อมต่อระบบแปลภาษา", ephemeral=True)
                res_json = await resp.json()
                translated_text = "".join([item[0] for item in res_json[0]])
                detected_lang = res_json[2].upper()

        embed = discord.Embed(
            title="🌐 Aegis — ผลการแปลภาษา",
            color=0x2ecc71
        )
        embed.add_field(name="📝 ข้อความต้นฉบับ", value=f"```{original_text}```", inline=False)
        embed.add_field(name=f"✨ แปลเป็นภาษาไทย (จาก: {detected_lang})", value=f"```{translated_text}```", inline=False)
        embed.set_footer(text="Aegis Bot / Shop Translation System")

        await interaction.followup.send(embed=embed, ephemeral=True)


class TranslateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="แปลภาษา",
        style=discord.ButtonStyle.success,
        emoji="🌐",
        custom_id="aegis_translate:button"
    )
    async def open_translate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TranslateModal())


@bot.tree.command(name="translate", description="เปิดหน้าต่างระบบแปลภาษา Aegis")
async def translate_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 AEGIS — TRANSLATE SYSTEM",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° TRANSLATE °•.\n"
            "╭ · ระบบแปลภาษาอัตโนมัติ รวดเร็วและแม่นยำ\n"
            "│ · รองรับการแปลภาษาจากทั่วโลกเป็นภาษาไทย\n"
            "╰ · ใช้งานง่ายผ่านปุ่มกดด้านล่างทันที\n\n"
            "📖 **วิธีใช้งานระบบ:**\n"
            "1. กดปุ่มสีเขียว **'แปลภาษา'** ด้านล่าง\n"
            "2. กรอกข้อความที่ต้องการแปลลงในช่องว่าง\n"
            "3. กดส่ง (Submit) เพื่อดูผลลัพธ์\n"
            "4. ระบบแสดงผลเฉพาะตัวคุณเท่านั้น"
        ),
        color=0x2ecc71
    )
    embed.set_image(url="https://i.pinimg.com/736x/de/f8/80/def8807c89475990941ba4617b4cbc2e.jpg")
    embed.set_footer(text="AEGIS BOT / SHOP — TRANSLATE SYSTEM")

    await interaction.channel.send(embed=embed, view=TranslateView())
    await interaction.response.send_message("✅ ส่งหน้าต่างแปลภาษาเรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 🔍 ระบบ TOKEN CHECKER
# ==========================================
class TokenModal(discord.ui.Modal, title="AEGIS : TOKEN CHECKER"):
    token_input = discord.ui.TextInput(
        label="กรอก Discord Token ที่ต้องการตรวจสอบ",
        style=discord.TextStyle.paragraph,
        placeholder="วาง Token ของคุณลงที่นี่...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        raw_token = self.token_input.value.strip()

        headers = {
            "Authorization": raw_token,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as resp:
                if resp.status != 200:
                    return await interaction.followup.send(
                        "❌ **Token ไม่ถูกต้องหรือหมดอายุแล้ว!** กรุณาตรวจสอบความถูกต้องอีกครั้ง",
                        ephemeral=True
                    )
                user_data = await resp.json()

        username = user_data.get("username", "Unknown")
        discriminator = user_data.get("discriminator", "0")
        full_name = f"{username}#{discriminator}" if discriminator != "0" else username
        user_id = user_data.get("id", "Unknown")
        email = user_data.get("email", "ไม่มีข้อมูล / ซ่อนอยู่")
        phone = user_data.get("phone", "ไม่มีข้อมูล / ซ่อนอยู่")
        mfa_enabled = "เปิดใช้งาน (2FA)" if user_data.get("mfa_enabled") else "ปิดใช้งาน"
        verified = "ยืนยันแล้ว" if user_data.get("verified") else "ยังไม่ยืนยัน"
        
        is_bot = user_data.get("bot", False)
        acc_type = "🤖 Bot Account" if is_bot else "👤 User Account"

        nitro_type = user_data.get("premium_type", 0)
        nitro_map = {0: "ไม่มี Nitro", 1: "Nitro Classic", 2: "Nitro Boost", 3: "Nitro Basic"}
        nitro_status = nitro_map.get(nitro_type, "ไม่ทราบสถานะ")

        avatar_id = user_data.get("avatar")
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"

        result_embed = discord.Embed(
            title="✨ AEGIS — TOKEN CHECKER RESULT ✨",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "• **ข้อมูล Token จะไม่ถูกนำไปบันทึกในฐานข้อมูลใดๆ**\n"
                "• ผลลัพธ์แสดงเฉพาะตัวคุณเท่านั้น (ส่งเข้า DM ส่วนตัว)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0xe74c3c
        )
        result_embed.set_thumbnail(url=avatar_url)
        result_embed.add_field(name="🏷️ ชื่อผู้ใช้", value=f"`{full_name}`", inline=True)
        result_embed.add_field(name="🆔 บัญชี ID", value=f"`{user_id}`", inline=True)
        result_embed.add_field(name="📂 ประเภทบัญชี", value=acc_type, inline=True)
        result_embed.add_field(name="📧 อีเมล", value=f"`{email}`", inline=True)
        result_embed.add_field(name="📱 เบอร์โทรศัพท์", value=f"`{phone}`", inline=True)
        result_embed.add_field(name="🔒 ระบบความปลอดภัย (2FA)", value=mfa_enabled, inline=True)
        result_embed.add_field(name="✅ สถานะยืนยันอีเมล", value=verified, inline=True)
        result_embed.add_field(name="💎 สถานะ Nitro ล่าสุด", value=nitro_status, inline=True)
        result_embed.set_footer(text="AEGIS BOT / SHOP — TOKEN CHECKER", icon_url="https://i.pinimg.com/736x/5c/6f/47/5c6f4777c193e7fff8120e187ace58fd.jpg")

        try:
            await interaction.user.send(embed=result_embed)
            await interaction.followup.send(
                "✅ ตรวจสอบ Token สำเร็จ! ระบบได้จัดส่งผลลัพธ์ไปที่ **ข้อความส่วนตัว (DM)** เรียบร้อยแล้ว",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ ไม่สามารถส่งข้อความหาคุณได้ กรุณาเปิดรับข้อความส่วนตัว (Direct Messages) ก่อนใช้งานครับ",
                ephemeral=True
            )


class TokenCheckerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="TOKEN CHECKER",
        style=discord.ButtonStyle.danger,
        emoji="🔍",
        custom_id="aegis_token_checker:button"
    )
    async def open_checker(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TokenModal())


@bot.tree.command(name="checktoken", description="เปิดหน้าต่างตรวจสอบ Discord Token (ส่งผลลัพธ์เข้า DM)")
async def checktoken_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="AEGIS — TOKEN CHECKER",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━ .•° TOKEN CHECKER °•.\n"
            "╭ · ระบบตรวจสอบความถูกต้องและดูสิทธิ์ของ Token\n"
            "│ · แยกประเภทบัญชีอัตโนมัติ (User Account / Bot)\n"
            "│ · ตรวจสอบอีเมล, เบอร์โทรศัพท์ และสถานะ 2FA\n"
            "╰ · เช็คสถานะแพลทินัม Nitro ล่าสุด\n\n"
            "**นโยบายความปลอดภัย:**\n"
            "• ข้อมูล Token จะไม่ถูกนำไปบันทึกหรือเก็บไว้ใดๆ\n"
            "• ผลลัพธ์แสดงเฉพาะตัวคุณเท่านั้น (ส่งเข้า DM ส่วนตัว)"
        ),
        color=0xe74c3c
    )
    embed.set_image(url="https://i.pinimg.com/736x/5c/6f/47/5c6f4777c193e7fff8120e187ace58fd.jpg")
    embed.set_footer(text="AEGIS BOT / SHOP — TOKEN CHECKER")

    await interaction.channel.send(embed=embed, view=TokenCheckerView())
    await interaction.response.send_message("✅ ส่งหน้าต่าง Token Checker เรียบร้อยแล้วครับ", ephemeral=True)


# ==========================================
# 2. ระบบ Ticket (Persistent View)
# ==========================================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="สอบถาม/แจ้งปัญหา", style=discord.ButtonStyle.success, emoji="📩", custom_id="aegis_persistent_ticket:button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        for channel in guild.text_channels:
            if channel.topic and f"ID: {user.id}" in channel.topic:
                return await interaction.response.send_message(f"❌ คุณมีห้องติดต่อแอดมินเปิดอยู่แล้วครับ: {channel.mention}", ephemeral=True)

        category_name = "🎫 AEGIS TICKETS"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        existing_tickets = [c for c in guild.text_channels if c.name.startswith("ticket-")]
        ticket_numbers = []
        for c in existing_tickets:
            parts = c.name.split("-")
            if len(parts) > 1 and parts[1].isdigit():
                ticket_numbers.append(int(parts[1]))

        next_number = 1 if not ticket_numbers else max(ticket_numbers) + 1

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{next_number}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket #{next_number} ของคุณ {user.name} (ID: {user.id})"
        )

        embed = discord.Embed(
            title=f"📩 Aegis Shop — เปิด Ticket #{next_number} สำเร็จ",
            description=f"สวัสดีครับคุณ {user.mention} แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อแอดมินไว้ได้เลยครับ ทีมงานจะรีบเข้ามาช่วยเหลือโดยเร็วที่สุด!",
            color=0x2b2d31
        )
        
        close_view = CloseTicketView()
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)

        await interaction.response.send_message(f"✅ สร้างห้องติดต่อแอดมินให้แล้วครับ: {ticket_channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ปิด Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="aegis_persistent_close_ticket:button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 กำลังปิดห้องนี้ใน 3 วินาที...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()


@bot.tree.command(name="ติดต่อแอดมิน", description="สร้างระบบติดต่อแอดมิน / แจ้งปัญหา (Ticket)")
@app_commands.describe(image="อัปโหลดรูปภาพประกอบ (ไม่บังคับ)", image_url="หรือใส่ลิงก์รูปภาพ URL (ไม่บังคับ)")
async def ticket_command(interaction: discord.Interaction, image: discord.Attachment = None, image_url: str = None):
    embed = discord.Embed(
        title="Aegis Bot / Shop — ติดต่อแอดมิน/แจ้งปัญหา",
        description=(
            "🎟️ **Aegis Support Ticket**\n"
            "หากคุณต้องการติดต่อร้านค้าหรือแจ้งปัญหา\n"
            "กดปุ่มด้านล่างเพื่อเปิดตั๋วได้ทันที\n\n"
            "```ansi\n"
            "\u001b[30;1m┌─────────────────────────────────────────┐\n"
            "  🟩 โปรดอธิบายรายละเอียดให้ครบถ้วน\n"
            "  ⏳ แอดมินจะรีบเข้ามาตอบโดยเร็วที่สุด\n"
            "  ⚠️ การเปิดตั๋วเล่น ๆ อาจส่งผลต่อสิทธิ์การใช้งาน\n"
            "└─────────────────────────────────────────┘\n"
            "\u001b[0m"
        ),
        color=0xf1c40f
    )

    target_image = image.url if image else (image_url if image_url else None)
    if target_image:
        embed.set_image(url=target_image)

    embed.set_footer(text="Powered by Aegis Bot / Shop")

    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ ส่งหน้าต่างติดต่อแอดมินเรียบร้อยครับ", ephemeral=True)

# เปิดใช้งาน Web Server และรันบอท
keep_alive()
bot.run(token)
