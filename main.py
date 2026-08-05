import discord
from discord.ext import commands
from discord.ui import View, Button, Select, SelectMenu
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
# 💾 1. ระบบ SaveRoles View
# ==========================================
class SaveRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เซฟยศ", emoji="✅", style=discord.ButtonStyle.primary, custom_id="saveroles_save", row=1)
    async def save_roles(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        roles_to_save = [role.id for role in user.roles if not role.is_default() and not role.managed]

        if not roles_to_save:
            return await interaction.response.send_message("⚠️ คุณยังไม่มีโรลยศใดๆ ที่สามารถบันทึกได้ครับ", ephemeral=True)

        saved_user_roles[user.id] = roles_to_save
        
        role_mentions = ", ".join([f"<@&{r_id}>" for r_id in roles_to_save])
        await interaction.response.send_message(f"✅ บันทึกข้อมูลและเซฟยศทั้งหมดของคุณเรียบร้อยแล้ว!\n📌 **ยศที่บันทึกไว้:** {role_mentions}", ephemeral=True)

    @discord.ui.button(label="รับยศคืน", emoji="🔄", style=discord.ButtonStyle.success, custom_id="saveroles_restore", row=1)
    async def restore_roles(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        if user.id not in saved_user_roles or not saved_user_roles[user.id]:
            return await interaction.response.send_message("❌ ไม่พบข้อมูลการเซฟยศของคุณในระบบ กรุณากดปุ่ม 'เซฟยศ' ก่อนครับ", ephemeral=True)

        role_ids = saved_user_roles[user.id]
        roles_to_add = []

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
# 🎫 2. ระบบ Tickets View (เปิดตั๋ว / ปิดตั๋ว)
# ==========================================
class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ปิดตั๋ว", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 กำลังปิดห้องตั๋วนี้ใน 5 วินาที...", ephemeral=False)
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass


class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="ติดต่อแอดมินทั่วไป", description="สอบถามปัญหาทั่วไปหรือพูดคุยกับแอดมิน", emoji="💬"),
            discord.SelectOption(label="แจ้งปัญหาบอท/ระบบ", description="แจ้งบัค แจ้งปัญหาการใช้งานระบบ", emoji="🛠️"),
            discord.SelectOption(label="ติดต่อซื้อสินค้า/เติมเงิน", description="สอบถามเรื่องสินค้าและบริการ", emoji="🛒"),
        ]
        super().__init__(placeholder="📌 กรุณาเลือกหัวข้อที่ต้องการติดต่อ...", min_values=1, max_values=1, options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        
        # ค้นหาหมวดหมู่สำหรับตั๋ว (ถ้ามีห้องชื่อ Tickets หรือสร้างใหม่)
        category = discord.utils.get(guild.categories, name="🎫 | TICKETS")
        if not category:
            category = await guild.create_category("🎫 | TICKETS")

        # ตั้งค่าสิทธิ์เข้าถึงห้องเฉพาะแอดมินและตัวผู้ใช้เอง
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # สร้างชื่อห้องตั๋ว
        channel_name = f"ticket-{member.name}"
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            return await interaction.response.send_message(f"❌ คุณมีห้องตั๋วเปิดอยู่แล้วที่ {existing_channel.mention}", ephemeral=True)

        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        
        embed = discord.Embed(
            title=f"🎫 ห้องตั๋วของคุณ: {self.values[0]}",
            description=f"สวัสดีครับคุณ {member.mention}\n- **หัวข้อ:** {self.values[0]}\n- โปรดพิมพ์รายละเอียดปัญหาของคุณไว้ได้เลย แอดมินจะรีบเข้ามาช่วยเหลือโดยเร็วที่สุดครับ",
            color=discord.Color.green()
        )
        
        view = TicketCloseView()
        await ticket_channel.send(content=f"{member.mention} @here", embed=embed, view=view)
        await interaction.response.send_message(f"✅ เปิดห้องตั๋วให้คุณแล้วที่ {ticket_channel.mention}", ephemeral=True)


class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ==========================================
# 💬 คำสั่ง Slash Commands และ Prefix Commands
# ==========================================

# คำสั่ง /saveroles
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


# คำสั่ง /ticket (สำหรับส่งแผงเปิดตั๋ว)
@bot.tree.command(name="ticket", description="ส่งแผงควบคุมระบบ Tickets (ติดต่อแอดมิน/แจ้งปัญหา)")
@app.default_permissions(administrator=True)
async def ticket_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 ระบบเปิดตั๋ว / Tickets Support",
        description="> หากต้องการติดต่อแอดมิน แจ้งปัญหา หรือสอบถามข้อมูลเพิ่มเติม\n> สามารถเลือกหัวข้อจากเมสด้านล่างนี้เพื่อเปิดห้องส่วนตัวได้ทันทีครับ!",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=TicketView())


@bot.command(name="ticket")
@commands.has_permissions(administrator=True)
async def ticket_prefix(ctx):
    embed = discord.Embed(
        title="🎫 ระบบเปิดตั๋ว / Tickets Support",
        description="> หากต้องการติดต่อแอดมิน แจ้งปัญหา หรือสอบถามข้อมูลเพิ่มเติม\n> สามารถเลือกหัวข้อจากเมสด้านล่างนี้เพื่อเปิดห้องส่วนตัวได้ทันทีครับ!",
        color=discord.Color.blurple()
    )
    await ctx.message.delete()
    await ctx.send(embed=embed, view=TicketView())


# ==========================================
# 🚀 รันบอทและเว็บเซิร์ฟเวอร์
# ==========================================
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
