import os, json, time, base64, io, hashlib, re
import concurrent.futures
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import bcrypt
from dotenv import load_dotenv
from groq import Groq
from PIL import Image
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from database import Base, engine, SessionLocal
from models import User
from ceda import MarketDataError, crop_names, get_history, geography
from weather import router as weather_router

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Override GROQ_MODEL in .env if you want to use a different available vision model.
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
CACHE = {}

SECRET_KEY = "change-this-to-a-long-random-string"
ALGORITHM = "HS256"

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AgroVision AI")
app.include_router(weather_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def prepare_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def ask_ai(image_bytes, prompt, tries=3):
    b64 = base64.b64encode(image_bytes).decode()
    last = None
    for attempt in range(tries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": "data:image/jpeg;base64," + b64},
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=4000,
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last = e
            msg = str(e).lower()
            if "per day" in msg:
                break
            if "503" in msg or "429" in msg or "overloaded" in msg or "rate limit" in msg:
                time.sleep(3 * (attempt + 1))
                continue
            raise
    raise last


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Please log in first")
    try:
        data = jwt.decode(
            authorization.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM]
        )
    except Exception:
        raise HTTPException(401, "Session expired. Please log in again")
    user = db.query(User).filter(User.email == data["sub"]).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user


class SignupData(BaseModel):
    name: str
    email: str
    password: str


class LoginData(BaseModel):
    email: str
    password: str


@app.get("/")
def root():
    return {"status": "running"}


@app.post("/signup")
def signup(data: SignupData, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(400, "Email already registered")

    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    db.add(User(name=data.name, email=email, **{"pass" + "word": hashed}))
    db.commit()
    return {"message": "Account created"}


@app.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user or not bcrypt.checkpw(
        data.password.encode(), user.password.encode()
    ):
        raise HTTPException(401, "Invalid email or password")
    token = jwt.encode(
        {"sub": user.email, "exp": datetime.utcnow() + timedelta(hours=12)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"token": token, "name": user.name}


DATA_GOV_IN_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_IN_URL = f"https://api.data.gov.in/resource/{DATA_GOV_IN_RESOURCE_ID}"
COMMODITY_ALIASES = {
    "rice": ["Rice", "Paddy"],
    "paddy": ["Paddy", "Rice"],
    "sugarcane": ["Sugarcane", "Sugar Cane"],
    "chilli": ["Chilli", "Green Chilli", "Dry Chilli"],
}


def _parse_market_price(value):
    try:
        price = float(str(value).replace(",", "").strip())
        return price if price >= 0 else None
    except (TypeError, ValueError):
        return None


def _date_sort_key(value):
    for date_format in ("%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format)
        except (TypeError, ValueError):
            continue
    return datetime.min


def _fetch_data_gov_records(crop_name, state, district, market):
    api_key = os.getenv("DATA_GOV_IN_API_KEY") or os.getenv("DATA_GOV_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "market_api_not_configured",
                "message": "Live mandi prices are not configured. Add DATA_GOV_IN_API_KEY to backend/.env and restart the backend.",
            },
        )

    commodities = COMMODITY_ALIASES.get(crop_name.casefold(), [crop_name])
    for commodity in commodities:
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": "1000",
            "sort[arrival_date]": "desc",
            "filters[commodity]": commodity,
        }
        for field, value in (("state", state), ("district", district), ("market", market)):
            if value:
                params[f"filters[{field}]"] = value

        request = Request(
            f"{DATA_GOV_IN_URL}?{urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": "AgroVision/1.0"},
        )
        try:
            with urlopen(request, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise HTTPException(
                    status_code=502,
                    detail="The market-data provider rejected the API key. Check DATA_GOV_IN_API_KEY.",
                ) from exc
            raise HTTPException(
                status_code=502,
                detail=f"The market-data provider returned HTTP {exc.code}. Try again later.",
            ) from exc
        except URLError as exc:
            raise HTTPException(
                status_code=502,
                detail="The market-data provider could not be reached. Check the backend internet connection and retry.",
            ) from exc
        except TimeoutError as exc:
            raise HTTPException(
                status_code=502,
                detail="The market-data provider could not be reached. Check the backend internet connection and retry.",
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=502,
                detail="The market-data provider returned an invalid response.",
            ) from exc

        records = payload.get("records", [])
        if not isinstance(records, list):
            raise HTTPException(
                status_code=502,
                detail="The market-data provider response did not contain a valid records list.",
            )
        if records:
            return commodity, records

    return commodities[-1], []


@app.get("/market-prices")
def market_prices(
    crop: str,
    state: str = "",
    district: str = "",
    market: str = "",
):
    crop_name = crop.strip()
    if not crop_name:
        raise HTTPException(status_code=422, detail="Crop name is required.")

    commodity, records = _fetch_data_gov_records(
        crop_name,
        state.strip(),
        district.strip(),
        market.strip(),
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No mandi records were found for {crop_name} with the selected location filters.",
        )

    daily_prices = {}
    latest_records = []
    for record in records:
        modal = _parse_market_price(record.get("modal_price"))
        minimum = _parse_market_price(record.get("min_price"))
        maximum = _parse_market_price(record.get("max_price"))
        arrival_date = str(record.get("arrival_date") or "").strip()
        if modal is None or not arrival_date:
            continue

        daily_prices.setdefault(arrival_date, []).append(modal)
        if minimum is not None:
            record["_parsed_min_price"] = minimum
        if maximum is not None:
            record["_parsed_max_price"] = maximum

    if not daily_prices:
        raise HTTPException(
            status_code=502,
            detail="The provider returned mandi rows without usable modal prices and arrival dates.",
        )

    dates = sorted(daily_prices, key=_date_sort_key, reverse=True)
    latest_date = dates[0]
    latest_records = [
        row for row in records
        if str(row.get("arrival_date") or "").strip() == latest_date
        and _parse_market_price(row.get("modal_price")) is not None
    ]
    latest_modal_prices = daily_prices[latest_date]
    latest_min_prices = [row["_parsed_min_price"] for row in latest_records if "_parsed_min_price" in row]
    latest_max_prices = [row["_parsed_max_price"] for row in latest_records if "_parsed_max_price" in row]
    market_names = sorted({
        str(row.get("market") or "").strip()
        for row in latest_records
        if str(row.get("market") or "").strip()
    })
    history = [
        {
            "date": date,
            "price": round(sum(daily_prices[date]) / len(daily_prices[date]), 2),
            "market_count": len(daily_prices[date]),
        }
        for date in sorted(dates, key=_date_sort_key)[-30:]
    ]
    previous_date = dates[1] if len(dates) > 1 else None
    previous_price = (
        round(sum(daily_prices[previous_date]) / len(daily_prices[previous_date]), 2)
        if previous_date else None
    )

    return {
        "crop": crop_name,
        "commodity": commodity,
        "unit": "₹ / quintal",
        "current": round(sum(latest_modal_prices) / len(latest_modal_prices), 2),
        "previous": previous_price,
        "min": round(sum(latest_min_prices) / len(latest_min_prices), 2) if latest_min_prices else None,
        "max": round(sum(latest_max_prices) / len(latest_max_prices), 2) if latest_max_prices else None,
        "as_of": latest_date,
        "history": history,
        "market_count": len(market_names),
        "markets": market_names[:8],
        "location": {
            "state": state.strip() or None,
            "district": district.strip() or None,
            "market": market.strip() or None,
        },
        "source": "data.gov.in",
        "source_url": "https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi",
        "record_count": len(records),
    }


@app.post("/analyze-land")
async def analyze_land(
    file: UploadFile = File(...),
    temperature: float = Form(...),
    rainfall: float = Form(...),
    humidity: float = Form(60),
    acres: float = Form(1),
    month: str = Form(""),
    location: str = Form(""),
    user: User = Depends(current_user),
):
    raw = await file.read()
    try:
        image_bytes = prepare_image(raw)
    except Exception:
        raise HTTPException(400, "Could not read that image. Try a JPG or PNG photo.")

    key = hashlib.md5(
        image_bytes + f"{temperature}|{rainfall}|{humidity}|{acres}|{month}|{location}".encode()
    ).hexdigest()
    if key in CACHE:
        return CACHE[key]

    prompt = f"""You are an agricultural advisor helping a farmer in India.
Look at this land photo and use the field data: temperature={temperature}C, humidity={humidity}%, rainfall={rainfall}mm over 30 days, acreage={acres}, month={month or 'not specified'}, location={location or 'not specified'}.

Reply with ONLY valid JSON in exactly this format:
{{
  "soil_type": "sandy / loamy / clay / black / red",
  "season": "kharif / rabi / zaid / all-season",
  "soil_condition": "a short summary of soil and moisture condition",
  "recommended_crops": [
    {{"crop": "crop name", "suitability": "high / medium / low", "reason": "brief reason", "estimated_cost_per_acre_inr": 15000, "water_need": "low / medium / high", "duration_days": 120}}
  ],
  "best_low_cost_pick": {{"crop": "crop name", "why": "reason it is the best low-cost option"}},
  "organic_plan": {{
    "fertilizers": ["organic fertilizer suggestions"],
    "pest_control": ["pest control actions"],
    "soil_improvement": ["soil improvement actions"]
  }},
  "chemical_reduction": ["how to reduce chemical dependency"],
  "cost_saving_tips": ["money-saving suggestions"],
  "avoid_crops": ["crops not suitable for this land and season"]
}}
Return realistic values for Indian farming conditions and keep the JSON valid."""

    try:
        text = ask_ai(image_bytes, prompt)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        start = text.find("{")
        end = text.rfind("}") + 1
        result = json.loads(text[start:end])
        CACHE[key] = result
        return result
    except Exception as e:
        raise HTTPException(500, f"AI analysis failed: {e}")


@app.post("/detect-disease")
async def detect_disease(file: UploadFile = File(...), crop: str = Form("")):
    raw = await file.read()
    try:
        image_bytes = prepare_image(raw)
    except Exception:
        raise HTTPException(400, "Could not read that image. Try a JPG or PNG photo.")

    key = hashlib.md5(image_bytes + crop.encode()).hexdigest()
    if key in CACHE:
        return CACHE[key]

    prompt = f"""You are a plant pathologist advising a small farmer in India.
Look at this photo of a crop leaf. The farmer says the crop is: {crop or "not specified"}.

Reply with ONLY valid JSON in exactly this format:
{{
  "is_plant_leaf": true,
  "crop": "crop name you identify",
  "disease": "disease name, or Healthy",
  "confidence": "high / medium / low",
  "severity": "none / mild / moderate / severe",
  "cause": "fungus / bacteria / virus / pest / nutrient deficiency / other",
  "symptoms": ["visible symptoms of this disease"],
  "effect_on_crop": "how it harms the plant and the harvest",
  "yield_loss_estimate": "rough percentage range if untreated",
  "precautions": ["immediate steps to stop it spreading"],
  "prevention": ["how to prevent it in future seasons"],
  "organic_treatment": ["organic options such as neem oil, Trichoderma, cow urine spray, buttermilk spray"],
  "chemical_treatment": [
    {{"name": "pesticide or fungicide name", "dose": "typical label dose", "note": "when and how to apply"}}
  ],
  "when_to_see_expert": "when the farmer should contact an agriculture officer"
}}
If the image is not a plant leaf, set is_plant_leaf to false and explain in effect_on_crop. If the leaf looks healthy, set disease to Healthy and keep the treatment lists short. Prefer organic options first. If you are unsure, set confidence to low."""

    try:
        text = ask_ai(image_bytes, prompt)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        start = text.find("{")
        end = text.rfind("}") + 1
        result = json.loads(text[start:end])
        CACHE[key] = result
        return result
    except Exception as e:
        raise HTTPException(500, f"AI analysis failed: {e}")


@app.post("/analyze-harvest")
async def analyze_harvest(
    file: UploadFile = File(...),
    crop: str = Form(""),
    temperature: float = Form(...),
    humidity: float = Form(60),
    forecast: str = Form(""),
    location: str = Form(""),
):
    raw = await file.read()
    try:
        image_bytes = prepare_image(raw)
    except Exception:
        raise HTTPException(400, "Could not read that image. Try a JPG or PNG photo.")

    key = hashlib.md5(
        image_bytes + f"{crop}{temperature}{humidity}{forecast}{location}".encode()
    ).hexdigest()
    if key in CACHE:
        return CACHE[key]

    prompt = f"""You are an agricultural expert advising a small farmer in India on harvesting.
Look at this photo of a crop in the field or just harvested. The farmer says the crop is: {crop or "not specified"}.
Location: {location}
Weather now: temperature {temperature} C, humidity {humidity}%.
7-day forecast: {forecast}

Decide if the crop is ready to harvest from what is visible (colour, size, ripeness, dryness), then choose the best harvest days using the forecast. Avoid heavy rain days.

Reply with ONLY valid JSON in exactly this format:
{{
  "is_crop": true,
  "crop": "crop name you identify",
  "confidence": "high / medium / low",
  "maturity_stage": "what stage the crop is at",
  "ready_to_harvest": "yes / almost / no",
  "days_to_harvest": "estimated days left, or 0 if ready",
  "quality_grade": "A / B / C",
  "grade_reasons": ["visible reasons for this grade"],
  "best_harvest_window": "which dates from the forecast are best and why",
  "weather_risk": "any rain, heat or humidity risk and what to do",
  "harvest_tips": ["practical tips for harvesting this crop"],
  "post_harvest_care": ["drying, cleaning, packing and storage steps"]
}}
If the image is not a crop, set is_crop to false and explain in weather_risk. If you are unsure, set confidence to low."""

    try:
        text = ask_ai(image_bytes, prompt)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        start = text.find("{")
        end = text.rfind("}") + 1
        result = json.loads(text[start:end])
        CACHE[key] = result
        return result
    except Exception as e:
        raise HTTPException(500, f"AI analysis failed: {e}")

# ============================================================
# INTEGRATED MARKET ENGINE
# ============================================================

PRICE_FILE = os.path.join(os.path.dirname(__file__), "data", "prices.csv")

# Storage knowledge (assumptions, shown to the user as such).
# cost = Rs per quintal per month, spoil = % of stock lost per month
STORAGE = {
    "grain":     dict(cost=15, spoil=0.5, max_days=365, cond="Dry godown, moisture below 12%, temperature under 25C, hermetic or jute bags on pallets, fumigate against weevils."),
    "pulse":     dict(cost=18, spoil=0.7, max_days=270, cond="Moisture below 10%, airtight bins, neem leaves or fumigation against bruchids, cool dry room."),
    "oilseed":   dict(cost=18, spoil=0.8, max_days=180, cond="Moisture below 8-9%, ventilated dry store, avoid heat (oil goes rancid)."),
    "vegetable": dict(cost=40, spoil=8.0, max_days=10,  cond="Cool shaded place, crates with ventilation. Cold storage (2-10C, 85-90% humidity) only if the crop suits it."),
    "onion":     dict(cost=25, spoil=3.5, max_days=150, cond="Cured bulbs, ventilated shed or bamboo structure, 25-30C and below 65% humidity, stack height under 1.5 m."),
    "potato":    dict(cost=30, spoil=1.5, max_days=240, cond="Cold storage at 2-4C (seed) or 10-12C (processing), 90% humidity, dark."),
    "fruit":     dict(cost=45, spoil=10.0, max_days=14, cond="Cold chain, 85-95% humidity, grade and pack in ventilated crates."),
    "spice":     dict(cost=30, spoil=1.0, max_days=270, cond="Fully dried, airtight bags, cool dark dry store away from strong odours."),
    "fibre":     dict(cost=20, spoil=0.4, max_days=300, cond="Dry covered godown, off the floor, protect from moisture and fire."),
    "default":   dict(cost=25, spoil=2.0, max_days=90,  cond="Clean dry ventilated store, graded produce, monitor weekly for moisture and pests."),
}
CATEGORY = {
    "grain": "paddy rice wheat maize jowar bajra ragi barley sorghum",
    "pulse": "gram chana tur arhar lentil masur moong urad peas",
    "oilseed": "groundnut soyabean soybean mustard sunflower sesamum castor linseed",
    "onion": "onion", "potato": "potato",
    "vegetable": "tomato brinjal cabbage cauliflower okra bhindi carrot beans chilli capsicum cucumber gourd",
    "fruit": "banana mango apple grapes orange papaya pomegranate",
    "spice": "turmeric ginger coriander cumin garlic pepper cardamom",
    "fibre": "cotton jute",
}
MSP_NOTE = "Compare with the government MSP for your crop; below MSP, consider selling to procurement centres."

def category(crop):
    c = crop.lower()
    for cat, words in CATEGORY.items():
        if any(w in c for w in words.split()):
            return cat
    return "default"

def _col(df, names):
    for n in names:
        for c in df.columns:
            if c.strip().lower().replace(" ", "_") == n:
                return c
    return None

def load_prices():
    if not os.path.exists(PRICE_FILE):
        return None
    df = pd.read_csv(PRICE_FILE)
    d, c, p = (_col(df, ["date", "arrival_date", "price_date"]),
               _col(df, ["commodity", "crop", "item"]),
               _col(df, ["modal_price", "price", "modal"]))
    if not (d and c and p):
        raise ValueError("prices.csv needs columns: date, commodity (or crop), modal_price (or price)")
    raw = df[d].astype(str).str.strip()
    dt = pd.to_datetime(raw, errors="coerce", format="%Y-%m-%d")
    miss = dt.isna()
    if miss.any():  # Agmarknet style dd/mm/yyyy
        dt[miss] = pd.to_datetime(raw[miss], errors="coerce", dayfirst=True)
    out = pd.DataFrame({"date": dt,
                        "crop": df[c].astype(str).str.strip().str.lower(),
                        "price": pd.to_numeric(df[p], errors="coerce")})
    s = _col(df, ["state"])
    out["state"] = df[s].astype(str).str.strip().str.lower() if s else ""
    return out.dropna(subset=["date", "price"]).query("price > 0")

def crop_list():
    df = load_prices()
    return sorted(df["crop"].unique().tolist()) if df is not None else []

def analyse(crop, state="", quantity=10, live=None, today=None, manual_price=None, hist=None, district=""):
    crop = crop.lower().strip()
    if hist is not None:
        h = hist
    else:
        df = load_prices()
        if df is None:
            raise ValueError("No price history found.")
        h = df[df["crop"] == crop]
        if state:
            hs = h[h["state"] == state.lower().strip()]
            if len(hs) >= 60:
                h = hs
    if len(h) < 60:
        raise ValueError(f"Not enough price history for '{crop}' ({len(h)} records).")
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    cat = category(crop); st = STORAGE[cat]

    monthly = h.set_index("date")["price"].resample("MS").mean().dropna()
    latest_hist = h["date"].max()
    age_days = int((today - latest_hist).days)
    if manual_price and manual_price > 0:
        current, source = float(manual_price), "entered"
    elif live:
        current, source = live["price"], "live"
    else:
        current, source = float(h.sort_values("date").tail(14)["price"].mean()), "history"
    stale = age_days > 60

    # Seasonal index: month average / yearly average, averaged across years
    m = monthly.to_frame("p"); m["y"] = m.index.year; m["m"] = m.index.month
    m["idx"] = m["p"] / m.groupby("y")["p"].transform("mean")
    seas = m.groupby("m")["idx"].mean()
    spread = m.groupby("m")["idx"].std().fillna(0.1)
    years = m["y"].nunique()

    # Recent trend (percent per month, last 90 days vs previous 90)
    r = h[h["date"] > latest_hist - pd.Timedelta(days=90)]["price"].mean()
    pr = h[(h["date"] <= latest_hist - pd.Timedelta(days=90)) & (h["date"] > latest_hist - pd.Timedelta(days=180))]["price"].mean()
    trend_pm = float((r / pr - 1) / 3) if pr and not np.isnan(pr) else 0.0
    trend_pm = max(-0.08, min(0.08, trend_pm))

    pct = float((h[h["date"] > latest_hist - pd.Timedelta(days=3*365)]["price"] < current).mean() * 100)
    cur_idx = seas.get(today.month, 1.0)

    scenarios = []
    for label, days in [("Sell now", 0), ("Hold 7 days", 7), ("Hold 15 days", 15), ("Hold 1 month", 30),
                        ("Hold 2 months", 60), ("Hold 3 months", 90), ("Hold 6 months", 180)]:
        if days > st["max_days"]:
            continue
        tgt = today + pd.Timedelta(days=days)
        s_ratio = seas.get(tgt.month, 1.0) / cur_idx if cur_idx else 1.0
        # seasonal move + damped trend; short holds rely less on seasonality
        w = min(1.0, days / 30)
        exp = current * (1 + (s_ratio - 1) * w) * (1 + trend_pm * (days / 30) * 0.5)
        months = days / 30
        storage = st["cost"] * months
        spoil = exp * (st["spoil"] / 100) * months
        interest = current * 0.01 * months  # 12%/yr opportunity cost
        net = exp - storage - spoil - interest
        sd = float(spread.get(tgt.month, 0.1)) * current * np.sqrt(max(months, 0.25))
        scenarios.append(dict(label=label, days=days, expected=round(exp, 1), storage=round(storage, 1),
                              spoilage=round(spoil, 1), interest=round(interest, 1), net=round(net, 1),
                              gain=round(net - current, 1), gain_pct=round((net / current - 1) * 100, 1),
                              low=round(net - sd, 1), high=round(net + sd, 1),
                              total_gain=round((net - current) * quantity, 0)))
    best = max(scenarios, key=lambda s: s["net"])
    threshold = max(0.03 * current, 20)
    if best["days"] == 0 or best["gain"] < threshold:
        action = "SELL_NOW"
        reason = "Waiting is not expected to beat storage cost, spoilage and interest."
        best_s = scenarios[0]
    else:
        best_s = best
        action = "HOLD_DAYS" if best["days"] <= 15 else "HOLD_WEEKS" if best["days"] <= 45 else "HOLD_MONTHS"
        reason = f"Prices usually firm up by {(today + pd.Timedelta(days=best['days'])).strftime('%B')}."
    if pct >= 85 and action != "SELL_NOW" and best_s["days"] > 0:
        reason += " Note: current price is already near the top of its 3-year range."
    if trend_pm < -0.03 and cat in ("vegetable", "fruit"):
        action, best_s, reason = "SELL_NOW", scenarios[0], "Perishable crop with a falling price trend."

    conf = "High" if years >= 5 and len(h) > 500 else "Medium" if years >= 3 else "Low"
    if source == "history" and stale:
        conf = "Low"
        reason += " Warning: the latest price on record is old, so enter today's price for a reliable answer."
    chart = [{"month": d.strftime("%b %Y"), "price": round(v, 1)} for d, v in monthly.tail(36).items()]
    seasonal = [{"month": pd.Timestamp(2000, k, 1).strftime("%b"), "index": round(float(v), 3)} for k, v in seas.items()]
    return dict(crop=crop, category=cat, state=state, district=district.strip(), quantity=quantity, current_price=round(current, 1),
                price_source=source, live=live, history_last_date=str(latest_hist.date()), data_age_days=age_days, stale=stale,
                years_of_data=int(years), records=int(len(h)), percentile_3y=round(pct, 0),
                trend_pct_per_month=round(trend_pm * 100, 1), action=action, reason=reason,
                best=best_s, scenarios=scenarios, storage=dict(st, category=cat), confidence=conf,
                chart=chart, seasonal=seasonal, msp_note=MSP_NOTE)


def analyse_without_history(crop, state, district, quantity, price, today=None, note=""):
    """Give a transparent cost-only estimate when the farmer supplied today's price."""
    crop = crop.strip()
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    cat = category(crop)
    storage = STORAGE[cat]
    current = float(price)
    scenarios = []

    for label, days in [
        ("Sell now", 0),
        ("Hold 7 days", 7),
        ("Hold 15 days", 15),
        ("Hold 1 month", 30),
        ("Hold 2 months", 60),
        ("Hold 3 months", 90),
        ("Hold 6 months", 180),
    ]:
        if days > storage["max_days"]:
            continue
        months = days / 30
        storage_cost = storage["cost"] * months
        spoilage = current * (storage["spoil"] / 100) * months
        interest = current * 0.01 * months
        net = current - storage_cost - spoilage - interest
        scenarios.append({
            "label": label,
            "days": days,
            "expected": round(current, 1),
            "storage": round(storage_cost, 1),
            "spoilage": round(spoilage, 1),
            "interest": round(interest, 1),
            "net": round(net, 1),
            "gain": round(net - current, 1),
            "gain_pct": round((net / current - 1) * 100, 1),
            "low": round(net, 1),
            "high": round(net, 1),
            "total_gain": round((net - current) * quantity, 0),
        })

    reason = (
        "No verified price history is available for this crop and location. "
        "This conservative estimate assumes the price stays flat; under that assumption, "
        "waiting adds storage, spoilage and interest costs."
    )
    result = {
        "crop": crop.lower(),
        "category": cat,
        "state": state,
        "district": district,
        "quantity": quantity,
        "current_price": round(current, 1),
        "price_source": "entered",
        "live": None,
        "history_last_date": None,
        "data_age_days": None,
        "stale": False,
        "years_of_data": 0,
        "records": 0,
        "percentile_3y": None,
        "trend_pct_per_month": None,
        "action": "SELL_NOW",
        "reason": reason,
        "best": scenarios[0],
        "scenarios": scenarios,
        "storage": dict(storage, category=cat),
        "confidence": "Low",
        "chart": [],
        "seasonal": [],
        "msp_note": MSP_NOTE,
        "history_available": False,
        "note": note,
    }
    return result


def _price_history_from_market_records(records):
    prices = []
    for record in records:
        price_value = _parse_market_price(record.get("modal_price"))
        date_value = str(record.get("arrival_date") or "").strip()
        parsed_date = pd.to_datetime(date_value, dayfirst=True, errors="coerce")
        if price_value is not None and price_value > 0 and not pd.isna(parsed_date):
            prices.append({"date": parsed_date.normalize(), "price": price_value})
    if not prices:
        return pd.DataFrame(columns=["date", "price"]), None

    history = pd.DataFrame(prices)
    latest_date = history["date"].max()
    latest_prices = history.loc[history["date"] == latest_date, "price"]
    live = {
        "price": float(latest_prices.median()),
        "markets": int(len(latest_prices)),
        "low": float(latest_prices.quantile(0.1)),
        "high": float(latest_prices.quantile(0.9)),
        "date": latest_date.strftime("%Y-%m-%d"),
    }
    return history, live


def _market_advice_from_ceda(crop, state, district, quantity, price):
    history, note, resolved = get_history(crop, state, district)
    history = history[["date", "price"]].copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history["price"] = pd.to_numeric(history["price"], errors="coerce")
    history = history.dropna(subset=["date", "price"]).sort_values("date")
    if history.empty:
        raise MarketDataError("CEDA returned no usable price records.")

    latest = history.iloc[-1]
    latest_date = latest["date"].strftime("%Y-%m-%d")
    live = {
        "price": float(latest["price"]),
        "markets": 1,
        "date": latest_date,
    }
    fallback_note = (
        "data.gov.in could not be reached. Using the latest available CEDA price "
        f"record from {latest_date}; this may not be today's mandi price."
    )
    if note:
        fallback_note = f"{fallback_note} {note}"

    commodity = resolved.get("crop", crop)
    resolved_state = resolved.get("state", state)
    resolved_district = resolved.get("district", district)
    if len(history) < 60:
        current_price = price if price > 0 else live["price"]
        result = analyse_without_history(
            commodity,
            resolved_state,
            resolved_district,
            quantity,
            current_price,
            note=f"{fallback_note} Only {len(history)} records are available, so a reliable trend forecast is not available.",
        )
        result["price_source"] = "entered" if price > 0 else "history"
        result["live"] = live
        result["history_last_date"] = latest_date
        result["records"] = len(history)
        return result

    result = analyse(
        commodity,
        resolved_state,
        quantity,
        live,
        manual_price=price if price > 0 else None,
        hist=history,
        district=resolved_district,
    )
    result["price_source"] = "entered" if price > 0 else "history"
    result["note"] = (
        f"Your entered price is used instead of the latest CEDA record from {latest_date}. "
        f"{fallback_note}"
        if price > 0
        else fallback_note
    )
    result["history_available"] = True
    result["state"] = resolved_state
    result["district"] = resolved_district
    return result


# ============================================================
# MARKET API ROUTES
# ============================================================

@app.get("/market-meta")
def market_meta(user: User = Depends(current_user)):
    try:
        states = [{"name": s["name"], "districts": [d["name"] for d in s["districts"]]} for s in geography()]
        crops = crop_names()
    except MarketDataError:
        df = load_prices()
        states = []
        if df is not None and not df.empty:
            for state_name in sorted({str(s).strip() for s in df["state"].dropna().unique() if str(s).strip()}):
                states.append({"name": state_name.title(), "districts": []})
        crops = crop_list()
    return {"crops": crops, "states": states}


@app.get("/market-crops")
def market_crops(user: User = Depends(current_user)):
    try:
        return {"crops": crop_names()}
    except MarketDataError:
        return {"crops": crop_list()}


_LIVE_DOWN_UNTIL = 0.0
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _try_live(crop, state, district):
    """Quick live-price attempt. Never raises; skips for 10 min after a failure."""
    global _LIVE_DOWN_UNTIL
    if time.time() < _LIVE_DOWN_UNTIL:
        return None, None
    if not (os.getenv("DATA_GOV_IN_API_KEY") or os.getenv("DATA_GOV_API_KEY")):
        return None, None
    try:
        _, records = _fetch_data_gov_records(crop, state, district, "")
        hist, live = _price_history_from_market_records(records)
        return (hist, live) if live else (None, None)
    except Exception:
        _LIVE_DOWN_UNTIL = time.time() + 600
        return None, None


def _proxy_history(crop, state):
    """Closest saved variety of the same crop (e.g. Basmati -> Common paddy) in the same state."""
    try:
        df = load_prices()
    except Exception:
        return None, ""
    if df is None or df.empty:
        return None, ""
    words = [w for w in re.split(r"[^a-z]+", crop.lower()) if len(w) > 2]
    if not words:
        return None, ""
    sub = df[(df["state"] == state.lower().strip()) & (df["crop"].str.contains(words[0], regex=False))]
    if sub.empty:
        return None, ""
    best = sub["crop"].value_counts().idxmax()
    h = sub[sub["crop"] == best][["date", "price"]].sort_values("date")
    return (h, best) if len(h) >= 60 else (None, "")


@app.get("/market-advice")
def market_advice(
    crop: str,
    state: str = "",
    district: str = "",
    quantity: float = 10,
    price: float = 0,
    user: User = Depends(current_user),
):
    crop_name = crop.strip()
    state_name = state.strip()
    district_name = district.strip()
    if not crop_name:
        raise HTTPException(status_code=400, detail="Type a crop first.")
    if not state_name:
        raise HTTPException(status_code=400, detail="Choose a state first.")

    # 1) live price (only if the farmer did not type one) - fast, never blocks long
    live_hist, live = (None, None) if price > 0 else _try_live(crop_name, state_name, district_name)

    # 2) saved / CEDA history with a hard time limit
    hist, resolved, ceda_note, err = None, {}, "", ""
    try:
        fut = _POOL.submit(get_history, crop_name, state_name, district_name)
        h, ceda_note, resolved = fut.result(timeout=25)
        h = h[["date", "price"]].copy()
        h["date"] = pd.to_datetime(h["date"], errors="coerce")
        h["price"] = pd.to_numeric(h["price"], errors="coerce")
        h = h.dropna(subset=["date", "price"]).sort_values("date")
        hist = h if not h.empty else None
    except concurrent.futures.TimeoutError:
        err = "the price-history service is busy right now"
    except Exception as e:
        err = str(e)

    commodity = resolved.get("crop", crop_name)
    res_state = resolved.get("state", state_name)
    res_dist = resolved.get("district", district_name)

    proxy_note = ""
    if hist is None or len(hist) < 60:
        ph, pname = _proxy_history(crop_name, state_name)
        if ph is not None:
            hist = ph
            proxy_note = (f"No saved history for '{crop_name}', so the history of '{pname}' "
                          "(closest saved variety) is used as a substitute.")

    if (hist is None or len(hist) < 60) and live_hist is not None and len(live_hist) >= 60:
        hist = live_hist

    if hist is None or len(hist) < 60:
        if price > 0 or live:
            current = price if price > 0 else live["price"]
            result = analyse_without_history(
                commodity, res_state, res_dist, quantity, current,
                note="No saved price history for this crop and state, so this is a cost-only estimate "
                     "from the price " + ("you entered." if price > 0 else "reported live.")
                     + " It is not a market-price prediction.",
            )
            result["price_source"] = "entered" if price > 0 else "live"
            result["live"] = live
            return result
        raise HTTPException(
            status_code=400,
            detail=f"No saved price history for {crop_name} in {state_name}"
                   + (f" ({err})" if err else "")
                   + ". Type today's mandi price in 'Price override' for a cost-based estimate, "
                     "or choose a crop/state that has saved data (e.g. Paddy(Dhan)(Common), Karnataka).",
        )

    try:
        result = analyse(commodity, res_state, quantity, live, manual_price=price if price > 0 else None,
                         hist=hist, district=res_dist)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    last = hist["date"].max().strftime("%Y-%m-%d")
    if price > 0:
        note = f"Your entered price is used with saved history up to {last}."
    elif live:
        note = f"Live Agmarknet price dated {live['date']} used with saved history up to {last}."
    else:
        note = (f"Live prices are unavailable, so the latest saved price (history up to {last}) is used. "
                "Enter today's mandi price in 'Price override' for a more reliable answer.")
    if proxy_note:
        note = proxy_note + " " + note
    if ceda_note:
        note += " " + ceda_note
    result["note"] = note
    result["history_available"] = True
    result["state"] = res_state
    result["district"] = res_dist
    return result


# ============================================================
# CHAT ASSISTANT
# ============================================================

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatData(BaseModel):
    message: str
    history: list[ChatMessage] = []


CHAT_SYSTEM = (
    "You are AgroVision Assistant, a friendly farming helper for small farmers in India. "
    "Answer questions about crops, soil, seasons, fertilizers, pests and diseases, harvesting, "
    "storage, mandi prices and selling decisions, and government schemes (MSP, PM-KISAN, crop insurance). "
    "Reply in the same language the user writes in (English, Hindi, Kannada, etc.). "
    "Keep answers short, practical and in simple words; use short bullet points for steps. "
    "Do not invent prices or scheme amounts; if unsure, say so and suggest the local agriculture officer "
    "or the Marketing page of this app. If the question is not about farming, politely steer back to farming."
)


@app.post("/chat")
def chat(data: ChatData, user: User = Depends(current_user)):
    text = data.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Type a question first.")
    msgs = [{"role": "system", "content": CHAT_SYSTEM}]
    for m in data.history[-8:]:
        if m.role in ("user", "assistant") and m.content.strip():
            msgs.append({"role": m.role, "content": m.content[:2000]})
    msgs.append({"role": "user", "content": text[:2000]})
    last = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL, messages=msgs, max_tokens=800, temperature=0.4
            )
            reply = resp.choices[0].message.content or ""
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            return {"reply": reply or "Sorry, I could not answer that. Please try again."}
        except Exception as e:
            last = e
            if any(k in str(e).lower() for k in ("503", "429", "overloaded", "rate limit")):
                time.sleep(2 * (attempt + 1))
                continue
            break
    raise HTTPException(status_code=502, detail=f"The assistant is busy right now. Please try again. ({last})")