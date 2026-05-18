function Interview() {
  const cats = window.__DATA__.INTERVIEW_CATEGORIES;
  const [activeCat, setActiveCat] = useState(cats[0].id);
  const current = cats.find(c => c.id === activeCat);
  const [messages, setMessages] = useState(window.__DATA__.SAMPLE_CHAT);
  const [input, setInput] = useState("");
  const [confidence, setConfidence] = useState(3);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = () => {
    if (!input.trim()) return;
    setMessages(m => [...m, { from: "user", text: input }]);
    setInput("");
    // Simulated coach reply
    setTimeout(() => {
      setMessages(m => [...m, { from: "coach", typing: true }]);
      setTimeout(() => {
        setMessages(m => m.filter(x => !x.typing).concat({
          from: "coach", feedback: true,
          text: "Good instinct. To strengthen it:",
          bullets: ["Open with the outcome, not the situation — hook them first.", "Quantify the impact if you can — numbers are sticky."],
          rating: 3
        }));
      }, 1400);
    }, 300);
  };

  return (
    <div className="screen" style={{ display: "grid", gridTemplateColumns: "280px 1fr 280px", height: "100vh", overflow: "hidden" }}>
      {/* LEFT — categories */}
      <div style={{ borderRight: "1px solid var(--line)", padding: "24px 18px", overflowY: "auto", background: "var(--bg-sunk)" }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 12 }}>Question bank</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {cats.map(c => (
            <button key={c.id} onClick={() => setActiveCat(c.id)} style={{
              display: "flex", flexDirection: "column", alignItems: "flex-start",
              padding: "10px 12px", borderRadius: 8, textAlign: "left",
              background: activeCat === c.id ? "var(--surface)" : "transparent",
              border: activeCat === c.id ? "1px solid var(--line)" : "1px solid transparent"
            }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{c.name}</div>
              <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 3, display: "flex", alignItems: "center", gap: 6 }}>
                <span className="mono">{c.practiced}/{c.total} practiced</span>
                <div style={{ flex: 1, maxWidth: 60, height: 3, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: `${(c.practiced/c.total)*100}%`, height: "100%", background: "var(--accent)" }}></div>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--line)" }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 10 }}>Questions in {current.name}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {current.questions.map((q, i) => (
              <button key={i} style={{
                padding: "8px 10px", borderRadius: 6, textAlign: "left",
                background: "var(--surface)", border: "1px solid var(--line)",
                fontSize: 12, color: "var(--ink-2)", lineHeight: 1.4
              }}>{q}</button>
            ))}
          </div>
        </div>
      </div>

      {/* CENTER — chat */}
      <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div style={{ padding: "16px 28px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--accent-tint)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="sparkle" size={16} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.01em" }}>Mock Interview · {current.name}</div>
            <div style={{ fontSize: 11, color: "var(--ink-3)" }}>Your coach will ask questions and critique your answers.</div>
          </div>
          <div style={{ flex: 1 }}></div>
          <button className="btn sm ghost"><Icon name="refresh" size={12} /> New session</button>
        </div>

        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 14 }}>
          {messages.map((m, i) => <ChatBubble key={i} m={m} />)}
        </div>

        <div style={{ padding: "14px 28px", borderTop: "1px solid var(--line)", background: "var(--bg-sunk)" }}>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, padding: 8 }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Type your answer… (Enter to send, Shift+Enter for newline)"
              rows={2}
              style={{
                flex: 1, background: "transparent", border: "none",
                resize: "none", outline: "none", padding: 8,
                fontSize: 13, lineHeight: 1.5, color: "var(--ink)",
                fontFamily: "var(--sans)"
              }}
            />
            <button className="btn accent sm" onClick={send} style={{ alignSelf: "flex-end" }}>
              <Icon name="send" size={12} /> Send
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT — progress */}
      <div style={{ borderLeft: "1px solid var(--line)", padding: "24px 20px", overflowY: "auto", background: "var(--bg-sunk)" }}>
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 14 }}>Session progress</div>

        <div className="card" style={{ padding: 16, marginBottom: 14 }}>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginBottom: 8 }}>Self-confidence</div>
          <div style={{ display: "flex", gap: 4, marginBottom: 10 }}>
            {[1,2,3,4,5].map(n => (
              <button key={n} onClick={() => setConfidence(n)} style={{
                flex: 1, height: 24, borderRadius: 6,
                background: n <= confidence ? "var(--accent)" : "var(--line)",
                border: "none", cursor: "pointer",
                transition: "background .15s"
              }} />
            ))}
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-3)" }}>
            {confidence === 1 ? "Dreading it" : confidence === 2 ? "Unsure" : confidence === 3 ? "Okay" : confidence === 4 ? "Solid" : "Ready"}
          </div>
        </div>

        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 10 }}>Answered today</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {["Tell me about a time you pushed back…", "Describe a project with difficult stakeholders…", "How do you handle harsh critique…"].map((q, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 6 }}>
              <div style={{ width: 5, height: 5, borderRadius: "50%", background: i === 0 ? "var(--accent)" : i === 1 ? "var(--info)" : "var(--warn)" }}></div>
              <div style={{ flex: 1, fontSize: 11, color: "var(--ink-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{q}</div>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>{["★★★★☆","★★★☆☆","★★☆☆☆"][i]}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 10 }}>Streak</div>
          <div style={{ display: "flex", gap: 3 }}>
            {[1,1,1,0,1,1,1,1,1,1,0,1,1,1].map((d, i) => (
              <div key={i} style={{ width: 12, height: 24, borderRadius: 3, background: d ? "var(--accent)" : "var(--line)" }}></div>
            ))}
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 8 }}><span className="mono" style={{ color: "var(--accent)" }}>12</span> days practiced in the last 14</div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ m }) {
  if (m.typing) {
    return (
      <div style={{ display: "flex", alignItems: "flex-end", gap: 10 }}>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-tint)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <Icon name="sparkle" size={13} />
        </div>
        <div style={{ padding: "10px 14px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "14px 14px 14px 4px", display: "flex", gap: 4 }}>
          {[0,1,2].map(i => <span key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ink-3)", animation: `pulse-dot 1s ease-in-out ${i*.15}s infinite` }}></span>)}
        </div>
      </div>
    );
  }
  if (m.from === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div style={{
          maxWidth: "75%", padding: "10px 14px",
          background: "var(--ink)", color: "var(--bg)",
          borderRadius: "14px 14px 4px 14px",
          fontSize: 13, lineHeight: 1.5
        }}>{m.text}</div>
      </div>
    );
  }
  // coach
  const isFeedback = m.feedback;
  const isQ = m.q;
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
      <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-tint)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon name="sparkle" size={13} />
      </div>
      <div style={{ maxWidth: "75%" }}>
        {isQ && <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 4 }}>Question</div>}
        {isFeedback && <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--accent)", marginBottom: 4 }}>Feedback</div>}
        <div style={{
          padding: "10px 14px",
          background: isFeedback ? "var(--accent-tint)" : "var(--surface)",
          border: `1px solid ${isFeedback ? "var(--accent-soft)" : "var(--line)"}`,
          borderRadius: "14px 14px 14px 4px",
          fontSize: 13, lineHeight: 1.55, color: "var(--ink-2)",
          fontWeight: isQ ? 500 : 400
        }}>
          <div>{m.text}</div>
          {m.bullets && (
            <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
              {m.bullets.map((b, i) => <li key={i} style={{ marginBottom: 4 }}>{b}</li>)}
            </ul>
          )}
          {m.rating && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid var(--accent-soft)", fontSize: 11, color: "var(--ink-3)", display: "flex", alignItems: "center", gap: 8 }}>
              <span>Answer strength</span>
              <span className="mono" style={{ color: "var(--ink)" }}>{"★".repeat(m.rating)}{"☆".repeat(5-m.rating)}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

window.Interview = Interview;
