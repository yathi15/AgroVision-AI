import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../api";

const VERDICT = {
  COST_ONLY:  { label: "Sell now (cost-based)", icon: "▲", color: "#8a5a00", bg: "#fff4d6" },
  SELL_NOW:    { label: "Sell now",             icon: "▲", color: "#b3261e", bg: "#fdecea" },
  HOLD_DAYS:   { label: "Hold for a few days",  icon: "●", color: "#8a5a00", bg: "#fff4d6" },
  HOLD_WEEKS:  { label: "Hold for weeks",       icon: "●", color: "#8a5a00", bg: "#fff4d6" },
  HOLD_MONTHS: { label: "Hold for months",      icon: "■", color: "#1b6b3a", bg: "#e4f4ea" },
};
const rs = (n) => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });

function PriceChart({ data }) {
  const [hover, setHover] = useState(null);
  const W = 720, H = 240, P = { l: 52, r: 16, t: 14, b: 28 };
  const vals = data.map((d) => d.price);
  const lo = Math.min(...vals) * 0.95, hi = Math.max(...vals) * 1.05;
  const x = (i) => P.l + (i * (W - P.l - P.r)) / (data.length - 1);
  const y = (v) => P.t + ((hi - v) * (H - P.t - P.b)) / (hi - lo);
  const path = data.map((d, i) => `${i ? "L" : "M"}${x(i)},${y(d.price)}`).join(" ");
  const ticks = [0, 1, 2, 3].map((k) => lo + ((hi - lo) * k) / 3);
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    setHover(Math.max(0, Math.min(data.length - 1, Math.round(((px - P.l) / (W - P.l - P.r)) * (data.length - 1)))));
  };

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }} onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={P.l} x2={W - P.r} y1={y(t)} y2={y(t)} stroke="#e3e8e2" />
          <text x={P.l - 8} y={y(t) + 4} fontSize="11" textAnchor="end" fill="#5b665d">{Math.round(t)}</text>
        </g>
      ))}
      {data.map((d, i) => i % 6 === 0 && (
        <text key={i} x={x(i)} y={H - 8} fontSize="11" textAnchor="middle" fill="#5b665d">{d.month}</text>
      ))}
      <path d={path} fill="none" stroke="#1b6b3a" strokeWidth="2" strokeLinejoin="round" />
      {hover !== null && (
        <g>
          <line x1={x(hover)} x2={x(hover)} y1={P.t} y2={H - P.b} stroke="#9aa59c" />
          <circle cx={x(hover)} cy={y(data[hover].price)} r="4.5" fill="#1b6b3a" stroke="#fff" strokeWidth="2" />
          <rect x={Math.min(x(hover) + 8, W - 130)} y={P.t} width="122" height="38" rx="6" fill="#16241a" />
          <text x={Math.min(x(hover) + 16, W - 122)} y={P.t + 16} fontSize="11" fill="#cfe0d3">{data[hover].month}</text>
          <text x={Math.min(x(hover) + 16, W - 122)} y={P.t + 31} fontSize="13" fontWeight="600" fill="#fff">{rs(data[hover].price)} / quintal</text>
        </g>
      )}
    </svg>
  );
}

export default function Marketing() {
  const [crops, setCrops] = useState([]);
  const [states, setStates] = useState([]);
  const [district, setDistrict] = useState("");
  const [crop, setCrop] = useState("");
  const [state, setState] = useState("");
  const [qty, setQty] = useState(10);
  const [price, setPrice] = useState("");
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const token = localStorage.getItem("token");
  const auth = token ? { headers: { Authorization: "Bearer " + token } } : {};

  useEffect(() => {
    const requestAuth = token ? { headers: { Authorization: "Bearer " + token } } : {};
    axios.get(`${API}/market-meta`, { ...requestAuth, timeout: 20000 })
      .then((r) => {
        setCrops(r.data.crops);
        setStates(r.data.states);
      })
      .catch((e) => setErr(e.response?.data?.detail?.message || e.response?.data?.detail || e.message || "Could not load the crop and state lists."));
  }, [token]);

  const run = async () => {
    if (!crop) return setErr("Type a crop first.");
    if (!state) return setErr("Choose a state first.");
    setBusy(true);
    setErr("");
    setRes(null);

    try {
      const r = await axios.get(`${API}/market-advice`, {
        ...auth,
        timeout: 75000,
        params: { crop, state, district, quantity: qty, price: price || 0 },
      });
      setRes(r.data);
    } catch (e) {
      setErr(e.response?.data?.detail?.message || e.response?.data?.detail || e.message || "Could not get market advice. Check that the backend is running.");
    }

    setBusy(false);
  };

  const v = res && (res.history_available === false ? VERDICT.COST_ONLY : VERDICT[res.action]);
  const card = { background: "#fff", border: "1px solid #dfe5de", borderRadius: 10, padding: 20, marginBottom: 16 };
  const input = { padding: "10px 12px", border: "1px solid #c9d2c8", borderRadius: 8, fontSize: 15, width: "100%", boxSizing: "border-box", color: "#16241a", background: "#fff", WebkitTextFillColor: "#16241a" };

  return (
    <div className="module-page module-page--marketing">
      <header className="module-heading">
        <span className="module-kicker">04 · Make the right sale</span>
        <h1>Market advisory</h1>
        <p>Compare reported mandi prices and seasonal trends to decide whether to sell now or store. Reports can be delayed; forecasts are estimates, not guarantees.</p>
      </header>

      <div style={{ ...card, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12, alignItems: "end" }}>
        <label>Crop<input style={input} list="crops" value={crop} onChange={(e) => setCrop(e.target.value)} placeholder="Type any crop, e.g. Onion" /></label>
        <datalist id="crops">{crops.map((c) => <option key={c} value={c} />)}</datalist>
        <label>State<select style={input} value={state} onChange={(e) => { setState(e.target.value); setDistrict(""); }}>
          <option value="">Choose state</option>
          {states.map((s) => <option key={s.name} value={s.name}>{s.name}</option>)}
        </select></label>
        <label>District (optional)<select style={input} value={district} onChange={(e) => setDistrict(e.target.value)} disabled={!state}>
          <option value="">Whole state</option>
          {(states.find((s) => s.name === state)?.districts || []).map((d) => <option key={d} value={d}>{d}</option>)}
        </select></label>
        <label>Quantity (quintals)<input style={input} type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} /></label>
        <label>Price override, ₹/quintal (optional)<input style={input} type="number" min="0" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Live reported price used by default" /></label>
        <button className="module-primary" onClick={run} disabled={busy} style={{ padding: "11px 18px", background: "#1b6b3a", color: "#fff", border: 0, borderRadius: 8, fontSize: 15, cursor: "pointer" }}>
          {busy ? "Analysing…" : "Get advice"}
        </button>
      </div>
      {err && <div role="alert" style={{ ...card, borderColor: "#b3261e", color: "#b3261e" }}>{err}</div>}

      {res && (
        <>
          <h2 style={{ margin: "0 0 12px", fontSize: 20 }}>{res.crop} · {res.district ? res.district + ", " : ""}{res.state}</h2>
          {res.note && (
            <div style={{ ...card, padding: "12px 16px", background: "#eef3ff", borderColor: "#6b7fd7" }}>
              <strong>{res.history_available === false ? "Basis for this recommendation" : "Market data note"}</strong>
              <p style={{ margin: "4px 0 0", lineHeight: 1.5 }}>{res.note}</p>
            </div>
          )}
          {res.stale && res.price_source === "history" && (
            <div role="alert" style={{ ...card, background: "#fff4d6", borderColor: "#8a5a00" }}>
              ▲ The latest price on record is from {res.history_last_date} ({res.data_age_days} days ago). Type today's price from your mandi in the box above and press Get advice again for a reliable answer.
            </div>
          )}
          <div style={{ ...card, background: v.bg, borderColor: v.color }}>
            <div style={{ display: "flex", gap: 12, alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ color: v.color, fontSize: 26, fontWeight: 700 }}>{v.icon} {v.label}</span>
              {res.history_available !== false && res.action !== "SELL_NOW" && <span style={{ fontWeight: 600 }}>Best plan: {res.best.label}</span>}
            </div>
            <p style={{ margin: "10px 0 0", lineHeight: 1.5 }}>{res.reason}</p>
            <div style={{ display: "flex", gap: 28, flexWrap: "wrap", marginTop: 14 }}>
              <div><div style={{ fontSize: 12, color: "#5b665d" }}>Price used ({res.price_source === "live" ? "latest mandi report" : res.price_source === "entered" ? "your override" : "latest on record"})</div><div style={{ fontSize: 22, fontWeight: 700 }}>{rs(res.current_price)}<span style={{ fontSize: 13, fontWeight: 400 }}> /quintal</span></div>{res.live?.date && <div style={{ fontSize: 12, color: "#5b665d" }}>Reported {res.live.date}{res.live.markets ? ` · ${res.live.markets} record(s)` : ""}</div>}</div>
              {res.action !== "SELL_NOW" && <div><div style={{ fontSize: 12, color: "#5b665d" }}>Extra income if you wait ({res.quantity} q)</div><div style={{ fontSize: 22, fontWeight: 700 }}>{rs(res.best.total_gain)}</div></div>}
              <div><div style={{ fontSize: 12, color: "#5b665d" }}>Confidence</div><div style={{ fontSize: 22, fontWeight: 700 }}>{res.confidence}</div></div>
              <div><div style={{ fontSize: 12, color: "#5b665d" }}>Vs last 3 years</div><div style={{ fontSize: 22, fontWeight: 700 }}>{res.history_available === false ? "Not available" : `Higher than ${res.percentile_3y}%`}</div></div>
            </div>
          </div>

          <div style={{ ...card, borderLeft: "5px solid #1b6b3a" }}>
            <h2 style={{ margin: "0 0 10px", fontSize: 20 }}>Advice in plain words</h2>
            <p style={{ margin: "0 0 10px", lineHeight: 1.6 }}>
              {res.history_available === false
                ? `Based on your entered offer of ${rs(res.current_price)} per quintal, selling now is the better choice under the flat-price assumption. Holding would add estimated storage, spoilage and interest costs without a verified price increase to offset them.`
                : res.action === "SELL_NOW"
                  ? "The estimate says selling now is the better option because waiting is not expected to cover storage, spoilage and interest costs."
                  : `The estimate suggests holding for ${res.best.label.toLowerCase()}, after accounting for estimated storage, spoilage and interest costs.`}
            </p>
            <p style={{ margin: "0 0 10px", lineHeight: 1.6 }}>
              {res.price_source === "entered"
                ? `This comparison uses the price you entered (${rs(res.current_price)} per quintal) as today's offer.`
                : `This comparison uses ${rs(res.current_price)} per quintal from ${res.price_source === "live" ? "a live mandi price" : "the latest price record on file"}.`}
              {res.stale && res.price_source === "history" ? ` That record is from ${res.history_last_date}, so the price may no longer reflect today's market.` : ""}
            </p>
            <p style={{ margin: 0, lineHeight: 1.6 }}>
              {res.history_available === false
                ? "Only hold if you can verify locally that a likely price increase will exceed these costs. Compare today's prices at nearby mandis, and check quality, transport and payment terms."
                : res.action === "SELL_NOW"
                  ? "Before deciding, compare the offer with today's prices at nearby mandis and check quality, transport and payment terms."
                  : `If you choose to hold, use suitable storage and recheck the local mandi price before ${res.best.label.toLowerCase()} ends.`}
              {" "}{res.history_available === false ? "This is not a market-price prediction." : "This is a historical estimate, not a guaranteed price or a substitute for checking the local mandi."}
            </p>
          </div>

          <div style={card}>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>{res.history_available === false ? "Price history" : "Monthly average price, last 3 years (₹ per quintal)"}</h2>
            {res.history_available === false
              ? <p style={{ margin: 0, lineHeight: 1.5 }}>A price chart and market trend are not shown because verified historical prices for this crop and location were unavailable.</p>
              : <>
                <PriceChart data={res.chart} />
                <p style={{ fontSize: 13, color: "#5b665d", margin: "6px 0 0" }}>Trend over the last 3 months: {res.trend_pct_per_month}% per month. Based on {res.records} records over {res.years_of_data} years; latest record {res.history_last_date}.</p>
              </>}
          </div>

          <div style={card}>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>If you wait: what you keep per quintal</h2>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead><tr style={{ textAlign: "right", color: "#5b665d" }}>
                  <th style={{ textAlign: "left", padding: 8 }}>Option</th><th>Expected price</th><th>Storage</th><th>Spoilage</th><th>Interest</th><th>You keep</th><th>Change</th>
                </tr></thead>
                <tbody>{res.scenarios.map((s) => (
                  <tr key={s.label} style={{ textAlign: "right", borderTop: "1px solid #e8ece7", fontWeight: s.label === res.best.label ? 700 : 400, background: s.label === res.best.label ? v.bg : "transparent" }}>
                    <td style={{ textAlign: "left", padding: 8 }}>{s.label}</td>
                    <td>{rs(s.expected)}</td><td>−{rs(s.storage)}</td><td>−{rs(s.spoilage)}</td><td>−{rs(s.interest)}</td><td>{rs(s.net)}</td>
                    <td style={{ color: s.gain_pct >= 0 ? "#1b6b3a" : "#b3261e" }}>{s.gain_pct >= 0 ? "▲" : "▼"} {Math.abs(s.gain_pct)}%</td>
                  </tr>))}</tbody>
              </table>
            </div>
          </div>

          {res.action !== "SELL_NOW" && (
            <div style={card}>
              <h2 style={{ marginTop: 0, fontSize: 18 }}>How to store it</h2>
              <p style={{ margin: 0, lineHeight: 1.5 }}>{res.storage.cond}</p>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#5b665d" }}>Safe storage period for this type of crop: about {res.storage.max_days} days.</p>
            </div>
          )}

          <p style={{ fontSize: 12.5, color: "#5b665d", lineHeight: 1.5 }}>
            Forecasts come from past seasonal patterns and recent trend; they are estimates, not guarantees. Storage cost, spoilage and interest use typical values for the crop type. {res.msp_note} History: CEDA Agri-Market Data (Agmarknet), latest record {res.history_last_date}. Today’s price: {res.price_source === "live" ? "Agmarknet via data.gov.in" : res.price_source === "entered" ? "entered by the farmer" : "last record on file"}.
          </p>
        </>
      )}
    </div>
  );
}
