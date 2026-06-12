"""
Garage 24/7 — Backend API + Telegram Bot
Bitta faylda ikkalasi ham ishlaydi!
"""
import logging
import asyncio
import threading
import httpx
import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                       WebAppInfo, ReplyKeyboardMarkup)
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                           ConversationHandler, ContextTypes, filters)

# ═══ SOZLAMALAR ═══
import os
BOT_TOKEN    = os.getenv("BOT_TOKEN", "BU_YERGA_TOKENINGIZNI_YOZING")
MINIAPP_URL  = os.getenv("MINIAPP_URL", "https://shamshod-theta.vercel.app")
ADMIN_ID     = int(os.getenv("ADMIN_ID", "123456789"))
SUPABASE_URL = "https://zpdididueiysnzmrxdco.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZGlkaWR1ZWl5c256bXJ4ZGNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA4NDAxNTAsImV4cCI6MjA5NjQxNjE1MH0.Ev1yt8wf78l8-qhdqPe2JaGItdYXufbsAX0cZ8uC94o"
KARTA_RAQAM  = "4073 4200 2335 2382"
KARTA_EGASI  = "Sojida Musaeva"
KIRISH_BONUS   = 30000
REFERRAL_BONUS = 15000

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

logging.basicConfig(level=logging.INFO)

# ════════════════════════════════
# FASTAPI — BACKEND
# ════════════════════════════════
app = FastAPI(title="Garage 24/7 API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def sb(table, query=""):
    return f"{SUPABASE_URL}/rest/v1/{table}{query}"

def masofa(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2-lat1)
    dlng = math.radians(lng2-lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlng/2)**2
    return round(R*2*math.asin(math.sqrt(a)), 1)

class UstaxonaModel(BaseModel):
    nomi: str
    manzil: str
    telefon: str
    lat: float = 41.2995
    lng: float = 69.2401
    narx_dan: int = 50000
    ish_vaqti: str = "08:00-20:00"
    ochiq: bool = True

class XizmatModel(BaseModel):
    ustaxona_id: int
    nomi: str
    narx: int

class BronModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    xizmat: str
    avto: Optional[str] = ""
    sana: str
    vaqt: str
    narx: int = 0
    tolov_usul: str = "naqd"
    izoh: Optional[str] = ""

class FoydalanuvchiModel(BaseModel):
    tg_id: str
    ism: Optional[str] = ""
    username: Optional[str] = ""
    referral_by: Optional[str] = ""

class BonusModel(BaseModel):
    tg_id: str
    miqdor: int
    izoh: str = ""

class SharhModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    yulduz: int
    matn: Optional[str] = ""

@app.get("/")
def root():
    return {"xabar": "Garage 24/7 API ishlayapti ✅"}

@app.get("/ustaxonalar")
async def ustaxonalar_royxati(lat: float = 41.2995, lng: float = 69.2401, radius: float = 30):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("ustaxonalar", "?select=*,xizmatlar(nomi,narx)&order=id"), headers=HEADERS)
        data = r.json()
    natija = []
    for u in data:
        km = masofa(lat, lng, u.get("lat", 41.2995), u.get("lng", 69.2401))
        if km <= radius:
            xizlar = u.get("xizmatlar", [])
            u["xizmatlar_list"] = [x["nomi"] for x in xizlar]
            u["narxlar"] = {x["nomi"]: x["narx"] for x in xizlar}
            u["masofa_km"] = km
            natija.append(u)
    natija.sort(key=lambda x: x["masofa_km"])
    return natija

@app.get("/ustaxonalar/{id}")
async def ustaxona_detail(id: int):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("ustaxonalar", f"?id=eq.{id}&select=*,xizmatlar(nomi,narx)"), headers=HEADERS)
        data = r.json()
    if not data: raise HTTPException(status_code=404, detail="Topilmadi")
    u = data[0]
    xizlar = u.get("xizmatlar", [])
    u["xizmatlar_list"] = [x["nomi"] for x in xizlar]
    u["narxlar"] = {x["nomi"]: x["narx"] for x in xizlar}
    return u

@app.post("/ustaxonalar")
async def ustaxona_qosh(u: UstaxonaModel):
    async with httpx.AsyncClient() as c:
        r = await c.post(sb("ustaxonalar"), headers=HEADERS, json=u.dict())
        return r.json()

@app.patch("/ustaxonalar/{id}")
async def ustaxona_tahrir(id: int, u: UstaxonaModel):
    async with httpx.AsyncClient() as c:
        r = await c.patch(sb("ustaxonalar", f"?id=eq.{id}"), headers=HEADERS, json=u.dict())
        return r.json()

@app.delete("/ustaxonalar/{id}")
async def ustaxona_ochir(id: int):
    async with httpx.AsyncClient() as c:
        await c.delete(sb("xizmatlar", f"?ustaxona_id=eq.{id}"), headers=HEADERS)
        await c.delete(sb("ustaxonalar", f"?id=eq.{id}"), headers=HEADERS)
    return {"xabar": "O'chirildi"}

@app.post("/xizmatlar")
async def xizmat_qosh(x: XizmatModel):
    async with httpx.AsyncClient() as c:
        r = await c.post(sb("xizmatlar"), headers=HEADERS, json=x.dict())
        return r.json()

@app.delete("/xizmatlar/ustaxona/{ustaxona_id}")
async def xizmatlar_ochir(ustaxona_id: int):
    async with httpx.AsyncClient() as c:
        await c.delete(sb("xizmatlar", f"?ustaxona_id=eq.{ustaxona_id}"), headers=HEADERS)
    return {"xabar": "O'chirildi"}

@app.post("/bron")
async def bron_qilish(b: BronModel):
    async with httpx.AsyncClient() as c:
        r = await c.post(sb("bronlar"), headers=HEADERS, json=b.dict())
    return {"xabar": "Bron qabul qilindi ✅", "data": r.json()}

@app.get("/bronlar")
async def barcha_bronlar():
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("bronlar", "?select=*&order=created_at.desc"), headers=HEADERS)
        return r.json()

@app.get("/bronlar/{foydalanuvchi_id}")
async def mening_bronlarim(foydalanuvchi_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("bronlar", f"?foydalanuvchi_id=eq.{foydalanuvchi_id}&order=created_at.desc"), headers=HEADERS)
        return r.json()

@app.post("/foydalanuvchi")
async def foydalanuvchi_saqlash(f: FoydalanuvchiModel):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}"), headers=HEADERS)
        if r.json():
            return r.json()[0]
        data = {"tg_id": f.tg_id, "ism": f.ism, "username": f.username, "balans": KIRISH_BONUS}
        r2 = await c.post(sb("foydalanuvchilar"), headers=HEADERS, json=data)
        # Referral bonus
        if f.referral_by:
            await _bonus_ber(f.referral_by, REFERRAL_BONUS, f"Do'st bonusi: {f.ism}", c)
        return r2.json()

@app.get("/foydalanuvchi_tekshir/{tg_id}")
async def foydalanuvchi_tekshir(tg_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("foydalanuvchilar", f"?tg_id=eq.{tg_id}"), headers=HEADERS)
        data = r.json()
    if not data: return {"mavjud": False}
    return {"mavjud": True, "balans": data[0].get("balans", 0), "data": data[0]}

async def _bonus_ber(tg_id, miqdor, izoh, client):
    r = await client.get(sb("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=balans"), headers=HEADERS)
    data = r.json()
    if not data: return
    yangi = (data[0].get("balans") or 0) + miqdor
    await client.patch(sb("foydalanuvchilar", f"?tg_id=eq.{tg_id}"), headers=HEADERS, json={"balans": yangi})
    await client.post(sb("balans_tarixi"), headers=HEADERS, json={"foydalanuvchi_id": tg_id, "tur": "bonus", "miqdor": miqdor, "izoh": izoh})

@app.post("/bonus_ber")
async def bonus_ber(b: BonusModel):
    async with httpx.AsyncClient() as c:
        await _bonus_ber(b.tg_id, b.miqdor, b.izoh, c)
    return {"xabar": f"Bonus berildi: {b.miqdor}"}

@app.post("/sharh")
async def sharh_qoldirish(s: SharhModel):
    async with httpx.AsyncClient() as c:
        await c.post(sb("sharhlar"), headers=HEADERS, json=s.dict())
        sr = await c.get(sb("sharhlar", f"?ustaxona_id=eq.{s.ustaxona_id}&select=yulduz"), headers=HEADERS)
        sharhlar = sr.json()
        if sharhlar:
            avg = round(sum(x["yulduz"] for x in sharhlar)/len(sharhlar), 1)
            await c.patch(sb("ustaxonalar", f"?id=eq.{s.ustaxona_id}"), headers=HEADERS,
                json={"reyting": avg, "sharhlar_soni": len(sharhlar)})
    return {"xabar": "Sharh qabul qilindi ✅"}

@app.get("/statistika")
async def statistika():
    async with httpx.AsyncClient() as c:
        u = await c.get(sb("ustaxonalar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        b = await c.get(sb("bronlar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        f = await c.get(sb("foydalanuvchilar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        bn = await c.get(sb("bronlar", "?select=narx"), headers=HEADERS)
        ust_cnt = int(u.headers.get("content-range","0/0").split("/")[-1] or 0)
        bron_cnt = int(b.headers.get("content-range","0/0").split("/")[-1] or 0)
        foy_cnt = int(f.headers.get("content-range","0/0").split("/")[-1] or 0)
        daromad = sum(x.get("narx",0) for x in bn.json())
    return {"ustaxonalar": ust_cnt, "bronlar": bron_cnt, "foydalanuvchilar": foy_cnt, "daromad": daromad}

# ════════════════════════════════
# TELEGRAM BOT
# ════════════════════════════════
UST_NOMI, UST_MANZIL, UST_TELEFON, UST_VAQT, UST_XIZMAT, UST_TASDIQ = range(6)

def menu():
    return ReplyKeyboardMarkup([
        ["🔧 Ustaxona topish", "📅 Bronlarim"],
        ["💰 Balansim", "🏪 Ustaxona qo'shish"],
        ["👥 Do'st taklif", "👤 Profilim"],
    ], resize_keyboard=True)

async def tg_get(endpoint):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://localhost:{os.getenv('PORT','8000')}/{endpoint}", timeout=10)
            return r.json()
    except: return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    ref = context.args[0] if context.args else None
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("foydalanuvchilar", f"?tg_id=eq.{uid}"), headers=HEADERS)
        mavjud = r.json()
    if not mavjud:
        async with httpx.AsyncClient() as c:
            await c.post(sb("foydalanuvchilar"), headers=HEADERS,
                json={"tg_id": uid, "ism": user.first_name, "username": user.username or "", "balans": KIRISH_BONUS})
            if ref:
                await _bonus_ber(ref, REFERRAL_BONUS, f"Do'st bonusi: {user.first_name}", c)
        matn = (f"👋 Salom, *{user.first_name}*!\n\n"
                f"🎁 Sizga *{KIRISH_BONUS:,} so'm* bonus berildi!\n"
                f"_(Faqat ilovada bron uchun)_\n\n"
                f"🏪 Ustaxona qo'shsangiz yana *+{REFERRAL_BONUS:,} so'm*!")
    else:
        bal = mavjud[0].get("balans", 0)
        matn = f"👋 Xush kelibsiz, *{user.first_name}*!\n\n💰 Balansingiz: *{bal:,} so'm*"
    kb = [[InlineKeyboardButton("🔧 Garage 24/7 ni ochish", web_app=WebAppInfo(url=MINIAPP_URL))]]
    await update.message.reply_text(matn, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("📌 Menyu:", reply_markup=menu())

async def balans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("foydalanuvchilar", f"?tg_id=eq.{uid}&select=balans"), headers=HEADERS)
        data = r.json()
    bal = data[0].get("balans", 0) if data else 0
    await update.message.reply_text(
        f"💰 *Balansingiz:* {bal:,} so'm\n\n"
        f"Balans to'ldirish:\n💳 *{KARTA_RAQAM}*\n👤 {KARTA_EGASI}\n\n"
        f"📝 Izohga: `G247-{uid}`\n\nO'tkazmadan so'ng chekni yuboring!",
        parse_mode="Markdown")

async def referral_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await update.message.reply_text(
        f"👥 *Do'st taklif qilish*\n\n"
        f"🎁 Siz: *+{REFERRAL_BONUS:,} so'm*\n"
        f"🎁 Do'stingiz: *+{KIRISH_BONUS:,} so'm*\n\n"
        f"🔗 Havolangiz:\n`{link}`",
        parse_mode="Markdown")

async def bronlarim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("bronlar", f"?foydalanuvchi_id=eq.{uid}&order=created_at.desc&limit=5"), headers=HEADERS)
        bronl = r.json()
    if not bronl:
        kb = [[InlineKeyboardButton("🔧 Ustaxona topish", web_app=WebAppInfo(url=MINIAPP_URL))]]
        await update.message.reply_text("📅 Hozircha bronlar yo'q.", reply_markup=InlineKeyboardMarkup(kb))
        return
    matn = "📅 *Bronlaringiz:*\n\n"
    for b in bronl:
        ico = "⏳" if b.get("holat") == "kutilmoqda" else "✅"
        matn += f"{ico} *{b.get('xizmat','—')}*\n📅 {b.get('sana','—')} · ⏰ {b.get('vaqt','—')}\n💰 {b.get('narx',0):,} so'm\n\n"
    await update.message.reply_text(matn, parse_mode="Markdown")

async def profil_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    async with httpx.AsyncClient() as c:
        r = await c.get(sb("foydalanuvchilar", f"?tg_id=eq.{uid}&select=balans"), headers=HEADERS)
        data = r.json()
    bal = data[0].get("balans", 0) if data else 0
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await update.message.reply_text(
        f"👤 *Profil*\n\nIsm: *{update.effective_user.first_name}*\n"
        f"💰 Balans: *{bal:,} so'm*\n\n🔗 Referral:\n`{link}`",
        parse_mode="Markdown")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Ruxsat yo'q!"); return
    async with httpx.AsyncClient() as c:
        u = await c.get(sb("ustaxonalar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        b = await c.get(sb("bronlar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        f = await c.get(sb("foydalanuvchilar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        ust = int(u.headers.get("content-range","0/0").split("/")[-1] or 0)
        bron = int(b.headers.get("content-range","0/0").split("/")[-1] or 0)
        foy = int(f.headers.get("content-range","0/0").split("/")[-1] or 0)
    await update.message.reply_text(
        f"📊 *Statistika*\n\n🏪 Ustaxona: *{ust}*\n👥 Foydalanuvchi: *{foy}*\n📅 Bronlar: *{bron}*",
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
        f"✅ *Tasdiqlang:*\n\n🏪 {d['nomi']}\n📍 {d['manzil']}\n📞 {d['telefon']}\n⏰ {d['ish_vaqti']}\n🔧 {d['xizmatlar']}\n\n🎁 *+{REFERRAL_BONUS:,} so'm* bonus!",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["✅ Tasdiqlash", "❌ Bekor"]], resize_keyboard=True))
    return UST_TASDIQ

async def ust_tasdiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor":
        await update.message.reply_text("Bekor.", reply_markup=menu()); return ConversationHandler.END
    d = context.user_data
    uid = str(update.effective_user.id)
    async with httpx.AsyncClient() as c:
        res = await c.post(sb("ustaxonalar"), headers=HEADERS,
            json={"nomi": d['nomi'], "manzil": d['manzil'], "telefon": d['telefon'], "ish_vaqti": d['ish_vaqti'], "ochiq": True})
        data = res.json()
        ust_id = data[0]['id'] if isinstance(data, list) and data else data.get('id')
        if ust_id:
            for xiz in [x.strip() for x in d['xizmatlar'].split(',')]:
                await c.post(sb("xizmatlar"), headers=HEADERS, json={"ustaxona_id": ust_id, "nomi": xiz, "narx": 50000})
        await _bonus_ber(uid, REFERRAL_BONUS, f"Ustaxona bonusi: {d['nomi']}", c)
    try:
        await context.bot.send_message(ADMIN_ID, f"🏪 Yangi ustaxona!\n{d['nomi']}\n{d['manzil']}\n{d['telefon']}")
    except: pass
    await update.message.reply_text(
        f"✅ *Qo'shildi!*\n\n🎁 *+{REFERRAL_BONUS:,} so'm* balansingizga qo'shildi!",
        parse_mode="Markdown", reply_markup=menu())
    return ConversationHandler.END

async def xabar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    kb = [[InlineKeyboardButton("🔧 Ochish", web_app=WebAppInfo(url=MINIAPP_URL))]]
    if t == "🔧 Ustaxona topish": await update.message.reply_text("Ilovani oching:", reply_markup=InlineKeyboardMarkup(kb))
    elif t == "📅 Bronlarim": await bronlarim_cmd(update, context)
    elif t == "💰 Balansim": await balans_cmd(update, context)
    elif t == "👥 Do'st taklif": await referral_cmd(update, context)
    elif t == "👤 Profilim": await profil_cmd(update, context)

def run_bot():
    """Botni alohida threadda ishga tushirish"""
    if BOT_TOKEN == "BU_YERGA_TOKENINGIZNI_YOZING":
        print("⚠️ BOT_TOKEN qo'yilmagan — bot ishlamaydi")
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(["🏪 Ustaxona qo'shish"]), ust_start)],
        states={
            UST_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_nomi)],
            UST_MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_manzil)],
            UST_TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_telefon)],
            UST_VAQT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_vaqt)],
            UST_XIZMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_xizmat)],
            UST_TASDIQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, ust_tasdiq)],
        },
        fallbacks=[]
    )
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("stats", stats_cmd))
    tg_app.add_handler(conv)
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, xabar))
    print("✅ Bot ishga tushdi!")
    loop.run_until_complete(tg_app.run_polling())

@app.on_event("startup")
async def startup():
    """FastAPI ishga tushganda botni ham ishga tushirish"""
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    print("✅ Garage 24/7 API + Bot ishga tushdi!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
