import os, itertools, requests
from dotenv import load_dotenv
load_dotenv()
H = {"Authorization": f"Bearer {os.getenv('CEDA_API_KEY')}", "Content-Type": "application/json"}
URL = "https://api.ceda.ashoka.edu.in/v1/agmarknet/prices"

names = [("commodity_id","state_id","start_date","end_date"),
         ("commodity_id","state_id","from_date","to_date"),
         ("commodityId","stateId","startDate","endDate"),
         ("commodity_id","state_id","start","end")]
dates = [("2024-01-01","2024-01-31"), ("01-01-2024","31-01-2024"), ("01/01/2024","31/01/2024")]

for (c,s,a,b), (d1,d2) in itertools.product(names, dates):
    body = {c: 18, s: 29, a: d1, b: d2}   # 18 = Onion? check below, 29 = Karnataka
    r = requests.post(URL, headers=H, json=body, timeout=30)
    ok = r.status_code == 200
    print("OK " if ok else "no ", body, "->", r.status_code, r.text[:300].replace("\n"," "))
    if ok:
        break