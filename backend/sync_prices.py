"""One-time sync: download price history from the CEDA Agmarknet API into data/prices.csv.
Run:  python sync_prices.py            (default crops and states)
      python sync_prices.py onion tomato --states karnataka "tamil nadu" --from 2019
The saved file is all the Marketing page needs afterwards (no key required to run the app)."""
import os, sys, time, argparse, datetime as dt
import requests, pandas as pd
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("CEDA_API_KEY")
BASE = "https://api.ceda.ashoka.edu.in/v1/agmarknet"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "prices.csv")

DEFAULT_CROPS = ["onion", "tomato", "potato", "wheat", "paddy", "maize", "groundnut", "banana"]
DEFAULT_STATES = ["karnataka", "maharashtra", "tamil nadu", "andhra pradesh"]

PATIENT = False

def call(method, path, **kw):
    """Calls CEDA. On rate limit it waits and tries again. In --patient mode it keeps waiting (up to ~6 hours)."""
    rounds = 72 if PATIENT else 1
    for rnd in range(rounds):
        for attempt in range(6):
            try:
                r = requests.request(method, BASE + path, headers=H, timeout=60, **kw)
            except requests.RequestException as e:
                print("  network problem, retrying:", e); time.sleep(3); continue
            if r.status_code == 429:
                wait = 5 * (attempt + 1); print(f"  rate limit, waiting {wait}s"); time.sleep(wait); continue
            if r.status_code == 401:
                sys.exit("Key rejected (401). Check CEDA_API_KEY in .env, or the key has expired.")
            return r
        if PATIENT and rnd < rounds - 1:
            print(f"  still limited. Sleeping 5 minutes, then trying again ({rnd + 1}/{rounds - 1})...")
            time.sleep(300)
    sys.exit("CEDA is still rate limiting. Leave it for an hour (or until tomorrow) and run again; saved data is kept.")

def save(rows):
    new = pd.DataFrame(rows, columns=["date", "commodity", "state", "min_price", "max_price", "modal_price"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        old = pd.read_csv(OUT)
        if {"commodity", "state", "date", "modal_price"} <= set(old.columns):
            new = pd.concat([old, new])
    new = new.drop_duplicates(subset=["date", "commodity", "state"], keep="last").sort_values(["commodity", "state", "date"])
    new.to_csv(OUT, index=False)
    return new

def main():
    if not KEY:
        sys.exit("CEDA_API_KEY not found in backend/.env")
    ap = argparse.ArgumentParser()
    ap.add_argument("crops", nargs="*", default=DEFAULT_CROPS)
    ap.add_argument("--states", nargs="*", default=DEFAULT_STATES)
    ap.add_argument("--from", dest="start", type=int, default=2019, help="first year")
    ap.add_argument("--patient", action="store_true", help="keep waiting through rate limits (leave it running)")
    a = ap.parse_args()
    global PATIENT
    PATIENT = a.patient

    com = call("GET", "/commodities").json()["output"]["data"]
    geo = call("GET", "/geographies").json()["output"]["data"]
    states = {}
    for g in geo:
        states.setdefault(g["census_state_id"], g["census_state_name"].replace("&", " & ").replace("  ", " ").strip())

    todo_c = []
    for want in a.crops:
        hit = [c for c in com if want.lower() in c["commodity_name"].lower()]
        if not hit: print(f"! no commodity matches '{want}'"); continue
        hit.sort(key=lambda c: len(c["commodity_name"]))  # shortest name = most basic variant
        todo_c.append(hit[0]); print(f"'{want}' -> {hit[0]['commodity_name']} (id {hit[0]['commodity_id']})")
    todo_s = [(i, n) for i, n in states.items() if any(w.lower() in n.lower() for w in a.states)]
    print("states:", [n for _, n in todo_s])

    done = set()
    if os.path.exists(OUT):
        try:
            _o = pd.read_csv(OUT)
            done = set(zip(_o["commodity"], _o["state"]))
        except Exception:
            pass
    today = dt.date.today()
    for c in todo_c:
        for sid, sname in todo_s:
            if (c["commodity_name"], sname) in done:
                print(f"  {c['commodity_name']} / {sname}: already saved, skipping"); continue
            rows, got = [], 0
            for year in range(a.start, today.year + 1):
                body = {"commodity_id": c["commodity_id"], "state_id": sid,
                        "from_date": f"{year}-01-01", "to_date": min(dt.date(year, 12, 31), today).isoformat()}
                r = call("POST", "/prices", json=body)
                if r is None or r.status_code != 200: continue
                for d in r.json().get("output", {}).get("data", []):
                    if d.get("modal_price"):
                        rows.append((d["date"][:10], c["commodity_name"], sname, d.get("min_price"), d.get("max_price"), d["modal_price"]))
                        got += 1
                time.sleep(1.5)
            print(f"  {c['commodity_name']} / {sname}: {got} rows")
            if rows:
                save(rows)

    if os.path.exists(OUT):
        final = pd.read_csv(OUT)
        print(f"\nDone. {len(final)} rows in {OUT}")
        print(final.groupby("commodity")["date"].agg(["min", "max", "count"]))

if __name__ == "__main__":
    main()