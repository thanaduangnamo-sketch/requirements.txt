import discord
from discord.ext import commands
from discord.ui import View, Button
import os
from flask import Flask
from threading import Thread

# ==========================================
# ⚙️ ตั้งค่าไอดีโรลยศที่ต้องการเซฟ/คืน
# ==========================================
ROLE_ID_TO_SAVE = 1326066039481565225  # <-- เปลี่ยนเป็น ID ยศของคุณที่นี่

# ==========================================
# 🌐 ระบบเว็บเซิร์ฟเวอร์ผูกพอร์ต Render
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
# 💾 แผงควบคุมระบบ SaveRoles System (ระบบแท็กยศดิสคอร์ด)
# ==========================================
class SaveRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศ", emoji="✅", style=discord.ButtonStyle.primary, custom_id="saveroles_save", row=1)
    async def save_roles(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(ROLE_ID_TO_SAVE)
        if not role:
            return await interaction.response.send_message("❌ ไม่พบยศที่กำหนดในระบบ โปรดตรวจสอบ ID ยศอีกครั้ง", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.response.send_message(f"✅ บันทึกข้อมูลและเซฟยศ {role.mention} ของคุณเรียบร้อยแล้ว!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ คุณยังไม่มี {role.mention} นี้ในตัว จึงไม่สามารถเซฟได้ครับ", ephemeral=True)

    @discord.ui.button(label="รับยศคืน", emoji="🔄", style=discord.ButtonStyle.success, custom_id="saveroles_restore", row=1)
    async def restore_roles(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(ROLE_ID_TO_SAVE)
        if not role:
            return await interaction.response.send_message("❌ ไม่พบยศที่กำหนดในระบบ โปรดตรวจสอบ ID ยศอีกครั้ง", ephemeral=True)

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"🔄 ดึงข้อมูลและทำการคืนยศ {role.mention} ให้คุณเรียบร้อยแล้ว!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการคืนยศ: {e}", ephemeral=True)

    @discord.ui.button(label="ดูข้อมูลผู้ใช้", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="saveroles_info", row=1)
    async def user_info(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(ROLE_ID_TO_SAVE)
        role_name = role.mention if role else "ไม่พบยศ"
        
        embed = discord.Embed(
            title="👤 ข้อมูลการเซฟยศของคุณ",
            description=f">>> **ผู้ใช้งาน:** {interaction.user.mention}\n- สถานะ: ปกติ\n- ยศที่ผูกไว้: {role_name}",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="รีวิว", emoji="⭐", style=discord.ButtonStyle.danger, custom_id="saveroles_review", row=1)
    async def review_system(self, interaction: discord.Interaction, button: Button):
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
