import os
import discord
from discord.ext import commands

# ตั้งค่า Intents ที่จำเป็น
intents = discord.Intents.default()
intents.members = True

client = commands.Bot(command_prefix="!", intents=intents)

# ⚙️ ตั้งค่า ID ยศ และลิงก์รูปภาพของคุณที่นี่
VERIFY_ROLE_ID = 1537840114380709998  # ใส่ ID ยศที่จะให้หลังยืนยัน
BANNER_IMAGE = "https://i.pinimg.com/736x/d1/50/12/d15012026d745a4302fd5bccffc437a2.jpg"

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # ทำให้ปุ่มใช้งานได้ตลอดเวลา

    @discord.ui.button(
        label="ยืนยันตัวตน", 
        style=discord.ButtonStyle.green, 
        custom_id="modern_verify_button", 
        emoji="✨"
    )
    async def verify_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        
        if not role:
            await interaction.response.send_message("❌ เกิดข้อผิดพลาด: ไม่พบยศที่ตั้งค่าไว้ในระบบ", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message("⚠️ คุณได้ทำการยืนยันตัวตนไปเรียบร้อยแล้วครับ!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("🎉 **ยืนยันตัวตนสำเร็จ!** ยินดีต้อนรับเข้าสู่เซิร์ฟเวอร์ของเราครับ", ephemeral=True)

@client.event
async def on_ready():
    client.add_view(VerifyView())
    print(f"🚀 บอทออนไลน์แล้วในชื่อ: {client.user}")

# คำสั่งสำหรับส่งหน้าต่างยืนยันตัวตน (พิมพ์ !setup ในห้องที่ต้องการ)
@client.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    embed = discord.Embed(
        title="🛡️ **VERIFICATION SYSTEM**",
        description="กรุณากดปุ่ม **\"ยืนยันตัวตน\"** ด้านล่างนี้เพื่อปลดล็อกห้องแชทและเข้าถึงเนื้อหาทั้งหมดภายในเซิร์ฟเวอร์",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_image(url=BANNER_IMAGE)
    embed.set_footer(text="ระบบรักษาความปลอดภัยอัตโนมัติ", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    await ctx.send(embed=embed, view=VerifyView())
    await ctx.message.delete()

# ดึง Token จาก Environment Variables ของ Render ป้องกัน Token หลุดและแก้ปัญหา Error
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Error: ไม่พบ DISCORD_TOKEN ใน Environment Variables!")
else:
    client.run(TOKEN)
