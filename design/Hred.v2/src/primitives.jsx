const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ========== ICONS ========== (minimal line icons, consistent 1.5 stroke)
const Icon = ({ name, size = 16, className = "", style = {} }) => {
  const common = {
    width: size, height: size, viewBox: "0 0 24 24",
    fill: "none", stroke: "currentColor", strokeWidth: 1.75,
    strokeLinecap: "round", strokeLinejoin: "round",
    className, style
  };
  const paths = {
    spark: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></>,
    feed: <><path d="M4 7h16M4 12h16M4 17h10"/></>,
    target: <><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1" fill="currentColor"/></>,
    doc: <><path d="M7 3h8l4 4v14H7z"/><path d="M15 3v4h4"/><path d="M10 13h6M10 17h4"/></>,
    chat: <><path d="M4 5h16v11H8l-4 4z"/></>,
    kanban: <><path d="M5 4h4v16H5zM15 4h4v10h-4zM10 4h4v7h-4z"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.5 3.6-8 8-8s8 3.5 8 8"/></>,
    sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.5 1.5M17.6 17.6l1.5 1.5M4.9 19.1l1.5-1.5M17.6 6.4l1.5-1.5"/></>,
    moon: <><path d="M20 15.5A8 8 0 1 1 8.5 4 7 7 0 0 0 20 15.5z"/></>,
    upload: <><path d="M12 15V3M7 8l5-5 5 5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/></>,
    check: <><path d="M4 12l5 5L20 6"/></>,
    chevron: <><path d="M9 6l6 6-6 6"/></>,
    chevronDown: <><path d="M6 9l6 6 6-6"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></>,
    filter: <><path d="M4 5h16M7 12h10M10 19h4"/></>,
    bolt: <><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    save: <><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M7 3v5h9V3M7 21v-8h10v8"/></>,
    skip: <><path d="M5 5l7 7-7 7M13 5l7 7-7 7"/></>,
    thumbUp: <><path d="M7 10v10H4V10zM7 10l4-7c1 0 2 1 2 2v4h5a2 2 0 0 1 2 2l-2 7a2 2 0 0 1-2 1H7"/></>,
    thumbDown: <><path d="M7 14V4H4v10zM7 14l4 7c1 0 2-1 2-2v-4h5a2 2 0 0 0 2-2l-2-7a2 2 0 0 0-2-1H7"/></>,
    send: <><path d="M4 12l16-8-6 16-2-7-8-1z"/></>,
    drag: <><circle cx="9" cy="6" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="6" r="1" fill="currentColor" stroke="none"/><circle cx="9" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="9" cy="18" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="18" r="1" fill="currentColor" stroke="none"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.4.9a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.5a7 7 0 0 0-2 1.2l-2.4-.9-2 3.4 2 1.6A7 7 0 0 0 5 12a7 7 0 0 0 .1 1.2l-2 1.6 2 3.4 2.4-.9a7 7 0 0 0 2 1.2L10 21h4l.5-2.5a7 7 0 0 0 2-1.2l2.4.9 2-3.4-2-1.6c.07-.4.1-.8.1-1.2z"/></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 7 9-7"/></>,
    building: <><rect x="5" y="3" width="14" height="18"/><path d="M9 7h.01M13 7h.01M9 11h.01M13 11h.01M9 15h.01M13 15h.01M10 21v-4h4v4"/></>,
    pin: <><path d="M12 22s7-7 7-12a7 7 0 0 0-14 0c0 5 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></>,
    euro: <><path d="M17 5a7 7 0 1 0 0 14M5 10h8M5 14h8"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    sparkle: <><path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/></>,
    close: <><path d="M6 6l12 12M18 6L6 18"/></>,
    arrowLeft: <><path d="M19 12H5M12 19l-7-7 7-7"/></>,
    arrowRight: <><path d="M5 12h14M12 5l7 7-7 7"/></>,
    refresh: <><path d="M4 4v6h6M20 20v-6h-6"/><path d="M20 10A8 8 0 0 0 6 6M4 14a8 8 0 0 0 14 4"/></>,
    edit: <><path d="M4 20h4l10-10-4-4L4 16z"/><path d="M14 6l4 4"/></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></>,
    file: <><path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13 3v6h6"/></>,
    star: <><path d="M12 2l3 7 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z"/></>,
    trash: <><path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/></>,
    users: <><circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M15 20c0-2.5 2-4.5 4.5-4.5"/></>,
    briefcase: <><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5"/></>
  };
  return <svg {...common}>{paths[name] || null}</svg>;
};

// ========== MATCH RING ========== (core brand element — animated reveal)
function MatchRing({ score, size = 52, stroke = 4, animate = true, delay = 0, label = true }) {
  const [current, setCurrent] = useState(animate ? 0 : score);
  const [bounced, setBounced] = useState(false);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  useEffect(() => {
    if (!animate) { setCurrent(score); return; }
    const t = setTimeout(() => {
      const start = performance.now();
      const dur = 900;
      const from = 0;
      const to = score;
      let raf;
      const step = (now) => {
        const t = Math.min(1, (now - start) / dur);
        // ease out cubic
        const eased = 1 - Math.pow(1 - t, 3);
        setCurrent(Math.round(from + (to - from) * eased));
        if (t < 1) raf = requestAnimationFrame(step);
        else if (score >= 85) {
          setBounced(true);
          setTimeout(() => setBounced(false), 700);
        }
      };
      raf = requestAnimationFrame(step);
      return () => cancelAnimationFrame(raf);
    }, delay);
    return () => clearTimeout(t);
  }, [score, animate, delay]);

  // Color buckets — consistent semantic
  const color = score >= 85 ? "var(--accent)" : score >= 70 ? "var(--info)" : "var(--ink-3)";
  const trackColor = "var(--line)";
  const offset = c - (current / 100) * c;

  const wrapperStyle = bounced ? { animation: "subtle-bounce .7s cubic-bezier(.4,1.4,.6,1)" } : {};

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 2, ...wrapperStyle }}>
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size/2} cy={size/2} r={r} stroke={trackColor} strokeWidth={stroke} fill="none" />
          <circle
            cx={size/2} cy={size/2} r={r}
            stroke={color} strokeWidth={stroke} fill="none"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            style={{ transition: "stroke 200ms ease" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "var(--mono)",
          fontWeight: 500,
          fontSize: size * 0.34,
          color: "var(--ink)",
          fontVariantNumeric: "tabular-nums",
          letterSpacing: "-0.01em"
        }}>
          {current}
        </div>
      </div>
      {label && (
        <div style={{ fontSize: 9, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--ink-4)", fontWeight: 600 }}>Match</div>
      )}
    </div>
  );
}

// ========== AVATAR / COMPANY LOGO (placeholder) ==========
function CompanyMark({ initial, size = 36, color }) {
  // Deterministic muted color per initial
  const colors = [
    "#C9CFC2", "#D6CEC3", "#C8CDD3", "#D4C9CB", "#CDD4C7", "#D1CAC2", "#C3CBD0"
  ];
  const idx = (initial?.charCodeAt(0) || 0) % colors.length;
  const bg = color || colors[idx];
  return (
    <div style={{
      width: size, height: size, borderRadius: size * 0.22,
      background: bg, color: "#1A1A17",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.42, fontWeight: 600, letterSpacing: "-0.02em",
      border: "1px solid rgba(0,0,0,0.06)",
      flexShrink: 0
    }}>{initial}</div>
  );
}

// ========== SCORE BREAKDOWN BAR ==========
function ScoreBar({ weight, color = "var(--accent)" }) {
  return (
    <div style={{ width: 120, height: 4, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
      <div style={{ width: `${weight*100}%`, height: "100%", background: color, transition: "width .6s ease" }} />
    </div>
  );
}

Object.assign(window, { Icon, MatchRing, CompanyMark, ScoreBar });
