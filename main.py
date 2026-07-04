from flask import Flask, request
import io, os, json
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import asyncio

# ================= CONFIG =================
BOT_TOKEN = "8790019492:AAEiL9dK5NdDUBAMvTZK14Wy9NaOsTkHt1A"
ADMIN_ID = 6060458529
USERNAME = "CpmTA"
WEBHOOK_URL = f"https://{USERNAME}.pythonanywhere.com/{BOT_TOKEN}"
WHITELIST_FILE = f"/home/{USERNAME}/mysite/allowed_users.json"

flask_app = Flask(__name__)
ptb_app = Application.builder().token(BOT_TOKEN).build()
user_photos = {}

# ================= WHITELIST =================
def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE) as f:
            return set(json.load(f))
    return set()

def save_whitelist(users):
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(list(users), f)

allowed_users = load_whitelist()

# ================= WATERMARK (အသေးလေး) =================
def add_watermark(img):
    img = img.convert("RGBA")
    txt = Image.new('RGBA', img.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt)
    text = "cpm thein"
    font_size = max(11, int(img.width * 0.016))
    font = ImageFont.load_default(size=font_size)
    bbox = draw.textbbox((0,0), text, font=font)
    w = bbox[2] - bbox[0]
    x = img.width - w - 12
    y = img.height - 18
    draw.text((x+1,y+1), text, font=font, fill=(0,0,0,120))
    draw.text((x,y), text, font=font, fill=(255,255,255,200))
    return Image.alpha_composite(img, txt).convert("RGB")

# ================= FILTERS =================
def enhance_auto(img): 
    return ImageEnhance.Sharpness(ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(1.15)).enhance(1.25)).enhance(1.5)

def filter_cpm_realistic(img):
    return ImageEnhance.Sharpness(ImageEnhance.Contrast(img).enhance(1.35)).enhance(2.0)

def filter_cpm_night(img):
    return ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(0.9)).enhance(1.7)

def filter_cpm_showroom(img):
    return ImageEnhance.Sharpness(ImageEnhance.Color(ImageEnhance.Brightness(img).enhance(1.2)).enhance(1.4)).enhance(2.5)

ENHANCE_OPTIONS = {
    "real": ("🏎️ Realistic", filter_cpm_realistic),
    "night": ("🌃 Night", filter_cpm_night),
    "show": ("✨ Showroom", filter_cpm_showroom),
    "auto": ("✨ Auto", enhance_auto),
}

def image_to_bytes(img):
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    bio.name = "enhanced.png"
    return bio

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏎️ Realistic", callback_data="real"),
         InlineKeyboardButton("🌃 Night", callback_data="night")],
        [InlineKeyboardButton("✨ Showroom", callback_data="show"),
         InlineKeyboardButton("✨ Auto", callback_data="auto")],
        [InlineKeyboardButton("📸 New Photo", callback_data="new")]
    ])

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == ADMIN_ID or uid in allowed_users:
        await update.message.reply_text("✅ Bot is ready.\nSend a photo and choose filter.", reply_markup=get_keyboard())
    else:
        kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"app_{uid}")]]
        await context.bot.send_message(ADMIN_ID, f"New user: {uid}", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("⛔ Access Denied. Waiting for admin approval.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID: return
    uid = int(q.data.split("_")[1])
    allowed_users.add(uid)
    save_whitelist(allowed_users)
    await q.edit_message_text(f"✅ Approved {uid}")
    await context.bot.send_message(uid, "🎉 Admin approved you. You can use the bot now.")

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in allowed_users and uid != ADMIN_ID: return
    file = await context.bot.get_file(update.message.photo[-1].file_id)
    img = Image.open(io.BytesIO(await file.download_as_bytearray())).convert("RGB")
    user_photos[uid] = img
    await update.message.reply_text("Choose filter:", reply_markup=get_keyboard())

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in user_photos: return
    if q.data == "new":
        user_photos.pop(uid, None)
        await q.edit_message_text("Send new photo.")
        return
    label, func = ENHANCE_OPTIONS[q.data]
    await q.edit_message_text(f"Processing {label}...")
    enhanced = add_watermark(func(user_photos[uid].copy()))
    await q.message.reply_document(image_to_bytes(enhanced), caption=f"✅ {label}\n📸 cpm thein")

# ================= WEBHOOK =================
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(CallbackQueryHandler(approve, pattern="^app_"))
ptb_app.add_handler(MessageHandler(filters.PHOTO, photo))
ptb_app.add_handler(CallbackQueryHandler(callback))

@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    asyncio.run(ptb_app.process_update(update))
    return "OK"

@flask_app.route("/")
def home():
    return "Bot is running on PythonAnywhere"

if __name__ == "__main__":
    import asyncio
    asyncio.run(ptb_app.bot.set_webhook(WEBHOOK_URL))
    print("Webhook set successfully!")
    flask_app.run()