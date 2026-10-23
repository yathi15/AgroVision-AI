import { NavLink } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import "./Navbar.css";

const NAV = [
  { to: "/dashboard", ico: "🏠", label: "Dashboard" },
  { to: "/land", ico: "🌱", label: "Land Analysis" },
  { to: "/disease", ico: "🍃", label: "Disease Detect" },
  { to: "/harvest", ico: "🌾", label: "Harvest" },
  { to: "/marketing", ico: "📈", label: "Marketing" },
];

function Brand() {
  return (
    <div className="an-brand">
      <div className="an-logo">🌾</div>
      <div>
        <h1>AgroVision AI</h1>
        <span>Smart farming advisor</span>
      </div>
    </div>
  );
}

export default function Navbar({ loggedIn, name, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // close the dropdown when clicking outside
  useEffect(() => {
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  if (!loggedIn) {
    return (
      <header className="an-header">
        <div className="an-inner">
          <Brand />
          <div className="an-auth-links">
            <NavLink to="/" end className={({ isActive }) => "an-link" + (isActive ? " an-active" : "")}>Login</NavLink>
            <NavLink to="/register" className={({ isActive }) => "an-link" + (isActive ? " an-active" : "")}>Register</NavLink>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="an-header">
      <div className="an-inner">
        <Brand />

        <nav className="an-links">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) => "an-link" + (isActive ? " an-active" : "")}
            >
              <span>{n.ico}</span> {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="an-user" ref={ref}>
          <button className="an-avatar" onClick={() => setOpen(!open)} aria-label="Account menu">
            {(name || "F").charAt(0).toUpperCase()}
          </button>
          {open && (
            <div className="an-menu">
              <p>Signed in as</p>
              <strong>{name}</strong>
              <button onClick={onLogout}>Logout</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}