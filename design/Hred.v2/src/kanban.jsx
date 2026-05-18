function Kanban() {
  const initialData = window.__DATA__.APPLICATIONS;
  const [cols, setCols] = useState(initialData);
  const [dragging, setDragging] = useState(null); // { id, from }
  const [dragOver, setDragOver] = useState(null);

  const columns = [
    { id: "discovered", name: "Discovered", desc: "Matched by your agent", accent: "var(--ink-3)" },
    { id: "applied", name: "Applied", desc: "Submitted, awaiting response", accent: "var(--info)" },
    { id: "interview", name: "Interview", desc: "In progress", accent: "var(--accent)" },
    { id: "offer", name: "Offer", desc: "Decision pending", accent: "var(--accent-2)" },
    { id: "rejected", name: "Rejected", desc: "Not this time", accent: "var(--warn)" }
  ];

  const onDragStart = (id, from) => setDragging({ id, from });
  const onDragEnd = () => { setDragging(null); setDragOver(null); };
  const onDrop = (toCol) => {
    if (!dragging) return;
    const { id, from } = dragging;
    if (from === toCol) { onDragEnd(); return; }
    setCols(prev => {
      const card = prev[from].find(c => c.id === id);
      return {
        ...prev,
        [from]: prev[from].filter(c => c.id !== id),
        [toCol]: [{ ...card, updated: "Just now" }, ...prev[toCol]]
      };
    });
    onDragEnd();
  };

  const totalApps = Object.values(cols).flat().length;
  const patterns = window.__DATA__.REJECTION_PATTERNS;

  return (
    <div className="screen" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Header */}
      <div style={{ padding: "24px 32px 18px", borderBottom: "1px solid var(--line)" }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: "-0.02em", margin: 0 }}>Applications</h1>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-3)" }}>
              <span className="mono" style={{ color: "var(--ink)" }}>{totalApps}</span> active · Drag to move between stages
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn sm"><Icon name="filter" size={12} /> Filter</button>
            <button className="btn sm"><Icon name="refresh" size={12} /> Sort</button>
            <button className="btn sm primary"><Icon name="plus" size={12} /> Add</button>
          </div>
        </div>

        {/* Stats strip */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginTop: 18 }}>
          {columns.map(c => (
            <div key={c.id} style={{
              padding: "10px 12px", background: "var(--surface)",
              border: "1px solid var(--line)", borderRadius: 8,
              borderLeft: `3px solid ${c.accent}`
            }}>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)" }}>{c.name}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 4 }}>
                <span className="mono" style={{ fontSize: 20, fontWeight: 500, letterSpacing: "-0.02em" }}>{cols[c.id].length}</span>
                <span style={{ fontSize: 11, color: "var(--ink-4)" }}>apps</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Board */}
      <div style={{ flex: 1, overflowX: "auto", overflowY: "hidden", padding: "20px 32px", background: "var(--bg-sunk)" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(260px, 1fr))", gap: 14, height: "100%" }}>
          {columns.map(c => (
            <div key={c.id}
              onDragOver={e => { e.preventDefault(); setDragOver(c.id); }}
              onDragLeave={() => setDragOver(null)}
              onDrop={() => onDrop(c.id)}
              style={{
                display: "flex", flexDirection: "column",
                background: "var(--bg)", border: `1px solid ${dragOver === c.id ? c.accent : "var(--line)"}`,
                borderRadius: 10, minHeight: 0,
                transition: "border-color .15s ease, background .15s ease",
                ...(dragOver === c.id ? { background: "var(--surface-2)" } : {})
              }}>
              <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: c.accent }}></span>
                <span style={{ fontSize: 12, fontWeight: 600 }}>{c.name}</span>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginLeft: "auto" }}>{cols[c.id].length}</span>
              </div>
              <div style={{ flex: 1, overflowY: "auto", padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                {cols[c.id].length === 0 ? (
                  <EmptyColumn colId={c.id} />
                ) : (
                  cols[c.id].map(card => (
                    <AppCard key={card.id} card={card} colId={c.id}
                      onDragStart={() => onDragStart(card.id, c.id)}
                      onDragEnd={onDragEnd}
                      isDragging={dragging?.id === card.id} />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Rejection analysis (below) */}
        <div style={{ marginTop: 18 }}>
          <RejectionAnalysis patterns={patterns} />
        </div>
      </div>
    </div>
  );
}

function AppCard({ card, colId, onDragStart, onDragEnd, isDragging }) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className="card card-hover"
      style={{
        padding: 12,
        cursor: "grab",
        opacity: isDragging ? 0.4 : 1,
        borderRadius: 8
      }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <CompanyMark initial={card.company[0]} size={28} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{card.company}</div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{card.role}</div>
        </div>
        <MatchRing score={card.score} size={28} stroke={2.5} animate={false} label={false} />
      </div>
      {card.notes && (
        <div style={{ marginTop: 8, padding: "6px 8px", background: "var(--surface-2)", borderRadius: 5, fontSize: 11, color: "var(--ink-2)", lineHeight: 1.4 }}>
          {card.notes}
        </div>
      )}
      <div style={{ marginTop: 8, display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 10, color: "var(--ink-4)" }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
          <Icon name="clock" size={10} /> {card.updated}
        </span>
        <Icon name="drag" size={12} style={{ color: "var(--ink-4)" }} />
      </div>
    </div>
  );
}

function EmptyColumn({ colId }) {
  const copy = {
    discovered: { title: "No new matches yet", body: "Your agent scans every morning. Fresh jobs will land here by 9am." },
    applied: { title: "Nothing submitted yet", body: "When you apply to a job, it lands here. Hit the apply button on anything in Discovered." },
    interview: { title: "No interviews scheduled", body: "Responses usually come 3–10 days after applying. Waiting is the worst part — hang in there." },
    offer: { title: "No offers — yet", body: "This space is reserved for the good news. We'll celebrate when it gets here." },
    rejected: { title: "No rejections yet", body: "Your first ghosting isn't waiting for you. 😉 Enjoy the quiet while it lasts." }
  }[colId];
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      padding: "24px 12px", textAlign: "center", gap: 6,
      border: "1.5px dashed var(--line-strong)", borderRadius: 8,
      color: "var(--ink-3)",
      margin: "auto 0"
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "var(--ink-2)" }}>{copy.title}</div>
      <div style={{ fontSize: 11, lineHeight: 1.5, textWrap: "pretty" }}>{copy.body}</div>
    </div>
  );
}

function RejectionAnalysis({ patterns }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="card" style={{ padding: 18 }}>
      <button onClick={() => setOpen(v => !v)} style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, background: "transparent", padding: 0 }}>
        <Icon name="info" size={14} style={{ color: "var(--warn)" }} />
        <div style={{ textAlign: "left", flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, letterSpacing: "-0.01em" }}>Pattern analysis</div>
          <div style={{ fontSize: 11, color: "var(--ink-3)" }}>Your agent noticed 3 patterns in your recent rejections</div>
        </div>
        <Icon name={open ? "chevronDown" : "chevron"} size={14} style={{ color: "var(--ink-3)" }} />
      </button>
      {open && (
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          {patterns.map((p, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 12px", background: "var(--surface-2)", borderRadius: 6 }}>
              <span style={{
                width: 6, height: 6, borderRadius: "50%",
                background: p.severity === "high" ? "var(--warn)" : p.severity === "medium" ? "var(--info)" : "var(--ink-4)"
              }}></span>
              <div style={{ flex: 1, fontSize: 12, color: "var(--ink-2)" }}>{p.pattern}</div>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{p.count}×</span>
              <button className="btn sm ghost" style={{ padding: "3px 8px", fontSize: 11 }}>See why</button>
            </div>
          ))}
          <div style={{ padding: 12, background: "var(--accent-tint)", border: "1px solid var(--accent-soft)", borderRadius: 6, fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>
            <strong style={{ color: "var(--accent)" }}>Suggestion:</strong> Your strongest narrative is "design-system consolidation." Senior roles are rejecting on depth. Consider either (a) targeting roles that match your 18-month system experience, or (b) writing a case study that reframes the Glint work as strategic, not tactical.
          </div>
        </div>
      )}
    </div>
  );
}

window.Kanban = Kanban;
