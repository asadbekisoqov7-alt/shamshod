"""
Garage 24/7 — Telegram Bot
Bonus tizimi + Ustaxona qo'shish + To'lov
"""
import logging
import httpx
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                       WebAppInfo, ReplyKeyboardMarkup, KeyboardButton)
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                           ConversationHandler, ContextTypes, filters)

BOT_TOKEN   = "8644472363:AAE27q6YOLN4DQcNRJ65nx7VUgEm-8H5VV8"
MINIAPP_URL = "https://shamshod-theta.vercel.app"
API_URL     = "https://shamshod-production.up.railway.app"
ADMIN_ID    =  8375903870
KARTA_RAQAM = "4073 4200 2335 2382"
KARTA_EGASI = "Sojida Musaeva"
KIRISH_BONUS   = 30000
REFERRAL_BONUS = 15000
UST_NOMI, UST_MANZIL, UST_TELEFON, UST_VAQT, UST_XIZMAT, UST_TASDIQLASH = range(6)
logging.basicConfig(level=logging.INFO)

async def api_get(ep):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{API_URL}/{ep}", timeout=10)
            return r.json()
    except: return None

async def api_post(ep, data):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{API_URL}/{ep}", json=data, timeout=10)
            return r.json()
    except: return None

def menu():
    return ReplyKeyboardMarkup([
        ["🔧 Ustaxona topish", "📅 Bronlarim"],
        ["💰 Balansim", "🏪 Ustaxona qo'shish"],
        ["👥 Do'st taklif", "👤 Profilim"],
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    mavjud = await api_get(f"foydalanuvchi_tekshir/{uid}")
    if not mavjud or not mavjud.get("mavjud"):
        ref = context.args[0] if context.args else None
        await api_post("foydalanuvchi", {"tg_id": uid, "ism": user.first_name, "username": user.username or "", "referral_by": ref})
        if ref:
            await api_post("bonus_ber", {"tg_id": ref, "miqdor": REFERRAL_BONUS, "izoh": f"Do'st bonusi: {user.first_name}"})
        matn = f"👋 Salom, *{user.first_name}*!\n\n🎁 Sizga *{KIRISH_BONUS:,} so'm* bonus berildi!\n_Faqat ilovada bron uchun_\n\n🏪 Ustaxona qo'shsangiz yana *+{REFERRAL_BONUS:,} so'm*!"
    else:
        bal = mavjud.get("balans", 0)
        matn = f"👋 Xush kelibsiz, *{user.first_name}*!\n\n💰 Balansingiz: *{bal:,} so'm*"
    kb = [[InlineKeyboardButton("🔧 Garage 24/7 ni ochish", web_app=WebAppInfo(url=MINIAPP_URL))]]
    await update.message.reply_text(matn, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("📌 Menyu:", reply_markup=menu())

async def balans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    ma = await api_get(f"foydalanuvchi_tekshir/{uid}")
    bal = ma.get("balans", 0) if ma else 0
    await update.message.reply_text(
        f"💰 *Balansingiz:* {bal:,} so'm\n\nBalans to'ldirish uchun:\n💳 *{KARTA_RAQAM}*\n👤 {KARTA_EGASI}\n\n📝 Izohga: `G247-{update.effective_user.id}`\n\nO'tkazmadan so'ng chekni yuboring!",
        parse_mode="Markdown")

async def referral_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await update.message.reply_text(
        f"👥 *Do'st taklif qilish*\n\nHavola orqali kirsa:\n🎁 Siz: *+{REFERRAL_BONUS:,} so'm*\n🎁 Do'stingiz: *+{KIRISH_BONUS:,} so'm*\n\n🔗 Havolangiz:\n`{link}`",
        parse_mode="Markdown")

async def bronlarim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    bronl = await api_get(f"bronlar/{uid}")
    if not bronl or not len(bronl):
        kb = [[InlineKeyboardButton("🔧 Ustaxona topish", web_app=WebAppInfo(url=MINIAPP_URL))]]
        await update.message.reply_text("📅 Hozircha bronlar yo'q.", reply_markup=InlineKeyboardMarkup(kb))
        return
    matn = "📅 *Bronlaringiz:*\n\n"
    for b in bronl[:5]:
        ico = "⏳" if b.get("holat") == "kutilmoqda" else "✅"
        matn += f"{ico} *{b.get('xizmat','—')}*\n📅 {b.get('sana','—')} · ⏰ {b.get('vaqt','—')}\n💰 {b.get('narx',0):,} so'm\n\n"
    await update.message.reply_text(matn, parse_mode="Markdown")

async def profil_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    ma = await api_get(f"foydalanuvchi_tekshir/{uid}")
    bal = ma.get("balans", 0) if ma else 0
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await update.message.reply_text(
        f"👤 *Profil*\n\nIsm: *{update.effective_user.first_name}*\n💰 Balans: *{bal:,} so'm*\n\n🔗 Referral:\n`{link}`",
        parse_mode="Markdown")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Ruxsat yo'q!"); return
    s = await api_get("statistika")
    if not s: await update.message.reply_text("❌ Xato"); return
    await update.message.reply_text(
        f"📊 *Statistika*\n\n🏪 Ustaxona: *{s.get('ustaxonalar',0)}*\n👥 Foydalanuvchi: *{s.get('foydalanuvchilar',0)}*\n📅 Bronlar: *{s.get('bronlar',0)}*\n💰 Daromad: *{s.get('daromad',0):,} so'm*",
        parse_mode="Markdown")

# Ustaxona qo'shish
async def ust_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🏪 *Ustaxona qo'shish*\n\n1️⃣ Ustaxona nomini yozing:", parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["❌ Bekor"]], resize_keyboard=True))
    return UST_NOMI

async def ust_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor": await update.message.reply_text("Bekor.", reply_markup=menu()); return ConversationHandler.END
    context.user_data['nomi'] = update.message.text
    await update.message.reply_text("2️⃣ Manzilni yozing:\n_(Masalan: Yunusobod, 5-mavze)_", parse_mode="Markdown")
    return UST_MANZIL

async def ust_manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['manzil'] = update.message.text
    await update.message.reply_text("3️⃣ Telefon raqamini yozing:")
    return UST_TELEFON

async def ust_telefon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['telefon'] = update.message.text
    await update.message.reply_text("4️⃣ Ish vaqti:\n_(Masalan: 08:00-20:00)_", parse_mode="Markdown")
    return UST_VAQT

async def ust_vaqt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ish_vaqti'] = update.message.text
    await update.message.reply_text("5️⃣ Xizmatlarni yozing _(vergul bilan)_:\n_(Masalan: Moy almashtirish, Diagnostika)_", parse_mode="Markdown")
    return UST_XIZMAT

async def ust_xizmat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['xizmatlar'] = update.message.text
    d = context.user_data
    await update.message.reply_text(
        f"✅ *Tasdiqlang:*\n\n🏪 {d['nomi']}\n📍 {d['manzil']}\n📞 {d['telefon']}\n⏰ {d['ish_vaqti']}\n🔧 {d['xizmatlar']}\n\n🎁 *+{REFERRAL_BONUS:,} so'm* bonus olasiz!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["✅ Tasdiqlash", "❌ Bekor"]], resize_keyboard=True))
    return UST_TASDIQLASH

async def ust_tasdiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor": await update.message.reply_text("Bekor.", reply_markup=menu()); return ConversationHandler.END
    d = context.user_data
    uid = str(update.effective_user.id)
    res = await api_post("ustaxonalar", {"nomi": d['nomi'], "manzil": d['manzil'], "telefon": d['telefon'], "ish_vaqti": d['ish_vaqti'], "ochiq": True})
    if res:
        ust_id = res[0]['id'] if isinstance(res, list) else res.get('id')
        if ust_id:
            for xiz in [x.strip() for x in d['xizmatlar'].split(',')]:
                await api_post("xizmatlar", {"ustaxona_id": ust_id, "nomi": xiz, "narx": 50000})
    await api_post("bonus_ber", {"tg_id": uid, "miqdor": REFERRAL_BONUS, "izoh": f"Ustaxona bonusi: {d['nomi']}"})
    try:
        await context.bot.send_message(ADMIN_ID, f"🏪 Yangi ustaxona!\n{d['nomi']}\n{d['manzil']}\n{d['telefon']}")
    except: pass
    await update.message.reply_text(f"✅ *Qo'shildi!*\n\n🎁 *+{REFERRAL_BONUS:,} so'm* balansingizga qo'shildi!", parse_mode="Markdown", reply_markup=menu())
    return ConversationHandler.END

async def xabar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    kb = [[InlineKeyboardButton("🔧 Ochish", web_app=WebAppInfo(url=MINIAPP_URL))]]
    if t == "🔧 Ustaxona topish": await update.message.reply_text("Ilovani oching:", reply_markup=InlineKeyboardMarkup(kb))
    elif t == "📅 Bronlarim": await bronlarim_cmd(update, context)
    elif t == "💰 Balansim": await balans_cmd(update, context)
    elif t == "👥 Do'st taklif": await referral_cmd(update, context)
    elif t == "👤 Profilim": await profil_cmd(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🏪 Ustaxona qo'shish"]), ust_start), CommandHandler("ustaxona", ust_start)],
        states={
            UST_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_nomi)],
            UST_MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_manzil)],
            UST_TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_telefon)],
            UST_VAQT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_vaqt)],
            UST_XIZMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_xizmat)],
            UST_TASDIQLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_tasdiq)],
        },
        fallbacks=[CommandHandler("bekor", lambda u,c: ConversationHandler.END)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("topup", lambda u,c: balans_cmd(u,c)))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, xabar))
    print("✅ Garage 24/7 Bot ishga tushdi!")
    app.run_polling()
