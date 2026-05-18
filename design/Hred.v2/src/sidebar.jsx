function Sidebar({ current, onNav, theme, onToggleTheme }) {
  const items = [
    { id: "feed", label: "Job Feed", icon: "feed", badge: "12 new" },
    { id: "detail", label: "Current Job", icon: "target" },
    { id: "materials", label: "Materials", icon: "doc" },
    { id: "interview", label: "Interview Prep", icon: "chat" },
    { id: "kanban", label: "Applications", icon: "kanban", badge: "13" },
    { id: "onboarding", label: "Profile", icon: "user" }
  ];
  return (
    <aside style={{
      background: "var(--bg-sunk)",
      borderRight: "1px solid var(--line)",
      display: "flex", flexDirection: "column",
      padding: "18px 14px",
      position: "sticky", top: 0, height: "100vh"
    }}>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 8px 18px" }}>
        <HiredMark size={32} />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1, gap: 4 }}>
          <HiredWordmark size={20} />
          <span style={{ fontSize: 9.5, color: "var(--ink-3)", letterSpacing: ".1em", textTransform: "uppercase", fontFamily: "'JetBrains Mono', monospace" }}>Career Agent</span>
        </div>
      </div>

      {/* Search */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "7px 10px", margin: "0 0 16px",
        background: "var(--surface)", border: "1px solid var(--line)",
        borderRadius: 8, color: "var(--ink-3)", fontSize: 12
      }}>
        <Icon name="search" size={13} />
        <span style={{ flex: 1 }}>Search…</span>
        <span className="kbd">⌘K</span>
      </div>

      {/* Nav */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {items.map(it => (
          <button key={it.id} onClick={() => onNav(it.id)}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "8px 10px", borderRadius: 7,
              background: current === it.id ? "var(--surface)" : "transparent",
              color: current === it.id ? "var(--ink)" : "var(--ink-2)",
              fontWeight: current === it.id ? 500 : 400,
              fontSize: 13,
              border: current === it.id ? "1px solid var(--line)" : "1px solid transparent",
              boxShadow: current === it.id ? "var(--shadow-sm)" : "none",
              textAlign: "left",
              width: "100%"
            }}>
            <Icon name={it.icon} size={15} />
            <span style={{ flex: 1 }}>{it.label}</span>
            {it.badge && (
              <span style={{
                fontSize: 10, fontFamily: "var(--mono)",
                padding: "2px 6px", borderRadius: 4,
                background: current === it.id ? "var(--accent-tint)" : "var(--surface-2)",
                color: current === it.id ? "var(--accent)" : "var(--ink-3)",
                fontWeight: 500
              }}>{it.badge}</span>
            )}
          </button>
        ))}
      </nav>

      {/* Daily agent status */}
      <div style={{ marginTop: 22, padding: "12px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 8 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent)", animation: "pulse-dot 2s ease-in-out infinite" }}></span>
          <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)" }}>Agent Active</span>
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.45 }}>
          Scanned <span className="mono" style={{ color: "var(--ink)" }}>847</span> jobs today.
          Found <span className="mono" style={{ color: "var(--accent)" }}>12</span> that match.
        </div>
        <div style={{ marginTop: 8, fontSize: 11, color: "var(--ink-4)" }}>Next sync in 3h 42m</div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Footer — theme + user */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 6px" }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: "var(--accent-soft)", color: "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontWeight: 600, fontSize: 12
        }}>AM</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Alex Morgan</div>
          <div style={{ fontSize: 10, color: "var(--ink-3)" }}>Product Designer · Berlin</div>
        </div>
        <button className="btn icon ghost" onClick={onToggleTheme} title="Toggle theme">
          <Icon name={theme === "dark" ? "sun" : "moon"} size={14} />
        </button>
      </div>
    </aside>
  );
}

window.Sidebar = Sidebar;
