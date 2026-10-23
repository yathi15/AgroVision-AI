"""CEDA Agmarknet API client: any crop, any state, optional district. Results are cached on disk."""
import os, re, json, time, difflib, datetime as dt
import requests, pandas as pd
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api.ceda.ashoka.edu.in/v1/agmarknet"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "data", "cache")
LOCAL_CSV = os.path.join(HERE, "data", "prices.csv")
START_YEAR = 2019
CACHE_DAYS = 30
_mem = {}

class MarketDataError(ValueError):
    pass

def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

def _call(method, path, **kw):
    key = os.getenv("CEDA_API_KEY")
    if not key:
        raise MarketDataError("CEDA_API_KEY is missing in backend/.env")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(4):
        try:
            r = requests.request(method, BASE + path, headers=headers, timeout=45, **kw)
        except requests.RequestException:
            time.sleep(2); continue
        if r.status_code == 429:
            time.sleep(3 * (attempt + 1)); continue
        if r.status_code == 401:
            raise MarketDataError("The CEDA API key was rejected. It may have expired; saved data is used when available.")
        return r
    return None

def _meta(name, path):
    if name in _mem:
        return _mem[name]
    os.makedirs(CACHE_DIR, exist_ok=True)
    f = os.path.join(CACHE_DIR, f"meta_{name}.json")
    data = None
    if os.path.exists(f):
        data = json.load(open(f, encoding="utf-8"))
    else:
        r = _call("GET", path)
        if r is not None and r.status_code == 200:
            data = r.json()["output"]["data"]
            json.dump(data, open(f, "w", encoding="utf-8"))
    if data is None:
        raise MarketDataError("Could not load the list of crops and states from the price service. Try again in a minute.")
    _mem[name] = data
    return data

def commodities():
    return _meta("commodities", "/commodities")

def geography():
    """[{id, name, districts:[{id, name}]}] sorted by name."""
    states = {}
    for g in _meta("geographies", "/geographies"):
        sid = g["census_state_id"]
        nm = g["census_state_name"].replace("&", " & ").replace("  ", " ").strip()
        st = states.setdefault(sid, {"id": sid, "name": nm, "districts": []})
        st["districts"].append({"id": g["census_district_id"], "name": g["census_district_name"].strip()})
    out = sorted(states.values(), key=lambda s: s["name"])
    for s in out:
        s["districts"].sort(key=lambda d: d["name"])
    return out

def crop_names():
    return sorted({c["commodity_name"] for c in commodities()})

def find_commodity(name):
    n = norm(name)
    coms = commodities()
    exact = [c for c in coms if norm(c["commodity_name"]) == n]
    if exact:
        return exact[0]
    part = [c for c in coms if n and (n in norm(c["commodity_name"]))]
    if part:
        return sorted(part, key=lambda c: len(c["commodity_name"]))[0]
    close = difflib.get_close_matches(n, [norm(c["commodity_name"]) for c in coms], n=4, cutoff=0.6)
    names = [c["commodity_name"] for c in coms if norm(c["commodity_name"]) in close]
    hint = f" Did you mean: {', '.join(names)}?" if names else ""
    raise MarketDataError(f"No crop named '{name}' in the price database.{hint}")

def find_state(name):
    n = norm(name)
    for s in geography():
        if norm(s["name"]) == n:
            return s
    for s in geography():
        if n and n in norm(s["name"]):
            return s
    raise MarketDataError(f"State '{name}' not found. Choose a state from the list.")

def find_district(state, name):
    n = norm(name)
    for d in state["districts"]:
        if norm(d["name"]) == n:
            return d
    for d in state["districts"]:
        if n and n in norm(d["name"]):
            return d
    return None

def _rows(r):
    out = []
    for d in r.json().get("output", {}).get("data", []) or []:
        if d.get("modal_price"):
            out.append((d["date"][:10], float(d["modal_price"]), d.get("min_price"), d.get("max_price")))
    return out

def _fetch(cid, sid, did=None):
    today = dt.date.today()
    rows, ok = [], False
    for year in range(START_YEAR, today.year + 1):
        body = {"commodity_id": cid, "state_id": sid,
                "from_date": f"{year}-01-01", "to_date": min(dt.date(year, 12, 31), today).isoformat()}
        if did:
            body["district_id"] = did
        r = _call("POST", "/prices", json=body)
        if r is None:
            continue
        if r.status_code == 200:
            ok = True
            rows += _rows(r)
        elif r.status_code == 400 and did:
            return None, "bad_district"
        time.sleep(0.3)
    return (rows if ok else None), ""

def _from_local_csv(crop_name, state_name):
    if not os.path.exists(LOCAL_CSV):
        return None
    try:
        df = pd.read_csv(LOCAL_CSV)
        m = (df["commodity"].map(norm) == norm(crop_name)) & (df["state"].map(norm) == norm(state_name))
        d = df[m]
        if len(d):
            return pd.DataFrame({"date": pd.to_datetime(d["date"]), "price": d["modal_price"].astype(float)})
    except Exception:
        return None
    return None

def get_history(crop, state, district=""):
    """Returns (DataFrame[date, price], note, resolved) for a crop in a state (optional district)."""
    if not state:
        raise MarketDataError("Choose a state.")
    com, st = find_commodity(crop), find_state(state)
    dist = find_district(st, district) if district else None
    resolved = {"crop": com["commodity_name"], "state": st["name"], "district": dist["name"] if dist else ""}
    os.makedirs(CACHE_DIR, exist_ok=True)

    def cache_file(d):
        return os.path.join(CACHE_DIR, f"{com['commodity_id']}_{st['id']}_{d['id'] if d else 0}.csv")

    def read_cache(d):
        f = cache_file(d)
        if os.path.exists(f):
            df = pd.read_csv(f, parse_dates=["date"])
            age = (time.time() - os.path.getmtime(f)) / 86400
            return df, age
        return None, None

    note = ""
    for d in ([dist, None] if dist else [None]):
        df, age = read_cache(d)
        if df is not None and age < CACHE_DAYS and len(df):
            if dist and d is None:
                note = f"District-level prices for {dist['name']} are not available; showing {st['name']} state prices."
                resolved["district"] = ""
            return df, note, resolved

    # Prices already downloaded with sync_prices.py are used first (no key or internet needed)
    if not dist:
        local0 = _from_local_csv(com["commodity_name"], st["name"])
        if local0 is not None and len(local0) >= 60:
            return local0, "", resolved

    try:
        rows, bad = _fetch(com["commodity_id"], st["id"], dist["id"] if dist else None)
    except MarketDataError:
        rows, bad = None, ""
    used = dist
    if (rows is None or not rows) and dist:
        try:
            rows, _ = _fetch(com["commodity_id"], st["id"], None)
        except MarketDataError:
            rows = None
        used = None
        if rows:
            note = f"District-level prices for {dist['name']} are not available; showing {st['name']} state prices."
            resolved["district"] = ""
    if rows:
        df = pd.DataFrame(rows, columns=["date", "price", "min", "max"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.drop_duplicates("date").sort_values("date")
        df.to_csv(cache_file(used), index=False)
        return df, note, resolved

    # API failed or no data: try old saved copies
    for d in ([dist, None] if dist else [None]):
        df, _ = read_cache(d)
        if df is not None and len(df):
            return df, "The price service is busy or unavailable, so saved data is shown.", resolved
    local = _from_local_csv(com["commodity_name"], st["name"])
    if local is not None:
        return local, "The price service is unavailable, so saved data is shown.", resolved
    if rows is not None:
        raise MarketDataError(f"No price records for {com['commodity_name']} in {st['name']}. Try another state or crop.")
    raise MarketDataError("The price service did not respond (limit reached or offline). Wait a minute and try again.")