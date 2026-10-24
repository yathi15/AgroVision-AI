import os, requests
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("DATA_GOV_API_KEY")
print("key loaded:", bool(key), "| length:", len(key or ""), "| starts with:", (key or "")[:4])
URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
tests = {
  "no filter": {"api-key": key, "format": "json", "limit": 2},
  "onion":     {"api-key": key, "format": "json", "limit": 2, "filters[commodity]": "Onion"},
  "onion+Karnataka": {"api-key": key, "format": "json", "limit": 2, "filters[commodity]": "Onion", "filters[state]": "Karnataka"},
}
for name, p in tests.items():
    try:
        r = requests.get(URL, params=p, timeout=60)
        print(f"\n== {name}: HTTP {r.status_code}")
        print(r.text[:500])
    except Exception as e:
        print(f"\n== {name}: FAILED -> {e}")