import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import math
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://shamshod-theta.vercel.app")

SB_URL = "https://zpdididueiysnzmrxdco.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZGlkaWR1ZWl5c256bXJ4ZGNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA4NDAxNTAsImV4cCI6MjA5NjQxNjE1MH0.Ev1yt8wf78l8-qhdqPe2JaGItdYXufbsAX0cZ8uC94o"
SB_H = {
    "apikey": SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def dist(lat1, lon1, lat2, lon2):
    R = 6371
    x = math.sin(math.radians(lat2 - lat1) / 2)
    y = math.sin(math.radians(lon2 - lon1) / 2)
    a = x*x + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * y*y
    return round(R * 2 * math.asin(math.sqrt(a)), 1)

async def sb_get(table, query=""):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, timeout=10)
        if r.status_code == 200:
            return r.json()
        return []

async def sb_post(table, data):
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{SB_URL}/rest/v1/{table}", headers=SB_H, json=data, timeout=10)
        if r.status_code in [200, 201]:
            return r.json()
        return None

async def sb_patch(table, query, data):
    async with httpx.AsyncClient() as client:
        r = await client.patch(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, json=data, timeout=10)
        return r.status_code in [200, 204]

async def tg_send(chat_id, text, reply_markup=None):
    if not BOT_TOKEN:
        return
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)

# ── MODELS ──────────────────────────────────────────────
class BronModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    xizmat: str
    avto: Optional[str] = ""
    sana: str
    vaqt: str
    narx: int = 0
    tolov_usul: str = "bepul"
    holat: str = "kutilmoqda"
    izoh: Optional[str] = ""

class FoydalanuvchiModel(BaseModel):
    tg_id: str
    ism: str
    username: Optional[str] = ""
    balans: int = 0
    rol: str = "haydovchi"

class UstaxonaModel(BaseModel):
    nomi: str
    manzil: str
    telefon: str
    lat: float = 41.2995
    lng: float = 69.2401
    narx_dan: int = 50000
    ish_vaqti: str = "08:00-20:00"
    ochiq: bool = True

class BonusModel(BaseModel):
    tg_id: str
    miqdor: int
    izoh: Optional[str] = ""

class SharhModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    yulduz: int
    matn: str

# ── ENDPOINTS ───────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "service": "Garage 24/7", "time": str(datetime.now())}

@app.get("/ustaxonalar")
async def get_ustaxonalar(lat: float = 41.2995, lng: float = 69.2401):
    data = await sb_get("ustaxonalar", "?select=*,xizmatlar(nomi,narx)&order=id")
    if not data:
        return []
    result = []
    for u in data:
        xz = u.get("xizmatlar") or []
        narxlar = {x["nomi"]: x["narx"] for x in xz}
        result.append({
            **u,
            "xizmatlar_list": [x["nomi"] for x in xz],
            "narxlar": narxlar,
            "masofa_km": dist(lat, lng, u.get("lat", 41.2995), u.get("lng", 69.2401))
        })
    result.sort(key=lambda x: x["masofa_km"])
    return result

@app.get("/ustaxonalar/{uid}")
async def get_ustaxona(uid: int):
    data = await sb_get("ustaxonalar", f"?id=eq.{uid}&select=*,xizmatlar(nomi,narx)")
    if data:
        u = data[0]
        xz = u.get("xizmatlar") or []
        u["xizmatlar_list"] = [x["nomi"] for x in xz]
        u["narxlar"] = {x["nomi"]: x["narx"] for x in xz}
        return u
    return {}

@app.post("/ustaxonalar")
async def add_ustaxona(u: UstaxonaModel):
    return await sb_post("ustaxonalar", u.dict())

@app.patch("/ustaxonalar/{uid}")
async def update_ustaxona(uid: int, u: dict):
    await sb_patch("ustaxonalar", f"?id=eq.{uid}", u)
    return {"ok": True}

@app.delete("/ustaxonalar/{uid}")
async def delete_ustaxona(uid: int):
    async with httpx.AsyncClient() as client:
        await client.delete(f"{SB_URL}/rest/v1/ustaxonalar?id=eq.{uid}", headers=SB_H)
    return {"ok": True}

@app.post("/bron")
async def create_bron(b: BronModel):
    result = await sb_post("bronlar", b.dict())
    # Ustaxona egasiga xabar yuborish
    try:
        ust = await sb_get("ustaxonalar", f"?id=eq.{b.ustaxona_id}&select=nomi,telefon")
        if ust:
            msg = f"🔔 <b>YANGI BRON!</b>\n\n🏪 {ust[0]['nomi']}\n🔧 {b.xizmat}\n📅 {b.sana} · {b.vaqt}\n🚗 {b.avto or '-'}\n💰 {b.narx:,} so'm\n📱 {b.foydalanuvchi_id}"
            if ADMIN_ID:
                await tg_send(ADMIN_ID, msg)
    except Exception as e:
        logger.error(f"Bron xabar xato: {e}")
    return result or {"ok": True}

@app.get("/bronlar")
async def get_bronlar():
    return await sb_get("bronlar", "?select=*&order=created_at.desc&limit=50")

@app.get("/bronlar/{foy_id}")
async def get_user_bronlar(foy_id: str):
    return await sb_get("bronlar", f"?foydalanuvchi_id=eq.{foy_id}&order=created_at.desc")

@app.post("/foydalanuvchi")
async def save_foydalanuvchi(f: FoydalanuvchiModel):
    ex = await sb_get("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}&select=id")
    if ex:
        await sb_patch("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}", {"ism": f.ism, "username": f.username})
        return {"ok": True, "action": "updated"}
    result = await sb_post("foydalanuvchilar", f.dict())
    return result or {"ok": True, "action": "created"}

@app.get("/foydalanuvchi_tekshir/{tg_id}")
async def check_foydalanuvchi(tg_id: str):
    data = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=*")
    return data[0] if data else {}

@app.post("/bonus_ber")
async def bonus_ber(b: BonusModel):
    user = await sb_get("foydalanuvchilar", f"?tg_id=eq.{b.tg_id}&select=balans")
    if user:
        new_bal = (user[0].get("balans") or 0) + b.miqdor
        await sb_patch("foydalanuvchilar", f"?tg_id=eq.{b.tg_id}", {"balans": new_bal})
        await sb_post("balans_tarixi", {"foydalanuvchi_id": b.tg_id, "tur": "bonus", "miqdor": b.miqdor, "izoh": b.izoh})
    return {"ok": True}

@app.post("/sharh")
async def add_sharh(s: SharhModel):
    result = await sb_post("sharhlar", s.dict())
    # Reytingni yangilash
    sharhlar = await sb_get("sharhlar", f"?ustaxona_id=eq.{s.ustaxona_id}&select=yulduz")
    if sharhlar:
        avg = sum(x["yulduz"] for x in sharhlar) / len(sharhlar)
        await sb_patch("ustaxonalar", f"?id=eq.{s.ustaxona_id}", {"reyting": round(avg, 1), "sharhlar_soni": len(sharhlar)})
    return result or {"ok": True}

@app.get("/statistika")
async def statistika():
    ust = await sb_get("ustaxonalar", "?select=id")
    bron = await sb_get("bronlar", "?select=narx,holat")
    foy = await sb_get("foydalanuvchilar", "?select=id")
    daromad = sum(b.get("narx", 0) for b in bron)
    return {
        "ustaxonalar": len(ust),
        "bronlar": len(bron),
        "foydalanuvchilar": len(foy),
        "daromad": daromad
    }

# ── TELEGRAM BOT ─────────────────────────────────────────
@app.post(f"/webhook/{BOT_TOKEN}")
async def webhook(update: dict):
    try:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return {"ok": True}

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user = msg.get("from", {})
        tg_id = f"tg_{user.get('id', '')}"

        if text.startswith("/start"):
            # Foydalanuvchini saqlash
            await sb_post("foydalanuvchilar", {
                "tg_id": tg_id,
                "ism": user.get("first_name", "") + " " + (user.get("last_name") or ""),
                "username": user.get("username", ""),
                "balans": 0,
                "rol": "haydovchi"
            })

            keyboard = {
                "keyboard": [
                    [{"text": "🔧 Ustaxona topish", "web_app": {"url": MINIAPP_URL}}],
                    [{"text": "📋 Bronlarim"}, {"text": "💰 Balansim"}],
                    [{"text": "👥 Do'st taklif"}, {"text": "👤 Profilim"}]
                ],
                "resize_keyboard": True
            }
            name = user.get("first_name", "Foydalanuvchi")
            await tg_send(chat_id,
                f"👋 Xush kelibsiz, <b>{name}</b>!\n\n🚗 <b>GARAGE 24/7</b> — O'zbekistondagi eng qulay avtomobil ustaxona platformasi.\n\n📍 Yaqin atrofdagi ustaxonalarni toping\n📅 Online bron qiling\n⭐ Sharhlar qoldiring",
                keyboard
            )

        elif text == "📋 Bronlarim":
            bronlar = await sb_get("bronlar", f"?foydalanuvchi_id=eq.{tg_id}&order=created_at.desc&limit=5")
            if bronlar:
                txt = "📋 <b>So'nggi bronlaringiz:</b>\n\n"
                for b in bronlar:
                    txt += f"🔧 {b.get('xizmat')} — {b.get('sana')} {b.get('vaqt')}\n💰 {b.get('narx', 0):,} so'm · {b.get('holat')}\n\n"
            else:
                txt = "📋 Hozircha bronlar yo'q.\n\n🔧 Ustaxona topish tugmasini bosing!"
            await tg_send(chat_id, txt)

        elif text == "💰 Balansim":
            user_data = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=balans,rol")
            if user_data:
                bal = user_data[0].get("balans", 0)
                rol = user_data[0].get("rol", "haydovchi")
                await tg_send(chat_id, f"💰 <b>Balansingiz:</b> {bal:,} so'm\n👤 Rol: {rol}")
            else:
                await tg_send(chat_id, "💰 Balans: 0 so'm")

        elif text == "👥 Do'st taklif":
            ref_link = f"https://t.me/shamashod_kotbot?start={tg_id}"
            await tg_send(chat_id, f"👥 <b>Do'stlaringizni taklif qiling!</b>\n\nHavola:\n<code>{ref_link}</code>\n\nNusxalab do'stlaringizga yuboring!")

        elif text == "👤 Profilim":
            user_data = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=*")
            if user_data:
                u = user_data[0]
                await tg_send(chat_id,
                    f"👤 <b>Profilingiz</b>\n\n"
                    f"📛 Ism: {u.get('ism', '-')}\n"
                    f"🔑 Rol: {u.get('rol', 'haydovchi')}\n"
                    f"💰 Balans: {u.get('balans', 0):,} so'm\n"
                    f"🆔 ID: {tg_id}"
                )
            else:
                await tg_send(chat_id, "👤 Profil topilmadi. /start bosing.")

        elif text == "/stats" and str(user.get("id")) == str(ADMIN_ID):
            stats = await statistika()
            await tg_send(chat_id,
                f"📊 <b>STATISTIKA</b>\n\n"
                f"🏪 Ustaxonalar: {stats['ustaxonalar']}\n"
                f"📅 Bronlar: {stats['bronlar']}\n"
                f"👥 Foydalanuvchilar: {stats['foydalanuvchilar']}\n"
                f"💰 Daromad: {stats['daromad']:,} so'm"
            )

    except Exception as e:
        logger.error(f"Webhook xato: {e}")

    return {"ok": True}

@app.on_event("startup")
async def startup():
    if BOT_TOKEN:
        try:
            webhook_url = f"{MINIAPP_URL.rstrip('/')}/webhook/{BOT_TOKEN}"
            async with httpx.AsyncClient() as client:
                await client.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    params={"url": webhook_url},
                    timeout=10
                )
            logger.info(f"Webhook set: {webhook_url}")
        except Exception as e:
            logger.error(f"Webhook xato: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
