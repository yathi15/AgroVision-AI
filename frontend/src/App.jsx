import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate, useLocation } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import LandAnalysis from "./pages/LandAnalysis";
import DiseaseDetect from "./pages/DiseaseDetect";
import Harvest from "./pages/Harvest";
import Marketing from "./pages/Marketing";
import ProtectedRoute from "./components/ProtectedRoute";
import ChatWidget from "./components/ChatWidget";
import { Logo, Menu, Chevron, SignOut } from "./components/Icons";
import "./theme.css";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/land", label: "Land Analysis" },
  { to: "/disease", label: "Disease Detect" },
  { to: "/harvest", label: "Harvest" },
  { to: "/marketing", label: "Marketing" },
];

function Brand() {
  return (
    <NavLink to="/dashboard" className="brand">
      <span className="brand-logo"><Logo /></span>
      <span className="brand-name">AGRO<span>VISION</span></span>
    </NavLink>
  );
}

function UserMenu({ name, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const initial = (name || "U").trim().charAt(0).toUpperCase();

  useEffect(() => {
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, []);

  return (
    <div className="user" ref={ref}>
      <button className="user-btn" onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open}>
        <span className="avatar">{initial}</span>
        <span className="user-name">Hi, {name}</span>
        <Chevron />
      </button>
      {open && (
        <div className="menu" role="menu">
          <div className="menu-head">
            <span className="avatar big">{initial}</span>
            <div><b>Hi, {name}</b><small>AgroVision member</small></div>
          </div>
          <button className="menu-item" role="menuitem" onClick={onLogout}><SignOut /> Sign out</button>
        </div>
      )}
    </div>
  );
}

function Layout() {
  const location = useLocation(); // re-render on every page change so login state stays fresh
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(false);
  const loggedIn = !!localStorage.getItem("token");
  const name = localStorage.getItem("name") || "Farmer";
  const onDashboard = location.pathname === "/dashboard";

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("name");
    navigate("/");
  };

  const routes = (
    <Routes>
      <Route path="/" element={loggedIn ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/register" element={loggedIn ? <Navigate to="/dashboard" replace /> : <Register />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/land" element={<ProtectedRoute><LandAnalysis /></ProtectedRoute>} />
      <Route path="/disease" element={<ProtectedRoute><DiseaseDetect /></ProtectedRoute>} />
      <Route path="/harvest" element={<ProtectedRoute><Harvest /></ProtectedRoute>} />
      <Route path="/marketing" element={<ProtectedRoute><Marketing /></ProtectedRoute>} />
    </Routes>
  );

  // Logged out: login / register pages are full-screen and draw their own layout.
  if (!loggedIn) return routes;

  return (
    <>
      <header className="topnav">
        <div className="topnav-in">
          <Brand />
          <nav className={`nav${navOpen ? " open" : ""}`}>
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} onClick={() => setNavOpen(false)} className={({ isActive }) => (isActive ? "active" : "")}>{n.label}</NavLink>
            ))}
          </nav>
          <UserMenu name={name} onLogout={logout} />
          <button className="burger" onClick={() => setNavOpen((o) => !o)} aria-label="Toggle menu"><Menu /></button>
        </div>
      </header>
      {onDashboard ? routes : <div className="page-wrap wrap"><div className="paper">{routes}</div></div>}
      <ChatWidget />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout />
    </BrowserRouter>
  );
}
