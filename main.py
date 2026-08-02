# ==========================================
# 🎫 ระบบ Ticket (Persistent View แบบดีไซน์ใหม่)
# ==========================================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="สร้าง Ticket", style=discord.ButtonStyle.secondary, emoji="🎟️", custom_id="aegis_persistent_ticket:button")
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
            description=f"สวัสดีครับคุณ {user.mention} แจ้งรายละเอียดปัญหาหรือเรื่องที่ต้องการติดต่อแอดมินไว้ได้เลยครับ!",
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


@bot.tree.command(name="ติดต่อแอดมิน", description="สร้างระบบติดต่อแอดมิน / แจ้งปัญหา (Ticket ดีไซน์ใหม่)")
@app_commands.describe(รูปภาพ="อัปโหลดรูปภาพแบนเนอร์ (ไม่บังคับ)", ลิงก์รูปภาพ="หรือใส่ลิงก์รูปภาพ URL (ไม่บังคับ)")
async def ticket_command(interaction: discord.Interaction, รูปภาพ: discord.Attachment = None, ลิงก์รูปภาพ: str = None):
    embed = discord.Embed(
        title="🎟️  ระบบ Ticket",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "> \"ทุกปัญหา มีทางออก\"\n"
            "> \"ทีมงานพร้อมช่วยเหลือคุณ\"\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "**กดปุ่มด้านล่างเพื่อสร้าง Ticket**"
        ),
        color=0x2b2d31
    )

    target_image = รูปภาพ.url if รูปภาพ else (ลิงก์รูปภาพ if ลิงก์รูปภาพ else None)
    if target_image:
        embed.set_image(url=target_image)

    embed.set_footer(text="Aegis Bot / Shop — Support System")

    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ ส่งหน้าต่างติดต่อแอดมินดีไซน์ใหม่เรียบร้อยแล้วครับ", ephemeral=True)
