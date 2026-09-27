import discord
from discord.ext import commands
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
import os

# הגדרת הבוט והרשאות
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# רשימת השחקנים שנרשמו למשחק
current_players = []
game_active = False

@bot.event
async def on_ready():
    print(f'הבוט מחובר ומפעיל את המשחק כעת בתור: {bot.user.name}')

@bot.command(name="להרשם")
async def register(ctx):
    """פקודה לשחקנים להצטרף למשחק"""
    global game_active
    if game_active:
        await ctx.send("המשחק כבר התחיל! לא ניתן להירשם כרגע.")
        return
    
    if ctx.author not in current_players:
        current_players.append(ctx.author)
        await ctx.send(f"🎮 {ctx.author.display_name} נרשם בהצלחה למשחק!")
    else:
        await ctx.send("אתה כבר רשום למשחק!")

@bot.command(name="התחל")
async def start_game(ctx):
    """פקודה למנהל להתחיל את הרולטה וההדחות"""
    global game_active, current_players
    if game_active:
        await ctx.send("יש כבר משחק פעיל ברגע זה.")
        return
    if len(current_players) < 2:
        await ctx.send("צריך לפחות 2 שחקנים כדי להתחיל את המשחק!")
        return

    game_active = True
    await ctx.send("🚀 המשחק מתחיל! מכין את לוח השחקנים...")

    # לולאת המשחק - ממשיכה כל עוד יש יותר משחקן אחד
    while len(current_players) > 1:
        await asyncio.sleep(4)  # הפסקה קלה בין סיבוב לסיבוב
        
        # בחירת שחקן אקראי שיודח (הברק פוגע בו)
        eliminated_player = random.choice(current_players)
        
        # יצירת התמונה המעודכנת של המצב הנוכחי עם אפקט הברק על המודח
        image_bytes = create_game_screen(current_players, eliminated_player)
        
        # שליחת התמונה לערוץ הדיסקורד
        file = discord.File(fp=image_bytes, filename="game_round.png")
        await ctx.send(content=f"⚡ הברק פגע ב-**{eliminated_player.display_name}** והוא מודח!", file=file)
        
        # הסרת השחקן המודח מהרשימה
        current_players.remove(eliminated_player)

    # הכרזה על המנצח האחרון שנשאר
    winner = current_players[0]
    await ctx.send(f"👑 **ברכות! {winner.mention} הוא המנצח האחרון שנשאר במשחק!** 👑")
    
    # איפוס המשחק
    current_players = []
    game_active = False

def create_game_screen(players, struck_player):
    """פונקציה גרפית שמחברת את השחקנים, השמות ואפקט הברק על תמונת הרקע"""
    # טעינת רקע המשחק
    try:
        base_img = Image.open("background.png").convert("RGBA")
    except FileNotFoundError:
        # יצירת רקע זמני אם הקובץ לא קיים
        base_img = Image.new("RGBA", (1000, 500), (34, 139, 34))

    # טעינת אפקט הברק
    try:
        lightning_img = Image.open("lightning.png").convert("RGBA").resize((100, 150))
    except FileNotFoundError:
        lightning_img = None

    draw = ImageDraw.Draw(base_img)
    
    # חישוב מיקומים בשורה (כמו בתמונה של טרופי)
    screen_width, screen_height = base_img.size
    spacing = screen_width // (len(players) + 1)
    
    for i, player in enumerate(players):
        # מיקום ה-X של השחקן הנוכחי בשורה
        x_pos = spacing * (i + 1) - 40
        y_pos = screen_height // 2
        
        # ציור עיגול שמייצג את השחקן (אוואטר)
        avatar_color = (255, 165, 0) if player != struck_player else (255, 0, 0)
        draw.ellipse([x_pos, y_pos, x_pos + 80, y_pos + 80], fill=avatar_color, outline=(255, 255, 255), width=3)
        
        # כתיבת שם השחקן מתחת לדמות
        draw.text((x_pos + 10, y_pos + 90), player.display_name[:10], fill=(255, 255, 255))
        
        # אם זה השחקן שמודח בסיבוב הזה, נדביק עליו את אפקט הברק
        if player == struck_player and lightning_img:
            base_img.paste(lightning_img, (x_pos - 10, y_pos - 100), lightning_img)

    # שמירת התמונה לזיכרון ושליחתה כקובץ לדיסקורד
    img_byte_arr = io.BytesIO()
    base_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# משיכת הטוקן הסודי בצורה מאובטחת
bot.run(os.getenv('DISCORD_TOKEN'))
