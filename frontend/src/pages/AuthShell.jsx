import { Logo } from "../components/Icons";

export default function AuthShell({ children }) {
  return (
    <div className="auth-page">
      <aside className="auth-art">
        <div className="brand">
          <span className="brand-logo"><Logo /></span>
          <span className="brand-name">AGRO<span>VISION</span> AI</span>
        </div>
        <div>
          <h2>Smarter decisions for <em>every season</em>.</h2>
          <ul>
            <li><i>✓</i> Find the right crop for your land from a single photo</li>
            <li><i>✓</i> Spot leaf diseases early and get treatment steps</li>
            <li><i>✓</i> Know when to sell your crop and when to store it</li>
          </ul>
        </div>
        <small style={{ color: "#9db8a5" }}>Image-based crop planning, disease diagnosis and market advisory</small>
      </aside>
      <main className="auth-side">{children}</main>
    </div>
  );
}
