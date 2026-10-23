"""Weather for the Harvest page. The backend fetches it (browsers on some networks are blocked)
and tries four free providers, no API key needed:
  1) Open-Meteo   2) MET Norway   3) wttr.in   4) 7timer
Returns: {temperature, humidity, days:[{date, rain, max}], source}
"""
import socket
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import requests
from fastapi import APIRouter, HTTPException

# Some networks silently drop IPv6 connections, which makes Python wait until it times out.
# Browsers fall back to IPv4 by themselves; Python does not, so we ask for IPv4 explicitly.
try:
    import urllib3.util.connection as _u3c
    _u3c.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

router = APIRouter()
UA = {"User-Agent": "AgroVisionAI/1.0 (student project)"}


def _open_meteo(lat, lon):
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m",
            "daily": "precipitation_sum,temperature_2m_max",
            "forecast_days": 7, "timezone": "auto",
        },
        headers=UA, timeout=6,
    )
    r.raise_for_status()
    j = r.json()
    d = j["daily"]
    days = [
        {"date": t, "rain": d["precipitation_sum"][i] or 0, "max": d["temperature_2m_max"][i]}
        for i, t in enumerate(d["time"])
    ]
    return {
        "temperature": j["current"]["temperature_2m"],
        "humidity": j["current"]["relative_humidity_2m"],
        "days": days,
        "source": "Open-Meteo",
    }


def _parse_met_no(j, lon):
    """Turn MET Norway timeseries into 7 local days (local time estimated from longitude)."""
    series = j["properties"]["timeseries"]
    offset = timedelta(hours=round(lon / 15.0))
    first = series[0]["data"]["instant"]["details"]
    per_day = OrderedDict()
    for e in series:
        t = datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(timezone.utc) + offset
        key = t.strftime("%Y-%m-%d")
        slot = per_day.setdefault(key, {"rain": 0.0, "max": None})
        det = e["data"]["instant"]["details"]
        temp = det.get("air_temperature")
        if temp is not None and (slot["max"] is None or temp > slot["max"]):
            slot["max"] = temp
        nxt = e["data"].get("next_1_hours") or e["data"].get("next_6_hours")
        if nxt:
            slot["rain"] += nxt.get("details", {}).get("precipitation_amount", 0) or 0
    days = [
        {"date": k, "rain": round(v["rain"], 1), "max": round(v["max"], 1)}
        for k, v in per_day.items() if v["max"] is not None
    ][:7]
    return {
        "temperature": first.get("air_temperature"),
        "humidity": first.get("relative_humidity"),
        "days": days,
        "source": "MET Norway",
    }


def _met_no(lat, lon):
    r = requests.get(
        "https://api.met.no/weatherapi/locationforecast/2.0/compact",
        params={"lat": round(lat, 4), "lon": round(lon, 4)},
        headers=UA, timeout=6,
    )
    r.raise_for_status()
    return _parse_met_no(r.json(), lon)


def _wttr(lat, lon):
    r = requests.get(f"https://wttr.in/{round(lat, 3)},{round(lon, 3)}", params={"format": "j1"}, headers=UA, timeout=7)
    r.raise_for_status()
    j = r.json()
    cur = j["current_condition"][0]
    days = []
    for d in j["weather"]:
        rain = sum(float(h.get("precipMM", 0) or 0) for h in d.get("hourly", []))
        days.append({"date": d["date"], "rain": round(rain, 1), "max": float(d["maxtempC"])})
    return {
        "temperature": float(cur["temp_C"]),
        "humidity": float(cur["humidity"]),
        "days": days,
        "source": "wttr.in",
    }


# 7timer rain classes (mm per hour) -> midpoint used for estimating daily rain
_SEVEN_RAIN = {0: 0.0, 1: 0.1, 2: 0.6, 3: 2.5, 4: 7.0, 5: 13.0, 6: 23.0, 7: 40.0, 8: 62.0, 9: 80.0}


def _parse_seven_timer(j, lon):
    init = datetime.strptime(str(j["init"]), "%Y%m%d%H").replace(tzinfo=timezone.utc)
    offset = timedelta(hours=round(lon / 15.0))
    per_day = OrderedDict()
    first = j["dataseries"][0]
    for e in j["dataseries"]:
        t = init + timedelta(hours=e["timepoint"]) + offset
        slot = per_day.setdefault(t.strftime("%Y-%m-%d"), {"rain": 0.0, "max": None})
        slot["rain"] += _SEVEN_RAIN.get(int(e.get("prec_amount", 0)), 0.0) * 3  # 3-hour blocks
        temp = e.get("temp2m")
        if temp is not None and (slot["max"] is None or temp > slot["max"]):
            slot["max"] = temp
    days = [{"date": k, "rain": round(v["rain"], 1), "max": v["max"]} for k, v in per_day.items() if v["max"] is not None][:7]
    hum = str(first.get("rh2m", "")).replace("%", "")
    return {
        "temperature": first.get("temp2m"),
        "humidity": float(hum) if hum.lstrip("-").isdigit() else None,
        "days": days,
        "source": "7timer",
    }


def _seven_timer(lat, lon):
    r = requests.get(
        "https://www.7timer.info/bin/api.pl",
        params={"lon": round(lon, 3), "lat": round(lat, 3), "product": "civil", "output": "json"},
        headers=UA, timeout=8,
    )
    r.raise_for_status()
    return _parse_seven_timer(r.json(), lon)


@router.get("/weather")
def weather(lat: float, lon: float):
    errors = []
    for fn in (_open_meteo, _met_no, _wttr, _seven_timer):
        try:
            out = fn(lat, lon)
            if out["days"] and out["temperature"] is not None and out["humidity"] is not None:
                return out
            errors.append(f"{fn.__name__}: empty data")
        except Exception as e:  # network block, timeout, bad JSON ...
            errors.append(f"{fn.__name__}: {type(e).__name__}")
    raise HTTPException(
        status_code=502,
        detail="Weather services could not be reached from the server (" + "; ".join(errors) + ").",
    )