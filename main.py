import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from PIL import Image, ImageDraw, ImageOps
import io
import os
from flask import Flask
import threading

# הגדרת הבוט והרשאות
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

current_players = []
game_active = False

# --- שרת אינטרנט זעיר למניעת קריסות באתרי אירוח ---
app = Flask('')
@app.route('/')
def home(): return "The bot is alive!"
def run_web(): app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_web, daemon=True).start()

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"סונכרנו בהצלחה {len(synced)} פקודות סלאש!")
    except Exception as e:
        print(f"שגיאה בסנכרון פקודות: {e}")
    print(f'הבוט מחובר ומפעיל את המשחק כעת בתור: {bot.user.name}')

# --- כפתור ההצטרפות האינטראקטיבי ---
class GameJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # הכפתור לא יפוג לעולם

    @discord.ui.button(label="הצטרף", style=discord.ButtonStyle.green, emoji="🎮")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        global game_active
        if game_active:
            await interaction.response.send_message("המשחק כבר התחיל! לא ניתן להירשם כרגע.", ephemeral=True)
            return
        
        if interaction.user not in current_players:
            current_players.append(interaction.user)
            # הודעה זמנית שרק הלוחץ רואה כדי לא להציף את הערוץ
            await interaction.response.send_message(f"🎮 הצטרפת בהצלחה למשחק! (סך הכל רשומים: {len(current_players)})", ephemeral=True)
            
            # עדכון ההודעה המרכזית עם מספר הרשומים העדכני
            embed = interaction.message.embeds[0]
            embed.set_footer(text=f"👥 שחקנים רשומים כרגע: {len(current_players)}")
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.send_message("אתה כבר רשום למשחק!", ephemeral=True)

# --- פקודת סלאש: הפעלה (יוצרת את ההודעה מהתמונה עם הכפתור) ---
@bot.tree.command(name="הפעלה", description="שלח הודעת הרשמה למשחק עם כפתור לחיצה")
async def setup_game(interaction: discord.Interaction):
    global game_active, current_players
    if game_active:
        await interaction.response.send_message("יש כבר משחק פעיל ברגע זה.", ephemeral=True)
        return
        
    current_players = [] # איפוס השחקנים לתחילת הרשמה חדשה
    
    # יצירת ההודעה המעוצבת (Embed) כמו בתמונה שלך
    embed = discord.Embed(
        title="🎮 הפעלה התחילה",
        description="לחצו על הכפתור כדי להיכנס למשחק ולהצטרף לרשימת המשתתפים.\n\n**בהנחיית:** " + interaction.user.mention,
        color=discord.Color.purple() # הפס הסגול בצד
    )
    embed.set_footer(text="👥 שחקנים רשומים כרגע: 0")
    
    # שליחת ההודעה יחד עם הכפתור הירוק
    view = GameJoinView()
    await interaction.response.send_message(embed=embed, view=view)

# --- פקודת סלאש: התחל ---
@bot.tree.command(name="התחל", description="התחל את משחק ההדחות אחרי שכולם נרשמו")
async def start_game(interaction: discord.Interaction):
    global game_active, current_players
    if game_active:
        await interaction.response.send_message("יש כבר משחק פעיל ברגע זה.", ephemeral=True)
        return
    if len(current_players) < 2:
        await interaction.response.send_message("צריך לפחות 2 שחקנים שנרשמו דרך הכפתור כדי להתחיל!", ephemeral=True)
        return

    game_active = True
    await interaction.response.send_message("🚀 ההרשמה נסגרה! המשחק מתחיל על החוף...")
    ctx_channel = interaction.channel

    while len(current_players) > 1:
        await asyncio.sleep(5)
        eliminated_player = random.choice(current_players)
        image_bytes = await create_game_screen(current_players, eliminated_player)
        
        file = discord.File(fp=image_bytes, filename="game_round.png")
        await ctx_channel.send(content=f"⚡ הברק פגע ב-**{eliminated_player.display_name}** והוא מודח מהאי!", file=file)
        current_players.remove(eliminated_player)

    winner = current_players[0]
    await ctx_channel.send(f"👑 **ברכות! {winner.mention} שרד את האי והוא המנצח הגדול!** 👑")
    
    current_players = []
    game_active = False

# --- פקודת סלאש: SAY ---
@bot.tree.command(name="say", description="גרום לבוט להגיד הודעה כלשהי בערוץ")
@app_commands.describe(text="הטקסט שאתה רוצה שהבוט יגיד")
async def say(interaction: discord.Interaction, text: str):
    await interaction.channel.send(text)
    await interaction.response.send_message("ההודעה נשלחה!", ephemeral=True)

async def create_game_screen(players, struck_player):
    try:
        base_img = Image.open("background.png").convert("RGBA")
    except FileNotFoundError:
        base_img = Image.new("RGBA", (1000, 500), (34, 139, 34))

    screen_width, screen_height = base_img.size
    spacing = screen_width // (len(players) + 1)
    
    for i, player in enumerate(players):
        x_pos = spacing * (i + 1) - 40
        y_pos = int(screen_height * 0.55)
        try:
            avatar_url = player.display_avatar.with_format("png").with_size(128).url
            async with bot.session.get(avatar_url) as resp:
                if resp.status == 200:
                    avatar_data = await resp.read()
                    avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA").resize((80, 80))
                    
                    mask = Image.new("L", (80, 80), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse([0, 0, 80, 80], fill=255)
                    
                    output = ImageOps.fit(avatar_img, (80, 80), centering=(0.5, 0.5))
                    output.putalpha(mask)
                    
                    border_color = (255, 0, 0) if player == struck_player else (255, 255, 255)
                    border_img = Image.new("RGBA", (86, 86), (0,0,0,0))
                    draw_border = ImageDraw.Draw(border_img)
                    draw_border.ellipse([0, 0, 84, 84], outline=border_color, width=4)
                    
                    base_img.paste(border_img, (x_pos - 3, y_pos - 3), border_img)
                    base_img.paste(output, (x_pos, y_pos), output)
        except Exception:
            draw = ImageDraw.Draw(base_img)
            avatar_color = (255, 165, 0) if player != struck_player else (255, 0, 0)
            draw.ellipse([x_pos, y_pos, x_pos + 80, y_pos + 80], fill=avatar_color, outline=(255, 255, 255), width=3)

        draw_text = ImageDraw.Draw(base_img)
        draw_text.text((x_pos + 5, y_pos + 90), player.display_name[:10], fill=(255, 255, 255))

    img_byte_arr = io.BytesIO()
    base_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@bot.event
async def on_connect():
    import aiohttp
    bot.session = aiohttp.ClientSession()

bot.run(os.getenv('DISCORD_TOKEN'))
