# ==========================================
# ⚡ DDOS SAIKUTO CONTROL PANEL (สำหรับเล่นขำๆ)
# ==========================================
import asyncio
import time

# เก็บข้อมูลคูลดาวน์ของผู้ใช้ (User ID -> เวลาที่สามารถใช้งานได้อีกครั้ง)
ddos_cooldowns = {}
# ระบบล็อคคิว (ให้ใช้ได้ทีละ 1 คนตามกติกา)
ddos_current_user = None


class DdosModal(discord.ui.Modal, title="⚡ DDOS SAIKUTO — กรอกเป้าหมาย"):
    def __init__(self, duration: int, mode: str):
        super().__init__()
        self.duration = duration
        self.mode = mode

        self.url_input = discord.ui.TextInput(
            label="กรอก URL เป้าหมายที่ต้องการทดสอบ",
            style=discord.TextStyle.short,
            placeholder="https://example.com",
            required=True,
            max_length=200
        )
        self.add_item(self.url_input)

    async def on_submit(self, interaction: discord.Interaction):
        global ddos_current_user
        target_url = self.url_input.value.strip()

        # แจ้งเตือนเริ่มต้นจำลองการทำงาน
        embed = discord.Embed(
            title="⚡กำลังเริ่มกระบวนการ DDOS Saikuto...",
            description=(
                f"🎯 **เป้าหมาย:** `{target_url}`\n"
                f"⏱️ **ระยะเวลา:** `{self.duration} วินาที`\n"
                f"⚙️ **โหมด:** `{self.mode}`\n"
                f"🔄 **สถานะ:** กำลังส่งคำขอ (Requests)..."
            ),
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # จำลองการทำงานนับเวลาถอยหลัง
        for remaining in range(self.duration, 0, -5 if self.duration >= 10 else -1):
            await asyncio.sleep(min(5, remaining))

        # ปลดล็อคคิวเมื่อทำเสร็จ
        ddos_current_user = None

        # ส่งผลลัพธ์จำลองความสำเร็จ
        success_embed = discord.Embed(
            title="✅ Aegis Bot / shop — สำเร็จ!",
            description=(
                f"🎉 การทดสอบจำลองเสร็จสิ้นเรียบร้อย!\n\n"
                f"🎯 **เป้าหมาย:** `{target_url}`\n"
                f"⏱️ **เวลาที่ใช้:** `{self.duration} วินาที`\n"
                f"⚙️ **โหมด:** `{self.mode}` (ผ่านพร็อกซี่ 2,841 ตัว)\n"
                f"📊 **สถานะผลลัพธ์:** จำลองการส่งข้อมูลสำเร็จ (จำลองเพื่อความสนุก)"
            ),
            color=0x2ecc71
        )
        await interaction.followup.send(embed=success_embed, ephemeral=True)


class DdosSelect(discord.ui.Select):
    def __init__(self, is_vip: bool):
        self.is_vip = is_vip
        max_time = 500 if is_vip else 50
        
        # สร้างตัวเลือก Dropdown ตามสิทธิ์ (VIP ได้สูงสุด 500 วิ, ปกติ 50 วิ)
        options = [
            discord.SelectOption(label="⏱️ 10 วินาที (ทดสอบสั้นๆ)", value="10", description="โหมดรวดเร็ว เหมาะสำหรับการเทสระบบ"),
            discord.SelectOption(label="⏱️ 30 วินาที (มาตรฐาน)", value="30", description="ความเร็วกำลังดี"),
            discord.SelectOption(label=f"⏱️ {max_time} วินาที (สูงสุดของระดับคุณ)", value=str(max_time), description=f"จัดเต็มเวลาสูงสุดสำหรับ {'VIP' if is_vip else 'Member ปกติ'}"),
        ]
        super().__init__(placeholder="👉 เลือกระยะเวลา (Duration) ที่นี่...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        global ddos_current_user
        user = interaction.user
        current_time = time.time()

        # 1. เช็คคิว (1 คนต่อครั้ง)
        if ddos_current_user and ddos_current_user != user.id:
            return await interaction.response.send_message("❌ ระบบกำลังใช้งานโดยผู้อื่นอยู่ กรุณารอสักครู่ (ใช้ได้ 1 คนต่อครั้ง)", ephemeral=True)

        # 2. เช็คคูลดาวน์
        cooldown_time = 900 if self.is_vip else 3600  # VIP 15 นาที, ปกติ 1 ชม.
        if user.id in ddos_cooldowns:
            remaining_cd = ddos_cooldowns[user.id] - current_time
            if remaining_cd > 0:
                mins = int(remaining_cd // 60)
                secs = int(remaining_cd % 60)
                return await interaction.response.send_message(f"⏳ คุณติดคูลดาวน์อยู่! กรุณารออีก `{mins} นาที {secs} วินาที` ก่อนใช้งานอีกครั้ง", ephemeral=True)

        # ล็อคคิวให้ผู้ใช้นี้
        ddos_current_user = user.id
        # ตั้งเวลาคูลดาวน์ใหม่
        ddos_cooldowns[user.id] = current_time + cooldown_time

        selected_duration = int(self.values[0])

        # ส่ง View เลือกระหมด Direct หรือ Proxy ต่อ
        view = DdosModeView(selected_duration)
        await interaction.response.send_message(
            f"⏱️ คุณเลือกเวลา **{selected_duration} วินาที** เรียบร้อย!\n👉 ขั้นตอนถัดไป: เลือกโหมดการโจมตีด้านล่างครับ",
            view=view,
            ephemeral=True
        )


class DdosModeView(discord.ui.View):
    def __init__(self, duration: int):
        super().__init__(timeout=60)
        self.duration = duration

    @discord.ui.button(label="🚀 โหมด Direct (เร็ว)", style=discord.ButtonStyle.danger, emoji="⚡")
    async def direct_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DdosModal(self.duration, "Direct (รวดเร็ว)"))

    @discord.ui.button(label="🛡️ โหมด Proxy (ซ่อนตัว)", style=discord.ButtonStyle.primary, emoji="🌐")
    async def proxy_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DdosModal(self.duration, "Proxy (2,841 ตัว)"))


class DdosControlPanelView(discord.ui.View):
    def __init__(self, is_vip: bool):
        super().__init__(timeout=None)
        self.add_item(DdosSelect(is_vip))


@bot.tree.command(name="ddos_panel", description="เปิดแผงควบคุมระบบจำลอง DDOS Saikuto (สำหรับเล่นขำๆ)")
async def ddos_panel_command(interaction: discord.Interaction):
    # ตรวจสอบยศ VIP (คุณสามารถเปลี่ยนชื่อ Role หรือ ID ตามเซิร์ฟเวอร์ของคุณได้ ตรงนี้เช็คจากชื่อยศว่ามีคำว่า 'vip' หรือไม่)
    is_vip = any("vip" in role.name.lower() for role in interaction.user.roles)
    
    role_name = "⭐ VIP" if is_vip else "● MEMBER ปกติ"
    max_sec = "500 วิ" if is_vip else "50 วิ"
    cd_time = "15 นาที" if is_vip else "1 ชม."
    time_options = "10 ~ 500 วิ" if is_vip else "10 ~ 50 วิ"

    embed = discord.Embed(
        title="⚡ DDOS SAIKUTO — CONTROL PANEL ⚡",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ยินดีต้อนรับ {interaction.user.mention} สู่ระบบAegis Bot / shop\n"
            "เลือกระยะเวลาจาก Dropdown ด้านล่าง\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**ระดับของคุณ:**\n`{role_name}`\n\n"
            "**ตารางเปรียบเทียบสิทธิ์:**\n"
            "```text\n"
            "╔══════════════╦══════════╦══════════╗\n"
            "║   สิทธิ์     ║  ⭐ VIP  ║  👤 ปกติ ║\n"
            "╠══════════════╬══════════╬══════════╣\n"
            "║ ⏱ ยิงสูงสุด ║  500 วิ  ║  50 วิ   ║\n"
            "║ ⏳ คูลดาวน์  ║  15 นาที ║  1 ชม.   ║\n"
            "║ ⚡ ลำดับคิว  ║  สูง     ║  ปกติ    ║\n"
            "╚══════════════╩══════════╩══════════╝\n"
            "```\n"
            "📌 **สิทธิ์ของคุณปัจจุบัน:**\n"
            f"• [ยิงสูงสุด]     = `{max_sec}`\n"
            f"• [คูลดาวน์]      = `{cd_time}`\n"
            f"• [ตัวเลือกเวลา]  = `{time_options}`\n"
            "• [Concurrent]    = `50 req`\n\n"
            "🌐 **ระบบพร็อกซี่:**\n"
            "• [สถานะ]    = `พร้อม`\n"
            "• [จำนวน]    = `2,841 ตัว`\n"
            "• [แหล่งที่มา] = `4 แหล่ง`\n"
            "• [Cache]    = `5 นาที`\n\n"
            "🟢 **สถานะระบบ:** ว่าง — พร้อมใช้งาน | คูลดาวน์: พร้อมใช้งาน\n\n"
            "┌──────────────────────────────────────┐\n"
            "│  📌 กฎการใช้งาน Aegis Bot / shop        │\n"
            "├──────────────────────────────────────┤\n"
            "│ 1. ใช้ได้ 1 คนต่อครั้งเท่านั้น      │\n"
            "│ 2. ห้ามยิงซ้ำก่อนหมดคูลดาวน์        │\n"
            "│ 3. เลือกเวลา → เลือกโหมด → กรอก URL │\n"
            "│ 4. โหมด Direct = เร็ว / Proxy = ซ่อน │\n"
            "│ 5. ผลลัพธ์จะแสดงเมื่อยิงเสร็จ       │\n"
            "└──────────────────────────────────────┘"
        ),
        color=0xe74c3c
    )
    embed.set_footer(text="DDOS SAIKUTO V6 — สำหรับทดสอบและเล่นสนุกเท่านั้น")

    view = DdosControlPanelView(is_vip)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ เปิดแผงควบคุม DDOS Saikuto สำเร็จ!", ephemeral=True)
