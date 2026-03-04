import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()




keep_alive()

# DEBUG - mostra tutte le variabili d'ambiente disponibili
print("=== ENV VARS ===")
for key in os.environ:
    if "TOKEN" in key or "DISCORD" in key:
        print(f"  Trovato: {key}")
print("================")


# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

COLOR_MAIN    = 0x5865F2
COLOR_SUCCESS = 0x2ECC71
COLOR_ERROR   = 0xE74C3C
COLOR_WARN    = 0xF39C12
COLOR_INFO    = 0x3498DB

TICKET_TYPES = {
    "support":  {"label": "Support",  "emoji": "🔧", "description": "Request support from staff.",     "color": COLOR_INFO},
    "purchase": {"label": "Purchase", "emoji": "🛒", "description": "Get assistance with purchasing.", "color": COLOR_SUCCESS},
    "media":    {"label": "Media",    "emoji": "🎬", "description": "Media inquiries or promotions.",  "color": COLOR_MAIN},
    "resell":   {"label": "Resell",   "emoji": "🔁", "description": "Reselling related inquiries.",    "color": COLOR_WARN},
}

# ─────────────────────────────────────────────
#  MODAL
# ─────────────────────────────────────────────
class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        emoji = TICKET_TYPES[ticket_type]["emoji"]
        label = TICKET_TYPES[ticket_type]["label"]
        super().__init__(title=f"{emoji} Open a {label} Ticket")
        self.ticket_type = ticket_type

        if ticket_type == "purchase":
            self.field1 = discord.ui.TextInput(label="What do you want to purchase?", placeholder="Describe the product/service...", style=discord.TextStyle.short, required=True, max_length=100)
            self.field2 = discord.ui.TextInput(label="Where did you find us?", placeholder="e.g. YouTube, TikTok, Discord, Friend...", style=discord.TextStyle.short, required=True, max_length=100)
        elif ticket_type == "support":
            self.field1 = discord.ui.TextInput(label="Describe your issue", placeholder="Explain your problem in detail...", style=discord.TextStyle.paragraph, required=True, max_length=500)
            self.field2 = discord.ui.TextInput(label="Order ID (if applicable)", placeholder="Leave blank if not applicable", style=discord.TextStyle.short, required=False, max_length=50)
        elif ticket_type == "media":
            self.field1 = discord.ui.TextInput(label="Your platform / channel", placeholder="e.g. YouTube: @YourChannel", style=discord.TextStyle.short, required=True, max_length=100)
            self.field2 = discord.ui.TextInput(label="What is your inquiry about?", placeholder="Promotion, partnership, review...", style=discord.TextStyle.paragraph, required=True, max_length=300)
        elif ticket_type == "resell":
            self.field1 = discord.ui.TextInput(label="Your reselling platform", placeholder="e.g. Shopify, Discord Server...", style=discord.TextStyle.short, required=True, max_length=100)
            self.field2 = discord.ui.TextInput(label="Tell us about yourself", placeholder="Experience, audience size, goals...", style=discord.TextStyle.paragraph, required=True, max_length=300)

        self.add_item(self.field1)
        self.add_item(self.field2)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild = interaction.guild
        guild_conf = config.get(str(guild.id), {})

        category_id = guild_conf.get("ticket_category")
        category = guild.get_channel(int(category_id)) if category_id else None

        support_role_id = guild_conf.get("support_role")
        support_role = guild.get_role(int(support_role_id)) if support_role_id else None

        ticket_num = guild_conf.get("ticket_count", 0) + 1
        guild_conf["ticket_count"] = ticket_num
        config[str(guild.id)] = guild_conf
        save_config(config)

        channel_name = f"ticket-{ticket_num:04d}-{interaction.user.name.lower().replace(' ', '-')[:15]}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user:   discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me:           discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True)

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket #{ticket_num:04d} | {TICKET_TYPES[self.ticket_type]['label']} | {interaction.user} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        )

        t = TICKET_TYPES[self.ticket_type]
        embed = discord.Embed(
            title=f"{t['emoji']} {t['label']} Ticket",
            description=f"🙏 **Thank you for creating a {t['label']} ticket.**\nWhile you wait for a support agent, please provide the following details clearly.",
            color=t["color"],
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="🕐 While you wait…", value="🔧 Provide detailed information and clear screenshots of your issue.", inline=False)
        embed.add_field(name="⚠️ Important", value="Moderators will **never** request payment in DMs.\nIf this happens, contact management immediately.", inline=False)
        embed.add_field(name=f"💠 {self.field1.label}", value=f"```{self.field1.value}```", inline=False)
        if self.field2.value:
            embed.add_field(name=f"💠 {self.field2.label}", value=f"```{self.field2.value}```", inline=False)
        embed.add_field(name="👤 Opened by", value=interaction.user.mention, inline=True)
        embed.add_field(name="🎫 Ticket #", value=f"`#{ticket_num:04d}`", inline=True)
        embed.add_field(name="📅 Opened at", value=f"<t:{int(datetime.utcnow().timestamp())}:F>", inline=True)
        embed.set_footer(text="Staff will assist you shortly.", icon_url=guild.icon.url if guild.icon else None)

        view = TicketControlView(ticket_type=self.ticket_type, opener_id=interaction.user.id)
        mention_txt = interaction.user.mention
        if support_role:
            mention_txt += f" {support_role.mention}"

        msg = await ticket_channel.send(content=mention_txt, embed=embed, view=view)
        await msg.pin()

        confirm_embed = discord.Embed(title="✅ Ticket Created!", description=f"Your ticket: {ticket_channel.mention}\nWe'll be with you shortly!", color=COLOR_SUCCESS)
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        embed = discord.Embed(title="❌ Error", description=str(error), color=COLOR_ERROR)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────
#  SELECT MENU
# ─────────────────────────────────────────────
class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=v["label"], value=k, emoji=v["emoji"], description=v["description"]) for k, v in TICKET_TYPES.items()]
        super().__init__(placeholder="📋 Select Ticket Type…", min_values=1, max_values=1, options=options, custom_id="ticket_type_select")

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        for ch in interaction.guild.text_channels:
            if ch.topic and str(interaction.user) in ch.topic and "Ticket #" in ch.topic:
                embed = discord.Embed(title="⚠️ You already have an open ticket!", description=f"Please use: {ch.mention}", color=COLOR_WARN)
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.send_modal(TicketModal(ticket_type))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


# ─────────────────────────────────────────────
#  CLOSE CONFIRM
# ─────────────────────────────────────────────
class CloseConfirmView(discord.ui.View):
    def __init__(self, closer_id: int):
        super().__init__(timeout=30)
        self.closer_id = closer_id

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = discord.Embed(title="🔒 Ticket Closing…", description="This ticket will be deleted in **5 seconds**.", color=COLOR_ERROR, timestamp=datetime.utcnow())
        embed.add_field(name="Closed by", value=interaction.user.mention)
        embed.set_footer(text="Thank you for contacting us!")
        await interaction.channel.send(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Close cancelled.", ephemeral=True)
        self.stop()


# ─────────────────────────────────────────────
#  TICKET CONTROL BUTTONS
# ─────────────────────────────────────────────
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str = "support", opener_id: int = 0):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.opener_id = opener_id

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, emoji="✋", custom_id="claim_ticket")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        guild_conf = config.get(str(interaction.guild.id), {})
        support_role_id = guild_conf.get("support_role")
        support_role = interaction.guild.get_role(int(support_role_id)) if support_role_id else None
        is_staff = (support_role and support_role in interaction.user.roles) or interaction.user.guild_permissions.administrator
        if not is_staff:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Access Denied", description="Only staff members can claim tickets.", color=COLOR_ERROR), ephemeral=True)
        button.label = f"Claimed by {interaction.user.display_name}"
        button.disabled = True
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        embed = discord.Embed(title="✋ Ticket Claimed", description=f"{interaction.user.mention} has claimed this ticket!", color=COLOR_SUCCESS, timestamp=datetime.utcnow())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚠️ Close Ticket?", description="Are you sure? This action **cannot be undone**.", color=COLOR_WARN)
        await interaction.response.send_message(embed=embed, view=CloseConfirmView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.primary, emoji="➕", custom_id="add_user_ticket")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        guild_conf = config.get(str(interaction.guild.id), {})
        support_role_id = guild_conf.get("support_role")
        support_role = interaction.guild.get_role(int(support_role_id)) if support_role_id else None
        is_staff = (support_role and support_role in interaction.user.roles) or interaction.user.guild_permissions.administrator
        if not is_staff:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ Access Denied", description="Only staff can add users.", color=COLOR_ERROR), ephemeral=True)
        await interaction.response.send_modal(AddUserModal(interaction.channel))


class AddUserModal(discord.ui.Modal, title="➕ Add User to Ticket"):
    user_id = discord.ui.TextInput(label="User ID", placeholder="Enter the user's ID (e.g. 123456789012345678)", required=True, max_length=25)

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        try:
            member = interaction.guild.get_member(int(raw))
        except ValueError:
            member = None
        if not member:
            return await interaction.response.send_message(embed=discord.Embed(title="❌ User Not Found", description="Please provide a valid user ID.", color=COLOR_ERROR), ephemeral=True)
        await self.channel.set_permissions(member, view_channel=True, send_messages=True, attach_files=True)
        await interaction.response.send_message(embed=discord.Embed(title="✅ User Added", description=f"{member.mention} has been added to the ticket.", color=COLOR_SUCCESS))
        await self.channel.send(f"👋 {member.mention} has been added to this ticket.")


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────
@tree.command(name="setup", description="⚙️ Configure and send the Ticket Panel")
@app_commands.describe(channel="Channel for the panel", title="Panel title", description="Panel description", support_role="Staff role", ticket_category="Category for tickets", color="Hex color (e.g. 5865F2)", website="Your website", thumbnail_url="Thumbnail URL", banner_url="Banner URL")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, channel: discord.TextChannel, title: str = "🎫 Ticket Panel", description: str = "We are eagerly waiting to assist you!\n\n💠 **How Do I Contact Us?**\nSimply select your ticket type below!", support_role: discord.Role = None, ticket_category: discord.CategoryChannel = None, color: str = "5865F2", website: str = "", thumbnail_url: str = "", banner_url: str = ""):
    await interaction.response.defer(ephemeral=True)
    config = load_config()
    guild_conf = config.get(str(interaction.guild.id), {})
    if support_role:
        guild_conf["support_role"] = str(support_role.id)
    if ticket_category:
        guild_conf["ticket_category"] = str(ticket_category.id)
    guild_conf["panel_channel"] = str(channel.id)
    config[str(interaction.guild.id)] = guild_conf
    save_config(config)

    try:
        embed_color = int(color.lstrip("#"), 16)
    except ValueError:
        embed_color = COLOR_MAIN

    embed = discord.Embed(title=title, description=description, color=embed_color, timestamp=datetime.utcnow())
    if website:
        embed.add_field(name="🌐 Website", value=f"[{website}](https://{website.replace('https://','').replace('http://','')})", inline=False)
    embed.add_field(name="🛒 Payment Methods Accepted", value="💳 **Card** — via Website\n💰 **Crypto** — via Website\n🏦 **iDEAL / Bank** — via Website\n📱 **Apple Pay** — via Website\n💸 **PayPal F&F** — via Ticket", inline=False)
    embed.add_field(name="📋 Ticket Types", value="\n".join(f"{v['emoji']} **{v['label']}** — {v['description']}" for v in TICKET_TYPES.values()), inline=False)
    if support_role:
        embed.add_field(name="👥 Support Team", value=support_role.mention, inline=True)
    if ticket_category:
        embed.add_field(name="📁 Ticket Category", value=ticket_category.mention, inline=True)
    embed.set_footer(text=f"{interaction.guild.name} • Support System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    elif interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    if banner_url:
        embed.set_image(url=banner_url)

    await channel.send(embed=embed, view=TicketPanelView())
    confirm = discord.Embed(title="✅ Panel Sent!", description=f"Ticket panel sent to {channel.mention}.", color=COLOR_SUCCESS)
    confirm.add_field(name="Config", value=f"• Role: {support_role.mention if support_role else '`Not set`'}\n• Category: {ticket_category.mention if ticket_category else '`Not set`'}")
    await interaction.followup.send(embed=confirm, ephemeral=True)


@tree.command(name="close", description="🔒 Close the current ticket")
async def close_cmd(interaction: discord.Interaction):
    if "ticket-" not in interaction.channel.name:
        return await interaction.response.send_message(embed=discord.Embed(title="❌ Not a Ticket", description="Use this only inside a ticket channel.", color=COLOR_ERROR), ephemeral=True)
    embed = discord.Embed(title="⚠️ Close Ticket?", description="Are you sure? This action **cannot be undone**.", color=COLOR_WARN)
    await interaction.response.send_message(embed=embed, view=CloseConfirmView(interaction.user.id))


@tree.command(name="panel", description="📋 Re-send the ticket panel here")
@app_commands.checks.has_permissions(administrator=True)
async def panel_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎫 Ticket Panel", description="We are eagerly waiting to assist you!\n\n💠 **How Do I Contact Us?**\nSelect your ticket type below!", color=COLOR_MAIN, timestamp=datetime.utcnow())
    embed.add_field(name="📋 Types", value="\n".join(f"{v['emoji']} **{v['label']}** — {v['description']}" for v in TICKET_TYPES.values()), inline=False)
    embed.set_footer(text=f"{interaction.guild.name} • Support System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed, view=TicketPanelView())


@tree.command(name="config", description="⚙️ View bot configuration")
@app_commands.checks.has_permissions(administrator=True)
async def config_view(interaction: discord.Interaction):
    config = load_config()
    gc = config.get(str(interaction.guild.id), {})
    sr = interaction.guild.get_role(int(gc["support_role"])) if gc.get("support_role") else None
    cat = interaction.guild.get_channel(int(gc["ticket_category"])) if gc.get("ticket_category") else None
    pc = interaction.guild.get_channel(int(gc["panel_channel"])) if gc.get("panel_channel") else None
    embed = discord.Embed(title="⚙️ Configuration", color=COLOR_MAIN, timestamp=datetime.utcnow())
    embed.add_field(name="👥 Support Role",    value=sr.mention if sr else "`Not set`", inline=True)
    embed.add_field(name="📁 Ticket Category", value=cat.mention if cat else "`Not set`", inline=True)
    embed.add_field(name="📢 Panel Channel",   value=pc.mention if pc else "`Not set`", inline=True)
    embed.add_field(name="🎫 Total Tickets",   value=f"`{gc.get('ticket_count', 0)}`", inline=True)
    embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(title="❌ Missing Permissions", description="You need administrator permissions.", color=COLOR_ERROR)
    else:
        embed = discord.Embed(title="❌ Error", description=str(error), color=COLOR_ERROR)
    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(embed=embed, ephemeral=True)


@bot.event
async def on_ready():
    print(f"\n{'='*45}")
    print(f"  ✅  Logged in as: {bot.user} (ID: {bot.user.id})")
    print(f"  🌐  Guilds: {len(bot.guilds)}")
    print(f"{'='*45}\n")
    try:
        # Sync globale
        synced = await tree.sync()
        print(f"  ⚡  Synced globale: {len(synced)} command(s)")
        # Sync immediato su ogni server
        for guild in bot.guilds:
            try:
                tree.copy_global_to(guild=guild)
                guild_synced = await tree.sync(guild=guild)
                print(f"  ✅  Sync su {guild.name}: {len(guild_synced)} command(s)")
            except Exception as e:
                print(f"  ❌  Errore sync {guild.name}: {e}")
    except Exception as e:
        print(f"  ❌  Sync error: {e}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="🎫 Tickets | /setup"))


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Legge il .env manualmente, senza dotenv
    TOKEN = ""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DISCORD_TOKEN="):
                    TOKEN = line.split("=", 1)[1].strip()
                    break
    if not TOKEN:
        print("❌ Token non trovato nel .env!")
    else:
        print(f"✅ Token letto dal .env ({len(TOKEN)} caratteri)")
        bot.run(TOKEN)
