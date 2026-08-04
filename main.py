import discord
from discord.ext import commands
from discord.ui import View, Button
import os
from flask import Flask
from threading import Thread

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

# ตัวแปรเก็บข้อมูลยศของผู้ใช้ชั่วคราว (Dictionary: {user_id: [list of role_ids]})
saved_user_roles = {}


@bot.event
async def on_ready():
    print(f"BOT LOGIN: {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced successfully.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# ==========================================
# 💾 แผงควบคุมระบบ SaveRoles System (บันทึกทุกยศ)
# ==========================================
class SaveRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศ", emoji="✅", style=discord.ButtonStyle.primary, custom_id="saveroles_save", row=1)
    async def save_roles(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        # กรองเอาเฉพาะยศที่มีอยู่จริง และไม่ใช่ @everyone หรือยศ Managed (ยศบอท/บูสต์)
        roles_to_save = [role.id for role in user.roles if not role.is_default() and not role.managed]

        if not roles_to_save:
            return await interaction.response.send_message("⚠️ คุณยังไม่มีโรลยศใดๆ ที่สามารถบันทึกได้ครับ", ephemeral=True)

        saved_user_roles[user.id] = roles_to_save
        
        # ดึงชื่อยศมาแสดงแบบแท็ก
        role_mentions = ", ".join([f"<@&{r_id}>" for r_id in roles_to_save])
        await interaction.response.send_message(f"✅ บันทึกข้อมูลและเซฟยศทั้งหมดของคุณเรียบร้อยแล้ว!\n📌 **ยศที่บันทึกไว้:** {role_mentions}", ephemeral=True)

    @discord.ui.button(label="รับยศคืน", emoji="🔄", style=discord.ButtonStyle.success, custom_id="saveroles_restore", row=1)
    async def restore_roles(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        if user.id not in saved_user_roles or not saved_user_roles[user.id]:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลการเซฟยศของคุณในระบบ กรุณากดปุ่ม 'เซฟยศ' ก่อนครับ", ephemeral=True)

        role_ids = saved_user_roles[user.id]
        roles_to_add = []
        failed_roles = []

        for r_id in role_ids:
            role = interaction.guild.get_role(r_id)
            if role:
                roles_to_add.append(role)

        try:
            if roles_to_add:
                await user.add_roles(*roles_to_add)
                role_mentions = ", ".join([r.mention for r in roles_to_add])
                await interaction.response.send_message(f"🔄 ดึงข้อมูลและทำการคืนยศทั้งหมดให้คุณเรียบร้อยแล้ว!\n🎉 **ยศที่ได้รับคืน:** {role_mentions}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ ไม่พบยศเหล่านี้ภายในเซิร์ฟเวอร์แล้ว (อาจถูกลบไปแล้ว)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ เกิดข้อผิดพลาดในการคืนยศ (บอทอาจไม่มีสิทธิ์จัดการยศเหล่านี้): {e}", ephemeral=True)

    @discord.ui.button(label="ดูข้อมูลผู้ใช้", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="saveroles_info", row=1)
    async def user_info(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        role_ids = saved_user_roles.get(user.id, [])
        
        if role_ids:
            role_mentions = ", ".join([f"<@&{r_id}>" for r_id in role_ids])
            status_text = f"บันทึกแล้ว ({len(role_ids)} ยศ)"
        else:
            role_mentions = "ยังไม่มีข้อมูลการเซฟ"
            status_text = "ยังไม่ได้เซฟ"

        embed = discord.Embed(
            title="👤 ข้อมูลการเซฟยศของคุณ",
            description=f">>> **ผู้ใช้งาน:** {user.mention}\n- **สถานะ:** {status_text}\n- **ยศที่บันทึกไว้:** {role_mentions}",
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
