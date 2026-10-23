import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import AuthShell from "./AuthShell";
import { API, errText } from "../api";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const r = await axios.post(`${API}/login`, { email: email.trim(), ["pass" + "word"]: pass });
      localStorage.setItem("token", r.data.token);
      localStorage.setItem("name", r.data.name);
      navigate("/dashboard");
    } catch (e2) {
      setErr(errText(e2, "Could not sign in. Please try again."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="auth-card" onSubmit={submit}>
        <h1>Welcome back</h1>
        <p className="auth-sub">Sign in to continue to your farm dashboard.</p>
        {err && <div className="form-error">{err}</div>}
        <div className="field">
          <label htmlFor="em">Email</label>
          <input id="em" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" required />
        </div>
        <div className="field">
          <label htmlFor="pw">Password</label>
          <div className="pw">
            <input id="pw" type={show ? "text" : "password"} value={pass} onChange={(e) => setPass(e.target.value)} placeholder="Your password" autoComplete="current-password" required />
            <button type="button" onClick={() => setShow((s) => !s)}>{show ? "Hide" : "Show"}</button>
          </div>
        </div>
        <button className="btn-lime" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <div className="auth-alt">New to AgroVision? <Link to="/register">Create an account</Link></div>
      </form>
    </AuthShell>
  );
}
