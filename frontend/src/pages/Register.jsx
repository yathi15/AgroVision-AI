
import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export default function Register() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    try {
      await axios.post("http://localhost:8000/signup", form);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Signup failed");
    }
  };

  return (
    <form onSubmit={submit} style={{ maxWidth: 320, margin: "40px auto", display: "grid", gap: 10 }}>
      <h2>AgroVision AI - Register</h2>
      <input placeholder="Name" onChange={(e) => setForm({ ...form, name: e.target.value })} required />
      <input type="email" placeholder="Email" onChange={(e) => setForm({ ...form, email: e.target.value })} required />
      <input type="password" placeholder="Password" onChange={(e) => setForm({ ...form, password: e.target.value })} required />
      <button type="submit">Create account</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </form>
  );
}