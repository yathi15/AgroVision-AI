import { useState } from "react";
import axios from "axios";
import ImageUpload from "../components/ImageUpload";
import { API } from "../api";

const box = { border: "1px solid #ccc", padding: 10, borderRadius: 6 };

const List = ({ items }) => (
  <ul>{(items || []).map((t) => <li key={t}>{t}</li>)}</ul>
);

export default function Harvest() {
  const [file, setFile] = useState(null);
  const [crop, setCrop] = useState("");
  const [place, setPlace] = useState("");
  const [matches, setMatches] = useState([]);
  const [locationName, setLocationName] = useState("");
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [needManual, setNeedManual] = useState(false);
  const [manual, setManual] = useState({ temp: "", humidity: "", rain: "none" });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchWeather = async (lat, lon) => {
    setWeatherLoading(true);
    setError("");
    setNeedManual(false);
    try {
      // The backend fetches the forecast (works even when the browser is blocked from weather sites)
      const res = await axios.get(`${API}/weather`, { params: { lat, lon }, timeout: 30000 });
      setWeather(res.data);
    } catch {
      setWeather(null);
      setNeedManual(true);
      setError("Live weather is not reachable right now. Enter today's weather below instead.");
    }
    setWeatherLoading(false);
  };

  const applyManual = () => {
    const temp = Number(manual.temp);
    const hum = Number(manual.humidity);
    if (!Number.isFinite(temp) || !Number.isFinite(hum) || manual.temp === "" || manual.humidity === "") {
      return setError("Enter the temperature and humidity.");
    }
    const mm = { none: 0, light: 5, heavy: 30 }[manual.rain];
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() + i);
      return { date: d.toISOString().slice(0, 10), rain: mm, max: temp };
    });
    setError("");
    setWeather({ temperature: temp, humidity: hum, days, source: "entered by you" });
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
      () => setError("Location blocked. Search a place instead.")
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
        return setError("Place not found. Check the spelling and search just the city name.");
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
      const forecast = weather.days
        .map((d) => `${d.date}: rain ${d.rain} mm, max ${d.max} C`)
        .join("; ");
      const form = new FormData();
      form.append("file", file);
      form.append("crop", crop);
      form.append("temperature", weather.temperature);
      form.append("humidity", weather.humidity);
      form.append("forecast", forecast);
      form.append("location", locationName);
      const res = await axios.post(`${API}/analyze-harvest`, form);
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const ready = file && weather;

  return (
    <div className="module-page">
      <header className="module-heading">
        <span className="module-kicker">03 · Harvest with confidence</span>
        <h1>Harvest readiness</h1>
        <p>Check crop maturity alongside your local weather to find a safer harvest window and protect quality.</p>
      </header>

      <ImageUpload onSelect={setFile} label="Upload a photo of your crop" />
      <input
        placeholder="Crop name (optional, e.g. tomato)"
        value={crop}
        onChange={(e) => setCrop(e.target.value)}
      />

      <div style={{ display: "flex", gap: 8 }}>
        <input
          style={{ flex: 1 }}
          placeholder="Search your place (e.g. Mysuru)"
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

      {needManual && !weather && (
        <div style={box}>
          <b>Enter weather manually</b>
          <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
            <input type="number" placeholder="Temperature now (°C)" value={manual.temp}
              onChange={(e) => setManual({ ...manual, temp: e.target.value })} />
            <input type="number" placeholder="Humidity (%)" value={manual.humidity}
              onChange={(e) => setManual({ ...manual, humidity: e.target.value })} />
            <select value={manual.rain} onChange={(e) => setManual({ ...manual, rain: e.target.value })}>
              <option value="none">No rain expected this week</option>
              <option value="light">Light rain expected</option>
              <option value="heavy">Heavy rain expected</option>
            </select>
            <button onClick={applyManual}>Use this weather</button>
          </div>
        </div>
      )}
      {locationName && <p>Location: <b>{locationName}</b></p>}

      {weather && (
        <div style={box}>
          <b>Now: {weather.temperature}°C, humidity {weather.humidity}%</b>
          {weather.source && <div style={{ fontSize: 12, opacity: 0.7 }}>Source: {weather.source}</div>}
          <table border="1" cellPadding="4" style={{ borderCollapse: "collapse", marginTop: 8 }}>
            <thead><tr><th>Date</th><th>Rain (mm)</th><th>Max °C</th></tr></thead>
            <tbody>
              {weather.days.map((d) => (
                <tr key={d.date}><td>{d.date}</td><td>{d.rain}</td><td>{d.max}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <button className="module-primary" onClick={analyze} disabled={!ready || loading}>
        {loading ? "Analyzing..." : "Check harvest"}
      </button>
      {error && <p className="module-error" role="alert">{error}</p>}

      {result && !result.is_crop && (
        <div className="module-results" style={{ ...box, background: "#fff8e1", color: "#1d2a21" }}><p>This does not look like a crop. {result.weather_risk}</p></div>
      )}

      {result && result.is_crop && (
        <div className="module-results" style={{ textAlign: "left", display: "grid", gap: 10 }}>
          <div style={{ ...box, background: result.ready_to_harvest === "yes" ? "#eaf7ea" : "#fff8e1", color: "#1d2a21" }}>
            <h3 style={{ margin: "0 0 8px", color: "#124a28" }}>{result.crop}: ready to harvest? {result.ready_to_harvest}</h3>
            <div>Stage: {result.maturity_stage}</div>
            <div>Days left: {result.days_to_harvest} · Confidence: {result.confidence}</div>
            <div>Quality grade: <b>{result.quality_grade}</b></div>
          </div>

          <h3>Why this grade</h3>
          <List items={result.grade_reasons} />

          <h3>Best harvest days</h3>
          <p>{result.best_harvest_window}</p>

          <h3>Weather risk</h3>
          <p>{result.weather_risk}</p>

          <h3>Harvest tips</h3>
          <List items={result.harvest_tips} />

          <h3>After harvest</h3>
          <List items={result.post_harvest_care} />
        </div>
      )}
    </div>
  );
}