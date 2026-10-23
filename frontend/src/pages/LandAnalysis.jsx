import { useState } from "react";
import axios from "axios";
import ImageUpload from "../components/ImageUpload";
import { API } from "../api";

const box = { border: "1px solid #ccc", padding: 10, borderRadius: 6 };

export default function LandAnalysis() {
  const [file, setFile] = useState(null);
  const [weather, setWeather] = useState({ temperature: "", humidity: "", rainfall: "" });
  const [acres, setAcres] = useState(1);
  const [place, setPlace] = useState("");
  const [matches, setMatches] = useState([]);
  const [locationName, setLocationName] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchWeather = async (lat, lon) => {
    setWeatherLoading(true);
    try {
      const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m&daily=precipitation_sum&past_days=30&forecast_days=1`;
      const res = await axios.get(url);
      const rain = res.data.daily.precipitation_sum.reduce((a, b) => a + (b || 0), 0);
      setWeather({
        temperature: res.data.current.temperature_2m,
        humidity: res.data.current.relative_humidity_2m,
        rainfall: Math.round(rain),
      });
    } catch {
      setError("Could not fetch weather. Type the values by hand.");
    }
    setWeatherLoading(false);
  };

  const useLiveLocation = () => {
    setError("");
    setMatches([]);
    if (!navigator.geolocation) {
      return setError("Your browser does not support location. Search a place instead.");
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setLocationName("My current location");
        await fetchWeather(pos.coords.latitude, pos.coords.longitude);
      },
      () => setError("Location blocked. Search a place or type the values by hand.")
    );
  };

  const searchPlace = async () => {
    setError("");
    setMatches([]);
    try {
      const res = await axios.get(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(place.trim())}&count=6&language=en`
      );
      const list = res.data.results || [];
      if (!list.length) {
        return setError("Place not found. Check the spelling (e.g. Bengaluru) and search just the city name.");
      }
      setMatches(list);
    } catch {
      setError("Could not search for that place.");
    }
  };

  const pickMatch = async (p) => {
    setMatches([]);
    setLocationName([p.name, p.admin1, p.country].filter(Boolean).join(", "));
    await fetchWeather(p.latitude, p.longitude);
  };

  const analyze = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("temperature", weather.temperature);
      form.append("humidity", weather.humidity || 60);
      form.append("rainfall", weather.rainfall);
      form.append("acres", acres);
      form.append("location", locationName);
      form.append("month", new Date().toLocaleString("en-US", { month: "long" }));
      const res = await axios.post(`${API}/analyze-land`, form, {
        headers: { Authorization: "Bearer " + localStorage.getItem("token") },
      });
      setResult(res.data);
    } catch (e) {
      setError(
        e.code === "ECONNABORTED"
          ? "Analysis timed out. Please try again."
          : e.response?.data?.detail || e.message
      );
    } finally {
      setLoading(false);
    }
  };

  const ready =
    file &&
    weather.temperature !== "" &&
    weather.rainfall !== "" &&
    Number(acres) > 0;

  return (
    <div className="module-page">
      <header className="module-heading">
        <span className="module-kicker">01 · Plan your fields</span>
        <h1>Land analysis</h1>
        <p>Discover crops that fit your soil, local weather and farm size, with practical plans to get started.</p>
      </header>

      <ImageUpload onSelect={setFile} label="Upload a photo of your land" />

      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={{ flex: 1 }}
          placeholder="Search any place (e.g. Bengaluru, Mysuru, Pune)"
          value={place}
          onChange={(e) => setPlace(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && place.trim() && searchPlace()}
        />
        <button onClick={searchPlace} disabled={!place.trim()}>Search</button>
      </div>

      {matches.map((p) => (
        <button key={p.id} onClick={() => pickMatch(p)} style={{ textAlign: "left" }}>
          {[p.name, p.admin1, p.country].filter(Boolean).join(", ")}
        </button>
      ))}

      <button onClick={useLiveLocation}>Or use my live location</button>

      {weatherLoading && <p>Fetching weather...</p>}
      {locationName && <p>Location: <b>{locationName}</b></p>}

      <input type="number" placeholder="Temperature (°C)" value={weather.temperature}
        onChange={(e) => setWeather({ ...weather, temperature: e.target.value })} />
      <input type="number" placeholder="Humidity (%)" value={weather.humidity}
        onChange={(e) => setWeather({ ...weather, humidity: e.target.value })} />
      <input type="number" placeholder="Rainfall, last 30 days (mm)" value={weather.rainfall}
        onChange={(e) => setWeather({ ...weather, rainfall: e.target.value })} />
      <input type="number" placeholder="Land size (acres)" value={acres}
        onChange={(e) => setAcres(e.target.value)} />

      <button className="module-primary" onClick={analyze} disabled={!ready || loading}>
        {loading ? "Analyzing..." : "Analyze land"}
      </button>
      {error && <p className="module-error" role="alert">{error}</p>}

      {result && (
        <div className="module-results" style={{ textAlign: "left", display: "grid", gap: 10 }}>
          <div style={box}>
            <h3>Soil: {result.soil_type} · Season: {result.season}</h3>
            <p>{result.soil_condition}</p>
          </div>

          <h3>Recommended crops</h3>
          {result.recommended_crops.map((c) => (
            <div key={c.crop} style={box}>
              <b>{c.crop}</b> ({c.suitability} suitability)
              <div>{c.reason}</div>
              <div>Cost per acre: ₹{c.estimated_cost_per_acre_inr}</div>
              <div>Water need: {c.water_need} · Duration: {c.duration_days} days</div>
            </div>
          ))}

          <div style={{ ...box, background: "#eaf7ea" }}>
            <b>Lowest-cost pick: {result.best_low_cost_pick.crop}</b>
            <div>{result.best_low_cost_pick.why}</div>
          </div>

          <h3>Organic plan</h3>
          <div style={box}>
            <b>Fertilizers</b>
            <ul>{result.organic_plan.fertilizers.map((t) => <li key={t}>{t}</li>)}</ul>
            <b>Pest control</b>
            <ul>{result.organic_plan.pest_control.map((t) => <li key={t}>{t}</li>)}</ul>
            <b>Soil improvement</b>
            <ul>{result.organic_plan.soil_improvement.map((t) => <li key={t}>{t}</li>)}</ul>
          </div>

          <h3>Use fewer chemicals</h3>
          <ul>{result.chemical_reduction.map((t) => <li key={t}>{t}</li>)}</ul>

          <h3>Cost-saving tips</h3>
          <ul>{result.cost_saving_tips.map((t) => <li key={t}>{t}</li>)}</ul>

          <h3>Avoid</h3>
          <p>{result.avoid_crops.join(", ")}</p>
        </div>
      )}
    </div>
  );
}