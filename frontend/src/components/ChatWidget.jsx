import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Chat } from "./Icons";
import { API } from "../api";

const SUGGESTIONS = [
  "Which crop is best to sow this month?",
  "How do I store onions for 3 months?",
  "What is MSP and how do I claim it?",
  "Yellow spots on my tomato leaves, what to do?",
];
const WELCOME = {
  role: "assistant",
  content: "Hello! I am the AgroVision assistant. Ask me about crops, diseases, storage, prices or schemes. You can write in English, Hindi or Kannada.",
};

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([WELCOME]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const bodyRef = useRef(null);

  useEffect(() => {
    const openIt = () => setOpen(true);
    window.addEventListener("agro-open-chat", openIt);
    return () => window.removeEventListener("agro-open-chat", openIt);
  }, []);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [msgs, busy, open]);

  const send = async (q) => {
    const question = (q ?? text).trim();
    if (!question || busy) return;
    const history = msgs.filter((m) => m !== WELCOME && !m.error).map(({ role, content }) => ({ role, content }));
    setMsgs((m) => [...m, { role: "user", content: question }]);
    setText("");
    setBusy(true);
    try {
      const token = localStorage.getItem("token");
      const r = await axios.post(
        `${API}/chat`,
        { message: question, history },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 60000 }
      );
      const reply = String(r.data.reply || "").replace(/\*\*/g, "");
      setMsgs((m) => [...m, { role: "assistant", content: reply }]);
    } catch (e) {
      const detail = e?.response?.data?.detail || e.message || "Something went wrong.";
      setMsgs((m) => [...m, { role: "assistant", content: String(detail), error: true }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {open && (
        <div className="chat-panel" role="dialog" aria-label="AgroVision assistant">
          <div className="chat-head">
            <span style={{ fontSize: 22 }}>🌾</span>
            <div>
              <b>AgroVision Assistant</b>
              <small>Farming help in your language</small>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </div>
          <div className="chat-body" ref={bodyRef}>
            {msgs.map((m, i) => (
              <div key={i} className={`msg ${m.error ? "err" : m.role === "user" ? "me" : "bot"}`}>
                {m.content}
              </div>
            ))}
            {msgs.length === 1 && (
              <div className="chips">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}
            {busy && <div className="msg bot">Thinking…</div>}
          </div>
          <form className="chat-form" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type your question…"
              maxLength={500}
            />
            <button type="submit" disabled={busy || !text.trim()}>Send</button>
          </form>
        </div>
      )}
      <button className="chat-fab" onClick={() => setOpen((o) => !o)} aria-label="Open chat assistant">
        <Chat /> {open ? "Close" : "Ask AgroVision"}
      </button>
    </>
  );
}
