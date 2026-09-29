import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import LandAnalysis from "./pages/LandAnalysis";
import DiseaseDetect from "./pages/DiseaseDetect";
import HarvestPrice from "./pages/HarvestPrice";

export default function App() {
  return (
    <BrowserRouter>
      <nav style={{ display: "flex", gap: "16px", padding: "12px" }}>
        <Link to="/">Login</Link>
        <Link to="/register">Register</Link>
        <Link to="/land">Land Analysis</Link>
        <Link to="/disease">Disease Detect</Link>
        <Link to="/harvest">Harvest & Price</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/land" element={<LandAnalysis />} />
        <Route path="/disease" element={<DiseaseDetect />} />
        <Route path="/harvest" element={<HarvestPrice />} />
      </Routes>
    </BrowserRouter>
  );
}