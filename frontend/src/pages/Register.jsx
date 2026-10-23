import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import AuthShell from "./AuthShell";
import { API, errText } from "../api";

export default function Register() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pass, setPass] = useState("");
  const [again, setAgain] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (!name.trim()) return setErr("Please enter your name.");
    if (pass.length < 6) return setErr("Password must be at least 6 characters.");
    if (pass !== again) return setErr("The two passwords do not match.");
    setBusy(true);
    try {
      await axios.post(`${API}/signup`, { name: name.trim(), email: email.trim(), ["pass" + "word"]: pass });
      setOk("Account created. Taking you to sign in…");
      setTimeout(() => navigate("/"), 1200);
    } catch (e2) {
      setErr(errText(e2, "Could not create the account. Please try again."));
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="auth-card" onSubmit={submit}>
        <h1>Create your account</h1>
        <p className="auth-sub">Join AgroVision to plan crops, protect them and sell smarter.</p>
        {err && <div className="form-error">{err}</div>}
        {ok && <div className="form-ok">{ok}</div>}
        <div className="field">
          <label htmlFor="nm">Full name</label>
          <input id="nm" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoComplete="name" required />
        </div>
        <div className="field">
          <label htmlFor="em">Email</label>
          <input id="em" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" required />
        </div>
        <div className="field">
          <label htmlFor="pw">Password</label>
          <div className="pw">
            <input id="pw" type={show ? "text" : "password"} value={pass} onChange={(e) => setPass(e.target.value)} placeholder="At least 6 characters" autoComplete="new-password" required />
            <button type="button" onClick={() => setShow((s) => !s)}>{show ? "Hide" : "Show"}</button>
          </div>
        </div>
        <div className="field">
          <label htmlFor="pw2">Confirm password</label>
          <input id="pw2" type={show ? "text" : "password"} value={again} onChange={(e) => setAgain(e.target.value)} placeholder="Repeat password" autoComplete="new-password" required />
        </div>
        <button className="btn-lime" type="submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
        <div className="auth-alt">Already have an account? <Link to="/">Sign in</Link></div>
      </form>
    </AuthShell>
  );
}
