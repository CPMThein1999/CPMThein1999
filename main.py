#!/usr/bin/env python3
import io
import os
import json
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ⚙️ CONFIG
BOT_TOKEN = "8790019492:AAEiL9dK5NdDUBAMvTZK14Wy9NaOsTkHt1A"
ADMIN_ID = 6060458529
WHITELIST_FILE = "allowed_users.json"
user_photos = {}

# 🔒 WHITELIST
def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, 'r') as f:
                return set(json.load(f))
        except: return set()
    return set()

def save_whitelist(whitelist):
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(list(whitelist), f)

allowed_users = load_whitelist()

# 💧 WATERMARK
def add_watermark(img):
    img = img.convert("RGBA")
    txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt)
    text = "cpm thein"
    font_size = max(12, int(img.width * 0.018))
    try: font = ImageFont.load_default(size=font_size)
    except: font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = img.width - w - 15, img.height - h - 15
    draw.text((x+1, y+1), text, font=font, fill=(0, 0, 0, 100))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 180))
    return Image.alpha_composite(img, txt).convert("RGB")

# ✨ FILTERS
def enhance_auto(img):
    img = ImageEnhance.Brightness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.25)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    return ImageEnhance.Color(img).enhance(1.2)

def enhance_hdr(img):
    img = ImageEnhance.Contrast(img).enhance(1.4)
    img = ImageEnhance.Sharpness(img).enhance(1.8)
    return ImageEnhance.Brightness(img).enhance(1.1)

def upscale_2x(img):
    return ImageEnhance.Sharpness(img.resize((img.width * 2, img.height * 2), Image.LANCZOS)).enhance(1.5)

def filter_cpm_realistic(img):
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Sharpness(img).enhance(2.2)
    return ImageEnhance.Color(img).enhance(1.15).filter(ImageFilter.SMOOTH)

def filter_cpm_night(img):
    img = ImageEnhance.Brightness(img).enhance(0.85)
    img = ImageEnhance.Contrast(img).enhance(1.6)
    return ImageEnhance.Sharpness(img).enhance(2.0)

def filter_cpm_showroom(img):
    img = ImageEnhance.Brightness(img).enhance(1.25)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    return ImageEnhance.Color(img).enhance(1.5).filter(ImageFilter.SHARPEN)

ENHANCE_OPTIONS = {
    "cpm_real": ("🏎️ Realistic", filter_cpm_realistic),
    "cpm_night": ("🌃 Night", filter_cpm_night),
    "cpm_show": ("✨ Showroom", filter_cpm_showroom),
    "auto": ("✨ Auto", enhance_auto),
    "hdr": ("📷 HDR", enhance_hdr),
    "upscale": ("🔍 Upscale 2x", upscale_2x),
    "bw": ("⬛ B&W", lambda i: i.convert("L").convert("RGB")),
}

def image_to_bytes(img, filename="enhanced.png"):
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    bio.name = filename
    return bio

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏎️ Realistic", callback_data="enhance_cpm_real"), InlineKeyboardButton("🌃 Night", callback_data="enhance_cpm_night")],
        [InlineKeyboardButton("✨ Showroom", callback_data="enhance_cpm_show"), InlineKeyboardButton("✨ Auto", callback_data="enhance_auto")],
        [InlineKeyboardButton("📷 HDR", callback_data="enhance_hdr"), InlineKeyboardButton("🔍 Upscale 2x", callback_data="enhance_upscale")],
        [InlineKeyboardButton("⬛ B&W", callback_data="enhance_bw"), InlineKeyboardButton("📸 New Photo", callback_data="new_photo")],
    ])

# 📨 HANDLERS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == ADMIN_ID or uid in allowed_users:
        await update.message.reply_text("📸 <b>CPM Photo Enhancer</b>\n\nဓာတ်ပုံပို့ပြီး Filter ရွေးပါ။\n<i>Watermark: cpm thein</i>", parse_mode="HTML")
    else:
        await update.message.reply_text("⚠️ Access Denied! Admin ခွင့်ပြုချက် လိုပါသည်။")
        kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}")]]
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 New Request\nID: {uid}\nName: {update.effective_user.full_name}", reply_markup=InlineKeyboardMarkup(kb))

async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID: return
    new_id = int(q.data.split("_")[1])
    allowed_users.add(new_id)
    save_whitelist(allowed_users)
    await q.edit_message_text(f"✅ Approved: {new_id}")
    await context.bot.send_message(chat_id=new_id, text="🎉 Admin က ခွင့်ပြုလိုက်ပါပြီ။")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID and uid not in allowed_users: return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    data = await file.download_as_bytearray()
    user_photos[uid] = Image.open(io.BytesIO(data)).convert("RGB")
    await update.message.reply_text("✅ Filter ရွေးပါ 👇", reply_markup=get_keyboard())

async def enhance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if uid not in user_photos: return
    etype = q.data.replace("enhance_", "")
    if etype not in ENHANCE_OPTIONS: return
    label, func = ENHANCE_OPTIONS[etype]
    await q.edit_message_text(f"⏳ {label} လုပ်နေတယ်...")
    try:
        enhanced = add_watermark(func(user_photos[uid].copy()))
        bio = image_to_bytes(enhanced)
        await q.message.reply_document(bio, caption=f"✅ {label} Done!\n📸 <b>cpm thein</b>", parse_mode="HTML")
        await q.message.reply_text("🔄 နောက်ထပ် ရွေးပါ။", reply_markup=get_keyboard())
    except Exception as e:
        await q.message.reply_text(f"❌ Error: {str(e)}")

async def new_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_photos.pop(q.from_user.id, None)
    await q.edit_message_text("📸 ပုံအသစ် ပို့ပါ။")

# 🚀 MAIN
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(approve_callback, pattern="^approve_"))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(new_photo_callback, pattern="^new_photo$"))
    app.add_handler(CallbackQueryHandler(enhance_callback, pattern="^enhance_"))
    print("✅ Bot Running on Railway!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()