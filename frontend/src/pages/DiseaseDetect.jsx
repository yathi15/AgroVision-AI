import { useState } from "react";
import axios from "axios";
import ImageUpload from "../components/ImageUpload";
import { API } from "../api";

const box = { border: "1px solid #ccc", padding: 10, borderRadius: 6 };

const List = ({ items }) => (
  <ul>{(items || []).map((t) => <li key={t}>{t}</li>)}</ul>
);

export default function DiseaseDetect() {
  const [file, setFile] = useState(null);
  const [crop, setCrop] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const detect = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("crop", crop);
      const res = await axios.post(`${API}/detect-disease`, form);
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  return (
    <div className="module-page">
      <header className="module-heading">
        <span className="module-kicker">02 · Protect your crops</span>
        <h1>Leaf health check</h1>
        <p>Upload a clear leaf photo for a quick disease assessment, severity check and treatment guidance.</p>
      </header>
      <ImageUpload onSelect={setFile} label="Upload a clear photo of the affected leaf" />
      <input placeholder="Crop name (optional, e.g. tomato)" value={crop}
        onChange={(e) => setCrop(e.target.value)} />
      <button className="module-primary" onClick={detect} disabled={!file || loading}>
        {loading ? "Analyzing..." : "Detect disease"}
      </button>
      {error && <p className="module-error" role="alert">{error}</p>}

      {result && !result.is_plant_leaf && (
        <div className="module-results" style={box}><p>This does not look like a plant leaf. {result.effect_on_crop}</p></div>
      )}

      {result && result.is_plant_leaf && (
        <div className="module-results" style={{ textAlign: "left", display: "grid", gap: 10 }}>
          <div style={{ ...box, background: result.disease === "Healthy" ? "#eaf7ea" : "#fdecea" }}>
            <h3>{result.crop}: {result.disease}</h3>
            <div>Severity: {result.severity} · Confidence: {result.confidence}</div>
            <div>Cause: {result.cause}</div>
          </div>

          <h3>Symptoms</h3>
          <List items={result.symptoms} />

          <h3>Effect on the crop</h3>
          <p>{result.effect_on_crop}</p>
          <p>Possible yield loss if untreated: {result.yield_loss_estimate}</p>

          <h3>Precautions now</h3>
          <List items={result.precautions} />

          <h3>How to prevent it</h3>
          <List items={result.prevention} />

          <h3>Organic treatment</h3>
          <List items={result.organic_treatment} />

          <h3>Chemical treatment (if needed)</h3>
          {(result.chemical_treatment || []).map((c) => (
            <div key={c.name} style={box}>
              <b>{c.name}</b>
              <div>Dose: {c.dose}</div>
              <div>{c.note}</div>
            </div>
          ))}
          <p style={{ fontSize: 13 }}>
            Doses are typical label values. Always follow the product label and confirm
            with a local agriculture officer before spraying.
          </p>

          <h3>When to see an expert</h3>
          <p>{result.when_to_see_expert}</p>
        </div>
      )}
    </div>
  );
}