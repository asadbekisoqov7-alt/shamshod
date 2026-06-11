"""
Garage 24/7 — Backend API (Supabase bilan)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import math
import os

app = FastAPI(title="Garage 24/7 API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══ SUPABASE CONFIG ═══
SUPABASE_URL = "https://zpdididueiysnzmrxdco.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZGlkaWR1ZWl5c256bXJ4ZGNvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA4NDAxNTAsImV4cCI6MjA5NjQxNjE1MH0.Ev1yt8wf78l8-qhdqPe2JaGItdYXufbsAX0cZ8uC94o"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def sb_url(table, query=""):
    return f"{SUPABASE_URL}/rest/v1/{table}{query}"

# ═══ MODELLAR ═══
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

class SharhModel(BaseModel):
    ustaxona_id: int
    foydalanuvchi_id: str
    yulduz: int
    matn: Optional[str] = ""

# ═══ YORDAMCHI ═══
def masofa(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)), 1)

# ═══ ENDPOINTLAR ═══

@app.get("/")
def root():
    return {"xabar": "Garage 24/7 API v2.0 ishlayapti ✅"}

# ── USTAXONALAR ──
@app.get("/ustaxonalar")
async def ustaxonalar_royxati(lat: float = 41.2995, lng: float = 69.2401, radius: float = 20):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb_url("ustaxonalar", "?select=*,xizmatlar(nomi,narx)&order=id"), headers=HEADERS)
        data = r.json()

    natija = []
    for u in data:
        km = masofa(lat, lng, u.get("lat", 41.2995), u.get("lng", 69.2401))
        if km <= radius:
            # Xizmatlar va narxlar
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
        r = await c.get(sb_url("ustaxonalar", f"?id=eq.{id}&select=*,xizmatlar(nomi,narx)"), headers=HEADERS)
        data = r.json()
    if not data:
        raise HTTPException(status_code=404, detail="Topilmadi")
    u = data[0]
    xizlar = u.get("xizmatlar", [])
    u["xizmatlar_list"] = [x["nomi"] for x in xizlar]
    u["narxlar"] = {x["nomi"]: x["narx"] for x in xizlar}
    return u

@app.post("/ustaxonalar")
async def ustaxona_qosh(u: UstaxonaModel):
    async with httpx.AsyncClient() as c:
        r = await c.post(sb_url("ustaxonalar"), headers=HEADERS, json=u.dict())
        return r.json()

@app.patch("/ustaxonalar/{id}")
async def ustaxona_tahrir(id: int, u: UstaxonaModel):
    async with httpx.AsyncClient() as c:
        r = await c.patch(sb_url("ustaxonalar", f"?id=eq.{id}"), headers=HEADERS, json=u.dict())
        return r.json()

@app.delete("/ustaxonalar/{id}")
async def ustaxona_ochir(id: int):
    async with httpx.AsyncClient() as c:
        await c.delete(sb_url("ustaxonalar", f"?id=eq.{id}"), headers=HEADERS)
    return {"xabar": "O'chirildi"}

# ── XIZMATLAR ──
@app.post("/xizmatlar")
async def xizmat_qosh(x: XizmatModel):
    async with httpx.AsyncClient() as c:
        r = await c.post(sb_url("xizmatlar"), headers=HEADERS, json=x.dict())
        return r.json()

@app.delete("/xizmatlar/{id}")
async def xizmat_ochir(id: int):
    async with httpx.AsyncClient() as c:
        await c.delete(sb_url("xizmatlar", f"?id=eq.{id}"), headers=HEADERS)
    return {"xabar": "O'chirildi"}

# ── BRONLAR ──
@app.post("/bron")
async def bron_qilish(b: BronModel):
    async with httpx.AsyncClient() as c:
        r = await c.post(sb_url("bronlar"), headers=HEADERS, json=b.dict())
        return {"xabar": "Bron qabul qilindi ✅", "data": r.json()}

@app.get("/bronlar")
async def barcha_bronlar():
    async with httpx.AsyncClient() as c:
        r = await c.get(sb_url("bronlar", "?select=*&order=created_at.desc"), headers=HEADERS)
        return r.json()

@app.get("/bronlar/{foydalanuvchi_id}")
async def mening_bronlarim(foydalanuvchi_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb_url("bronlar", f"?foydalanuvchi_id=eq.{foydalanuvchi_id}&order=created_at.desc"), headers=HEADERS)
        return r.json()

@app.patch("/bronlar/{id}/holat")
async def bron_holat(id: int, holat: str):
    async with httpx.AsyncClient() as c:
        r = await c.patch(sb_url("bronlar", f"?id=eq.{id}"), headers=HEADERS, json={"holat": holat})
        return r.json()

# ── FOYDALANUVCHILAR ──
@app.post("/foydalanuvchi")
async def foydalanuvchi_saqlash(f: FoydalanuvchiModel):
    async with httpx.AsyncClient() as c:
        # Mavjudligini tekshir
        r = await c.get(sb_url("foydalanuvchilar", f"?tg_id=eq.{f.tg_id}"), headers=HEADERS)
        if r.json():
            return r.json()[0]
        # Yangi qo'sh
        r2 = await c.post(sb_url("foydalanuvchilar"), headers=HEADERS, json=f.dict())
        return r2.json()

@app.get("/foydalanuvchilar/soni")
async def foydalanuvchilar_soni():
    async with httpx.AsyncClient() as c:
        r = await c.get(sb_url("foydalanuvchilar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        count = r.headers.get("content-range", "0").split("/")[-1]
        return {"soni": int(count) if count.isdigit() else 0}

# ── SHARHLAR ──
@app.post("/sharh")
async def sharh_qoldirish(s: SharhModel):
    if not 1 <= s.yulduz <= 5:
        raise HTTPException(status_code=400, detail="Yulduz 1-5 orasida bo'lishi kerak")
    async with httpx.AsyncClient() as c:
        r = await c.post(sb_url("sharhlar"), headers=HEADERS, json=s.dict())
        # Ustaxona reytingini yangilash
        sr = await c.get(sb_url("sharhlar", f"?ustaxona_id=eq.{s.ustaxona_id}&select=yulduz"), headers=HEADERS)
        sharhlar = sr.json()
        if sharhlar:
            avg = round(sum(x["yulduz"] for x in sharhlar) / len(sharhlar), 1)
            await c.patch(
                sb_url("ustaxonalar", f"?id=eq.{s.ustaxona_id}"),
                headers=HEADERS,
                json={"reyting": avg, "sharhlar_soni": len(sharhlar)}
            )
        return {"xabar": "Sharh qabul qilindi ✅"}

@app.get("/sharhlar/{ustaxona_id}")
async def ustaxona_sharhlari(ustaxona_id: int):
    async with httpx.AsyncClient() as c:
        r = await c.get(sb_url("sharhlar", f"?ustaxona_id=eq.{ustaxona_id}&order=created_at.desc"), headers=HEADERS)
        return r.json()

# ── STATISTIKA ──
@app.get("/statistika")
async def statistika():
    async with httpx.AsyncClient() as c:
        u = await c.get(sb_url("ustaxonalar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        b = await c.get(sb_url("bronlar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        f = await c.get(sb_url("foydalanuvchilar", "?select=count"), headers={**HEADERS, "Prefer": "count=exact"})
        bn = await c.get(sb_url("bronlar", "?select=narx"), headers=HEADERS)

        ust_cnt = int(u.headers.get("content-range","0/0").split("/")[-1] or 0)
        bron_cnt = int(b.headers.get("content-range","0/0").split("/")[-1] or 0)
        foy_cnt = int(f.headers.get("content-range","0/0").split("/")[-1] or 0)
        daromad = sum(x.get("narx",0) for x in bn.json())

    return {
        "ustaxonalar": ust_cnt,
        "bronlar": bron_cnt,
        "foydalanuvchilar": foy_cnt,
        "daromad": daromad
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ── BONUS TIZIMI ──

class BonusModel(BaseModel):
    tg_id: str
    miqdor: int
    izoh: str = ""

@app.post("/bonus_ber")
async def bonus_ber(b: BonusModel):
    async with httpx.AsyncClient() as c:
        # Balansni yangilash
        r = await c.get(f"{SUPABASE_URL}/rest/v1/foydalanuvchilar?tg_id=eq.{b.tg_id}&select=balans", headers=HEADERS)
        data = r.json()
        if not data:
            return {"xabar": "Foydalanuvchi topilmadi"}
        
        yangi_balans = (data[0].get("balans") or 0) + b.miqdor
        await c.patch(
            f"{SUPABASE_URL}/rest/v1/foydalanuvchilar?tg_id=eq.{b.tg_id}",
            headers=HEADERS,
            json={"balans": yangi_balans}
        )
        # Tarix
        await c.post(
            f"{SUPABASE_URL}/rest/v1/balans_tarixi",
            headers=HEADERS,
            json={"foydalanuvchi_id": b.tg_id, "tur": "bonus", "miqdor": b.miqdor, "izoh": b.izoh}
        )
    return {"xabar": f"Bonus berildi: {b.miqdor}", "yangi_balans": yangi_balans}

@app.get("/foydalanuvchi_tekshir/{tg_id}")
async def foydalanuvchi_tekshir(tg_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/foydalanuvchilar?tg_id=eq.{tg_id}", headers=HEADERS)
        data = r.json()
    if not data:
        return {"mavjud": False}
    return {"mavjud": True, "balans": data[0].get("balans", 0), "data": data[0]}

@app.get("/balans/{tg_id}")
async def balans_korish(tg_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/foydalanuvchilar?tg_id=eq.{tg_id}&select=balans", headers=HEADERS)
        data = r.json()
    return {"balans": data[0].get("balans", 0) if data else 0}

@app.post("/balans_toplay/{tg_id}")
async def balans_toplay(tg_id: str, miqdor: int):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/foydalanuvchilar?tg_id=eq.{tg_id}&select=balans", headers=HEADERS)
        data = r.json()
        if not data:
            raise HTTPException(status_code=404, detail="Topilmadi")
        yangi = (data[0].get("balans") or 0) + miqdor
        await c.patch(
            f"{SUPABASE_URL}/rest/v1/foydalanuvchilar?tg_id=eq.{tg_id}",
            headers=HEADERS, json={"balans": yangi}
        )
        await c.post(f"{SUPABASE_URL}/rest/v1/balans_tarixi", headers=HEADERS,
            json={"foydalanuvchi_id": tg_id, "tur": "topup", "miqdor": miqdor, "izoh": "Admin to'ldirdi"})
    return {"xabar": "Balans to'ldirildi", "yangi_balans": yangi}

@app.get("/bron_narxlar")
async def bron_narxlar():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SUPABASE_URL}/rest/v1/bron_narxlar?select=*", headers=HEADERS)
        return r.json()
