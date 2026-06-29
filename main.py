import os
import logging
from fastapi import FastAPI, Request
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
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, timeout=10)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.error(f"sb_get {table}: {e}")
    return []

async def sb_post(table, data):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{SB_URL}/rest/v1/{table}", headers=SB_H, json=data, timeout=10)
            if r.status_code in [200, 201]:
                return r.json()
    except Exception as e:
        logger.error(f"sb_post {table}: {e}")
    return None

async def sb_patch(table, query, data):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.patch(f"{SB_URL}/rest/v1/{table}{query}", headers=SB_H, json=data, timeout=10)
            return r.status_code in [200, 204]
    except Exception as e:
        logger.error(f"sb_patch {table}: {e}")
    return False

async def tg(method, payload):
    if not BOT_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                json=payload, timeout=10
            )
            return r.json()
    except Exception as e:
        logger.error(f"tg {method}: {e}")

async def send(chat_id, text, markup=None):
    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    return await tg("sendMessage", p)

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

class FoyModel(BaseModel):
    tg_id: str
    ism: str
    username: Optional[str] = ""
    balans: int = 0
    rol: str = "haydovchi"

class UstModel(BaseModel):
    nomi: str
    manzil: str
    telefon: str
    lat: float = 41.2995
    lng: float = 69.2401
    narx_dan: int = 50000
    ish_vaqti: str = "08:00-20:00"
    ochiq: bool = True

class SharhModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    yulduz: int
    matn: str

# ── ENDPOINTS ───────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "bot": f"@shamashod_kotbot", "time": str(datetime.now())}

@app.get("/ustaxonalar")
async def get_ustaxonalar(lat: float = 41.2995, lng: float = 69.2401):
    data = await sb_get("ustaxonalar", "?select=*,xizmatlar(nomi,narx)&order=id")
    if not data:
        return []
    result = []
    for u in data:
        xz = u.get("xizmatlar") or []
        result.append({
            **u,
            "xizmatlar_list": [x["nomi"] for x in xz],
            "narxlar": {x["nomi"]: x["narx"] for x in xz},
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
async def add_ustaxona(u: UstModel):
    return await sb_post("ustaxonalar", u.dict())

@app.patch("/ustaxonalar/{uid}")
async def update_ustaxona(uid: int, req: Request):
    data = await req.json()
    await sb_patch("ustaxonalar", f"?id=eq.{uid}", data)
    return {"ok": True}

@app.delete("/ustaxonalar/{uid}")
async def delete_ustaxona(uid: int):
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(f"{SB_URL}/rest/v1/ustaxonalar?id=eq.{uid}", headers=SB_H)
    except:
        pass
    return {"ok": True}

@app.post("/bron")
async def create_bron(b: BronModel):
    result = await sb_post("bronlar", b.dict())
    try:
        ust = await sb_get("ustaxonalar", f"?id=eq.{b.ustaxona_id}&select=nomi")
        nom = ust[0]["nomi"] if ust else "Ustaxona"
        msg = (f"🔔 <b>YANGI BRON!</b>\n\n"
               f"🏪 {nom}\n"
               f"🔧 {b.xizmat}\n"
               f"📅 {b.sana} · {b.vaqt}\n"
               f"🚗 {b.avto or '-'}\n"
               f"💰 {b.narx:,} so'm\n"
               f"👤 {b.foydalanuvchi_id}")
        if ADMIN_ID:
            await send(ADMIN_ID, msg)
    except Exception as e:
        logger.error(f"bron xabar: {e}")
    return result or {"ok": True}

@app.get("/bronlar")
async def get_bronlar():
    return await sb_get("bronlar", "?select=*&order=created_at.desc&limit=50")

@app.get("/bronlar/{foy_id}")
async def get_user_bronlar(foy_id: str):
    return await sb_get("bronlar", f"?foydalanuvchi_id=eq.{foy_id}&order=created_at.desc")

@app.post("/foydalanuvchi")
async def save_foy(f: FoyModel):
    ex = await sb_get("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}&select=id,rol")
    if ex:
        await sb_patch("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}", {"ism": f.ism, "username": f.username})
        return {"ok": True, "rol": ex[0].get("rol", "haydovchi")}
    await sb_post("foydalanuvchilar", f.dict())
    return {"ok": True, "rol": "haydovchi"}

@app.get("/foydalanuvchi_tekshir/{tg_id}")
async def check_foy(tg_id: str):
    data = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=*")
    return data[0] if data else {}

@app.post("/sharh")
async def add_sharh(s: SharhModel):
    result = await sb_post("sharhlar", s.dict())
    sharhlar = await sb_get("sharhlar", f"?ustaxona_id=eq.{s.ustaxona_id}&select=yulduz")
    if sharhlar:
        avg = sum(x["yulduz"] for x in sharhlar) / len(sharhlar)
        await sb_patch("ustaxonalar", f"?id=eq.{s.ustaxona_id}", {
            "reyting": round(avg, 1),
            "sharhlar_soni": len(sharhlar)
        })
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

# ── TELEGRAM BOT WEBHOOK ────────────────────────────────
@app.post("/webhook")
async def webhook(req: Request):
    try:
        update = await req.json()
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return {"ok": True}

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user = msg.get("from", {})
        tg_id = f"tg_{user.get('id', '')}"
        name = (user.get("first_name") or "") + (" " + user.get("last_name", "") if user.get("last_name") else "")

        # Foydalanuvchini saqlash
        ex = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=rol")
        if not ex:
            await sb_post("foydalanuvchilar", {
                "tg_id": tg_id, "ism": name,
                "username": user.get("username", ""),
                "balans": 0, "rol": "haydovchi"
            })

        rol = ex[0].get("rol", "haydovchi") if ex else "haydovchi"

        if text.startswith("/start"):
            kb = {
                "keyboard": [
                    [{"text": "🔧 Ustaxona topish", "web_app": {"url": MINIAPP_URL}}],
                    [{"text": "📋 Bronlarim"}, {"text": "👤 Profilim"}],
                    [{"text": "👥 Do'st taklif"}]
                ],
                "resize_keyboard": True
            }
            await send(chat_id,
                f"👋 Xush kelibsiz, <b>{name}</b>!\n\n"
                f"🚗 <b>GARAGE 24/7</b>\n"
                f"O'zbekistondagi avtomobil ustaxona platformasi\n\n"
                f"📍 Yaqin ustaxonalarni toping\n"
                f"📅 Online bron qiling\n"
                f"⭐ Sharhlar qoldiring",
                kb
            )

        elif text == "📋 Bronlarim":
            bronlar = await sb_get("bronlar", f"?foydalanuvchi_id=eq.{tg_id}&order=created_at.desc&limit=5")
            if bronlar:
                txt = "📋 <b>So'nggi bronlar:</b>\n\n"
                for b in bronlar:
                    txt += f"🔧 {b.get('xizmat')} · 📅 {b.get('sana')} {b.get('vaqt')}\n💰 {b.get('narx',0):,} so'm · {b.get('holat')}\n\n"
            else:
                txt = "📋 Hozircha bronlar yo'q.\n\n🔧 Ustaxona topish tugmasini bosing!"
            await send(chat_id, txt)

        elif text == "👤 Profilim":
            u = await sb_get("foydalanuvchilar", f"?tg_id=eq.{tg_id}&select=*")
            if u:
                u = u[0]
                await send(chat_id,
                    f"👤 <b>Profil</b>\n\n"
                    f"📛 {u.get('ism','-')}\n"
                    f"🔑 Rol: {u.get('rol','haydovchi')}\n"
                    f"💰 Balans: {u.get('balans',0):,} so'm"
                )

        elif text == "👥 Do'st taklif":
            link = f"https://t.me/shamashod_kotbot?start=ref_{tg_id}"
            await send(chat_id,
                f"👥 <b>Do'stlaringizni taklif qiling!</b>\n\n"
                f"Havola:\n<code>{link}</code>"
            )

        elif text == "/stats" and str(user.get("id")) == str(ADMIN_ID):
            s = await statistika()
            await send(chat_id,
                f"📊 <b>STATISTIKA</b>\n\n"
                f"🏪 Ustaxonalar: {s['ustaxonalar']}\n"
                f"📅 Bronlar: {s['bronlar']}\n"
                f"👥 Foydalanuvchilar: {s['foydalanuvchilar']}\n"
                f"💰 Daromad: {s['daromad']:,} so'm"
            )

    except Exception as e:
        logger.error(f"Webhook xato: {e}")
    return {"ok": True}

# Webhook o'rnatish
@app.get("/set_webhook")
async def set_webhook():
    webhook_url = f"{MINIAPP_URL.rstrip('/')}/webhook"
    result = await tg("setWebhook", {"url": webhook_url, "drop_pending_updates": True})
    return {"ok": True, "result": result, "webhook_url": webhook_url}

@app.get("/del_webhook")
async def del_webhook():
    result = await tg("deleteWebhook", {"drop_pending_updates": True})
    return {"ok": True, "result": result}

@app.on_event("startup")
async def startup():
    if BOT_TOKEN:
        webhook_url = f"{MINIAPP_URL.rstrip('/')}/webhook"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                    json={"url": webhook_url, "drop_pending_updates": True},
                    timeout=10
                )
                logger.info(f"Webhook: {r.json()}")
        except Exception as e:
            logger.error(f"Webhook xato: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
