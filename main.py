import discord
from discord import app_commands
from discord.ext import commands

# ==========================================
# 🟩 ระบบรับยศทั่วไป (Role Select Menu)
# ==========================================
class GeneralRoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        # ดึงรายชื่อยศตัวอย่าง หรือคุณสามารถเปลี่ยนชื่อยศและ ID ยศตรงนี้ได้ตามต้องการ
        # แนะนำให้ใส่เป็น Role ID หรือชื่อยศที่มีอยู่ในเซิร์ฟเวอร์ของคุณ
        options = [
            discord.SelectOption(label="ยศที่ 1 (ตัวอย่าง)", description="กดเพื่อรับหรือคืนยศนี้", emoji="🟢", value="ROLE_ID_1"),
            discord.SelectOption(label="ยศที่ 2 (ตัวอย่าง)", description="กดเพื่อรับหรือคืนยศนี้", emoji="🟢", value="ROLE_ID_2"),
            discord.SelectOption(label="ยศที่ 3 (ตัวอย่าง)", description="กดเพื่อรับหรือคืนยศนี้", emoji="🟢", value="ROLE_ID_3"),
        ]
        super().__init__(
            placeholder="【 ☁️ เลือกรับยศที่ต้องการ 】", 
            min_values=1, 
            max_values=1, 
            options=options, 
            custom_id="general_role_select:dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0]) # หรือถ้าใช้ชื่อยศ ให้ปรับเปลี่ยนตามความเหมาะสม
        
        # ค้นหายศจาก ID (แนะนำให้เปลี่ยนค่าใน value เป็น ID ของยศจริงในเซิร์ฟเวอร์)
        # ตัวอย่างนี้สมมติว่าเก็บบันทึกเป็น ID ของยศ
        role = interaction.guild.get_role(role_id)

        if not role:
            return await interaction.response.send_message("❌ ไม่พบยศนี้ในระบบเซิร์ฟเวอร์ กรุณาติดต่อแอดมิน", ephemeral=True)

        user = interaction.user

        # ตรวจสอบว่าผู้ใช้มีศนี้อยู่แล้วหรือยัง (กดซ้ำเพื่อคืนยศ / Toggle)
        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"🗑️ ทำการคืนยศ **{role.name}** เรียบร้อยแล้วครับ", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ คุณได้รับยศ **{role.name}** เรียบร้อยแล้วครับ!", ephemeral=True)


class GeneralRoleView(discord.ui.View):
    def __init__(self, guild: discord.Guild = None):
        super().__init__(timeout=None)
        self.add_item(GeneralRoleSelect(guild))


@bot.tree.command(name="setup_roles", description="สร้างระบบรับยศทั่วไปดีไซน์สวยงามเหมือนในภาพตัวอย่าง")
@app_commands.describe(image_url="ใส่ลิงก์รูปภาพแบนเนอร์ด้านใน Embed (ไม่บังคับ)")
async def setup_roles_command(interaction: discord.Interaction, image_url: str = "https://i.pinimg.com/736x/de/f8/80/def8807c89475990941ba4617b4cbc2e.jpg"):
    embed = discord.Embed(
        title="💬 ระบบรับยศทั่วไป",
        description=(
            "`.•° 💧 𝓡𝓪𝓲𝓷 𝓓𝓻𝓸𝓹𝓼 💧 °•.`\n\n"
            "🟢 : เลือกรับยศที่ต้องการจากเมนูด้านล่าง\n"
            "🟢 : เลือกยศซ้ำ เพื่อคืนยศ\n\n"
            "`.•° 💧 𝓡𝓪𝓲𝓷 𝓓𝓻𝓸𝓹𝓼 💧 °•.`"
        ),
        color=0x2b2d31
    )
    
    if image_url:
        embed.set_image(url=image_url)
        
    embed.set_footer(text="© GET ROLES BOT")

    view = GeneralRoleView(interaction.guild)
    
    # ส่งข้อความไปยังห้องที่ใช้คำสั่ง
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ สร้างหน้าต่างระบบรับยศเรียบร้อยแล้วครับ", ephemeral=True)
