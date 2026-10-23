"""AgroVision market engine: history + live price -> sell/hold decision."""
import os, re
import requests
import pandas as pd
import numpy as np

PRICE_FILE = os.path.join(os.path.dirname(__file__), "data", "prices.csv")
RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"  # Agmarknet daily prices on data.gov.in

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

def live_price(crop, state=""):
    key = os.getenv("DATA_GOV_API_KEY")
    if not key:
        return None
    params = {"api-key": key, "format": "json", "limit": 200, "filters[commodity]": crop.title()}
    if state:
        params["filters[state]"] = state.title()
    try:
        r = requests.get(f"https://api.data.gov.in/resource/{RESOURCE}", params=params, timeout=15)
        rows = r.json().get("records", [])
    except Exception:
        return None
    vals = [float(x["modal_price"]) for x in rows if str(x.get("modal_price", "")).replace(".", "").isdigit()]
    if not vals:
        return None
    return dict(price=float(np.median(vals)), markets=len(vals),
                low=float(np.percentile(vals, 10)), high=float(np.percentile(vals, 90)),
                date=rows[0].get("arrival_date", ""))

def analyse(crop, state="", quantity=10, live=None, today=None, manual_price=None, hist=None):
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
    return dict(crop=crop, category=cat, state=state, quantity=quantity, current_price=round(current, 1),
                price_source=source, live=live, history_last_date=str(latest_hist.date()), data_age_days=age_days, stale=stale,
                years_of_data=int(years), records=int(len(h)), percentile_3y=round(pct, 0),
                trend_pct_per_month=round(trend_pm * 100, 1), action=action, reason=reason,
                best=best_s, scenarios=scenarios, storage=dict(st, category=cat), confidence=conf,
                chart=chart, seasonal=seasonal, msp_note=MSP_NOTE)