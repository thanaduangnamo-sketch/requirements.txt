import discord
from discord.ext import commands
from discord.ui import View, Button
import os
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 ระบบจำลองเว็บพอร์ต ป้องกัน Render ตัดการเชื่อมต่อ
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()


# ==========================================
# 🤖 ตั้งค่าบอท Discord
# ==========================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.environ.get("DISCORD_TOKEN", "ใส่ Token ของบอทในนี้")


@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# ==========================================
# 💾 แผงควบคุมระบบ SaveRoles System
# ==========================================
class SaveRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศ", emoji="✅", style=discord.ButtonStyle.primary, custom_id="saveroles_save", row=1)
    async def save_roles(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("✅ บันทึกข้อมูล (เซฟยศ) ของคุณเรียบร้อยแล้ว!", ephemeral=True)

    @discord.ui.button(label="รับยศคืน", emoji="🔄", style=discord.ButtonStyle.success, custom_id="saveroles_restore", row=1)
    async def restore_roles(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 ดึงข้อมูลและทำการคืนยศให้คุณเรียบร้อยแล้ว!", ephemeral=True)

    @discord.ui.button(label="ดูข้อมูลผู้ใช้", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="saveroles_info", row=1)
    async def user_info(self, button: Button, interaction: discord.Interaction):
        embed = discord.Embed(
            title="👤 ข้อมูลการเซฟยศของคุณ",
            description=f">>> **ผู้ใช้งาน:** {interaction.user.mention}\n- สถานะ: ปกติ\n- ยศที่บันทึกไว้: (ยังไม่มีข้อมูล)",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="รีวิว", emoji="⭐", style=discord.ButtonStyle.danger, custom_id="saveroles_review", row=1)
    async def review_system(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("⭐ ขอบคุณที่สนใจรีวิวระบบของเรา! สามารถพิมพ์ข้อความรีวิวได้เลยครับ", ephemeral=True)


# ==========================================
# 💬 คำสั่ง Slash Command และ Prefix Command: /saveroles และ !saveroles
# ==========================================
@bot.tree.command(name="saveroles", description="ส่งแผงควบคุมระบบ SaveRoles System (เซฟยศ/คืนยศ)")
async def saveroles_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="SaveRoles System",
        description=(
            "### 🗄️ บอทเซฟยศอัตโนมัติ กันหลุดดิส\n\n"
            "🟢 **คนยังไม่เคยเซฟ** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( เซฟยศ ) เพื่อทำการเก็บข้อมูล\n"
            "```\n"
            "🟢 **คนมาเอายศคืน** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( รับยศคืน ) เพื่อรับยศคืน\n"
            "+ ในกรณีดิสบิน เผลอออกดิส หรือดิสหลุด หรืออยากออกเข้าใหม่\n"
            "```\n\n"
            "⚠️ **ข้อความจากแอดมิน** ⚠️\n"
            "```diff\n"
            "- ❗ : บอทมีปัญหาโปรดแจ้งแอดมินโดยทันที\n"
            "```"
        ),
        color=discord.Color.from_rgb(40, 42, 54)
    )
    # ใส่ลิงก์ GIF ตามที่คุณต้องการ
    embed.set_image(url="https://media.discordapp.net/attachments/1168490971990851645/1168892040562610278/standard.gif?ex=6a72864b&is=6a7134cb&hm=d305063fd143d3c83dda97b9ada40666a7a91df4e1d99193b474fb132d2d1d5b&")
    
    await interaction.response.send_message(embed=embed, view=SaveRolesView())


@bot.command(name="saveroles")
@commands.has_permissions(administrator=True)
async def saveroles_prefix(ctx):
    embed = discord.Embed(
        title="SaveRoles System",
        description=(
            "### 🗄️ บอทเซฟยศอัตโนมัติ กันหลุดดิส\n\n"
            "🟢 **คนยังไม่เคยเซฟ** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( เซฟยศ ) เพื่อทำการเก็บข้อมูล\n"
            "```\n"
            "🟢 **คนมาเอายศคืน** 🟢\n"
            "```asciidoc\n"
            "+ ให้กดปุ่ม ( รับยศคืน ) เพื่อรับยศคืน\n"
            "+ ในกรณีดิสบิน เผลอออกดิส หรือดิสหลุด หรืออยากออกเข้าใหม่\n"
            "```\n\n"
            "⚠️ **ข้อความจากแอดมิน** ⚠️\n"
            "```diff\n"
            "- ❗ : บอทมีปัญหาโปรดแจ้งแอดมินโดยทันที\n"
            "```"
        ),
        color=discord.Color.from_rgb(40, 42, 54)
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1168490971990851645/1168892040562610278/standard.gif?ex=6a72864b&is=6a7134cb&hm=d305063fd143d3c83dda97b9ada40666a7a91df4e1d99193b474fb132d2d1d5b&")
    
    await ctx.message.delete()
    await ctx.send(embed=embed, view=SaveRolesView())


# ==========================================
# 🚀 รันบอทและเว็บเซิร์ฟเวอร์
# ==========================================
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
