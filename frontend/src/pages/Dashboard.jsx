import { Link } from "react-router-dom";
import { Sprout, Leaf, Wheat, Trend, Chat, Grid, Bars, Globe } from "../components/Icons";

const ACTIONS = [
  { to: "/land", Icon: Sprout, tone: "land", tag: "Plan", title: "Land Analysis", text: "Upload a photo of your land. Get suitable crops, a low-cost plan and an organic plan.", go: "Analyse my land" },
  { to: "/disease", Icon: Leaf, tone: "disease", tag: "Protect", title: "Disease Detect", text: "Photograph a sick leaf to find the disease, how serious it is, and how to treat it.", go: "Check a leaf" },
  { to: "/harvest", Icon: Wheat, tone: "harvest", tag: "Harvest", title: "Harvest", text: "Know if your crop is ready, its quality grade, and the best days to harvest.", go: "Plan my harvest" },
  { to: "/marketing", Icon: Trend, tone: "market", tag: "Sell", title: "Marketing", text: "Type any crop, state and district. Find out whether to sell now or store it.", go: "Get price advice" },
];

const STEPS = [
  { n: 1, title: "Add your details", text: "Upload a photo of your land, leaf or crop, or type the crop, state and district." },
  { n: 2, title: "AI analyses it", text: "Vision AI reads the image. The market engine compares old and current mandi prices." },
  { n: 3, title: "Get clear advice", text: "See what to grow, how to treat a disease, when to harvest, and whether to sell or store." },
];

const TIPS = [
  ["Rabi (harvest time)", "Wheat, gram and mustard are ripening. Harvest on dry days and dry the grain well before storing."],
  ["Rabi to Zaid", "Good time for watermelon, cucumber and fodder crops. Irrigate in the morning."],
  ["Zaid", "Summer vegetables and moong do well. Mulch the soil to save water."],
  ["Zaid", "Protect crops from heat. Prepare land, test soil and arrange seed for kharif."],
  ["Pre-kharif", "Prepare fields, add compost and check seed quality before the monsoon."],
  ["Kharif sowing", "Paddy, maize, cotton, groundnut and pulses can be sown with the first good rain."],
  ["Kharif", "Weed, top-dress fertilizer and watch for pests after heavy rain."],
  ["Kharif", "Keep drainage clear. Watch for leaf diseases in humid weather."],
  ["Kharif harvest", "Early paddy and maize are maturing. Check readiness before harvesting."],
  ["Kharif harvest, Rabi sowing", "Harvest kharif crops and sow wheat, gram and mustard when the soil is cool."],
  ["Rabi", "Irrigate rabi crops on time. Watch for frost damage and fungal disease."],
  ["Rabi", "Top-dress wheat and watch for rust. Plan storage for the coming harvest."],
];

export default function Dashboard() {
  const name = localStorage.getItem("name") || "Farmer";
  const tip = TIPS[new Date().getMonth()];
  const openChat = () => window.dispatchEvent(new Event("agro-open-chat"));

  return (
    <div className="wrap">
      <section className="hero">
        <div className="chip-live"><i /> Welcome back, {name}</div>
        <h1 className="hero-title">AGRO<em>VISION</em></h1>
        <p className="hero-lead">
          Image-based crop planning, disease diagnosis and market advice, built to help farmers decide with confidence.
        </p>
        <div className="hero-actions">
          <a className="btn-lime" href="#modules">Explore tools <span>→</span></a>
          <button className="btn-ghost" onClick={openChat}><Chat /> Ask the assistant</button>
        </div>
        <div className="hero-stats">
          <div className="stat"><i className="stat-ico"><Grid /></i><div><b>4</b><span>AI modules</span></div></div>
          <div className="stat"><i className="stat-ico"><Bars /></i><div><b>6+ yrs</b><span>Mandi price history</span></div></div>
          <div className="stat"><i className="stat-ico"><Globe /></i><div><b>3</b><span>Chat languages</span></div></div>
        </div>
      </section>

      <nav className="quick" aria-label="Quick access">
        {ACTIONS.map(({ to, Icon, title, tone }) => (
          <Link key={to} to={to} className="quick-item">
            <span className={`quick-ico quick-ico--${tone}`}><Icon /></span>
            <span>{title}</span>
          </Link>
        ))}
        <button className="quick-item" onClick={openChat}>
          <span className="quick-ico"><Chat /></span>
          <span>Ask AgroVision</span>
        </button>
      </nav>

      <div className="strip">
        <span>Powered by</span><b>Vision AI</b><b>Agmarknet mandi data</b><b>Seasonal price models</b>
      </div>

      <section className="section" id="modules">
        <div className="eyebrow-c">Our tools</div>
        <h2 className="big">Smart tools for <em>every stage</em> of farming</h2>
        <p className="section-sub">From choosing what to grow to deciding when to sell, everything in one place.</p>
        <div className="grid-actions">
          {ACTIONS.map(({ to, Icon, tone, tag, title, text, go }) => (
            <Link key={to} to={to} className="action-card">
              <div className="action-tag">{tag}</div>
              <div className={`action-ico action-ico--${tone}`}><Icon /></div>
              <h3>{title}</h3>
              <p>{text}</p>
              <div className="action-go"><span>{go}</span><span className="action-arrow">→</span></div>
            </Link>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="eyebrow-c">How it works</div>
        <h2 className="big">Three simple <em>steps</em></h2>
        <p className="section-sub">No technical knowledge needed.</p>
        <div className="steps">
          {STEPS.map((s) => (
            <div key={s.n} className="step">
              <div className="step-n">{s.n}</div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </div>
          ))}
        </div>

        <div className="info-row">
          <div className="glass">
            <div className="eyebrow">This month</div>
            <h3>{tip[0]}</h3>
            <p>{tip[1]}</p>
            <p style={{ fontSize: 12, marginBottom: 0 }}>General guidance for India. Check local conditions before acting.</p>
          </div>
          <div className="glass">
            <div className="eyebrow">Assistant</div>
            <h3>Ask AgroVision anything</h3>
            <p>Chat in English, Hindi or Kannada about crops, storage, diseases and schemes.</p>
            <ul>
              <li>Which fertilizer for my crop?</li>
              <li>How do I store grain safely?</li>
              <li>Which government schemes can I use?</li>
            </ul>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-in">
          <span>AgroVision AI · Image-based crop planning, disease diagnosis and market advisory</span>
          <span>Price advice is an estimate, not a guarantee.</span>
        </div>
      </footer>
    </div>
  );
}
