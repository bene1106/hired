function Materials({ job, onBack }) {
  const [tab, setTab] = useState("cover");
  const [generating, setGenerating] = useState(true);
  const [progress, setProgress] = useState(0);
  const [coverText, setCoverText] = useState("");

  const targetCover = `Dear Lumen Labs team,

Your recent post on the design-token rewrite is exactly the kind of problem I've been sitting in for the last 18 months. At Glint Systems I led a system consolidation across four product areas — we moved from three inconsistent component libraries to a single, token-driven system, cutting engineering hand-off time by roughly 40%.

What caught my eye in your job description is the emphasis on partnering closely with engineering on tokens and theming. That's the part I enjoy most: getting into the weeds of naming, scale, and semantic vs. raw tokens with the engineers who will actually consume them.

I'd love to talk about your current setup — especially how you're thinking about theming across the new workspaces feature.

Best,
Alex Morgan`;

  useEffect(() => {
    if (!generating) return;
    const dur = 3200; // condensed from "15s" for demo
    const start = performance.now();
    let raf;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / dur);
      setProgress(t);
      if (t < 1) raf = requestAnimationFrame(tick);
      else {
        setGenerating(false);
        // Typewriter-ish reveal
        let i = 0;
        const chunk = 8;
        const typer = setInterval(() => {
          i += chunk;
          setCoverText(targetCover.slice(0, i));
          if (i >= targetCover.length) clearInterval(typer);
        }, 20);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [generating]);

  const stages = [
    { label: "Analyzing job post", at: 0.2 },
    { label: "Cross-referencing your profile", at: 0.45 },
    { label: "Drafting cover letter", at: 0.75 },
    { label: "Polishing tone + length", at: 0.95 }
  ];

  return (
    <div className="screen" style={{ maxWidth: 1280, margin: "0 auto", padding: "24px 32px 80px", minHeight: "100vh" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <button className="btn ghost sm" onClick={onBack}>
          <Icon name="arrowLeft" size={13} /> Back
        </button>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn sm" disabled={generating}><Icon name="refresh" size={12} /> Regenerate</button>
          <button className="btn sm"><Icon name="copy" size={12} /> Copy all</button>
          <button className="btn primary sm" disabled={generating}><Icon name="send" size={12} /> Submit application</button>
        </div>
      </div>

      {/* Header strip */}
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
        <CompanyMark initial={job?.companyInitial || "L"} size={40} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, color: "var(--ink-3)", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 2 }}>Applying to</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{job?.title || "Product Designer"} · {job?.company || "Lumen Labs"}</div>
        </div>
        <MatchRing score={job?.score || 94} size={44} stroke={3} animate={false} label={false} />
      </div>

      {/* Two-column */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "flex-start" }}>
        {/* LEFT — Job post */}
        <div className="card" style={{ padding: 0, position: "sticky", top: 16, maxHeight: "calc(100vh - 80px)", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="file" size={13} style={{ color: "var(--ink-3)" }} />
            <span style={{ fontSize: 12, fontWeight: 500, letterSpacing: "-0.01em" }}>Job post</span>
            <span className="chip" style={{ marginLeft: "auto" }}>Source</span>
          </div>
          <div style={{ padding: 20, overflowY: "auto", fontSize: 13, color: "var(--ink-2)", lineHeight: 1.65 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: "0 0 10px" }}>About the role</h4>
            <p style={{ margin: "0 0 14px" }}>We're rebuilding our core product around a shared <mark style={{ background: "var(--accent-tint)", color: "var(--accent)", padding: "0 2px" }}>design system</mark>, and we need a product designer who has done this before. You'll own the component library, partner closely with engineering on <mark style={{ background: "var(--accent-tint)", color: "var(--accent)", padding: "0 2px" }}>design tokens</mark>, and ship features end-to-end.</p>

            <h4 style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: "0 0 10px" }}>What you'll do</h4>
            <ul style={{ paddingLeft: 18, margin: "0 0 14px" }}>
              <li>Lead design-token consolidation across 3 squads</li>
              <li>Partner with 2 FE engineers on the component library rewrite</li>
              <li>Ship 1–2 customer-facing features per quarter end-to-end</li>
              <li>Run monthly design-crit and pair reviews</li>
            </ul>

            <h4 style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", margin: "0 0 10px" }}>Who you are</h4>
            <ul style={{ paddingLeft: 18, margin: 0 }}>
              <li>4+ years in B2B SaaS product design</li>
              <li>Strong portfolio of <mark style={{ background: "var(--accent-tint)", color: "var(--accent)", padding: "0 2px" }}>system-level</mark> work</li>
              <li>Comfort with async / written communication</li>
              <li>Based in EU (Berlin or remote)</li>
            </ul>
          </div>
        </div>

        {/* RIGHT — Generated */}
        <div className="card" style={{ padding: 0, minHeight: 520, display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--line)", display: "flex", gap: 2 }}>
            {[
              { id: "cover", label: "Cover letter", icon: "mail" },
              { id: "cv", label: "CV highlights", icon: "doc" },
              { id: "research", label: "Company brief", icon: "building" }
            ].map(t => (
              <button key={t.id} className="btn sm" onClick={() => setTab(t.id)} style={{
                background: tab === t.id ? "var(--surface-2)" : "transparent",
                border: "1px solid transparent",
                color: tab === t.id ? "var(--ink)" : "var(--ink-3)",
                fontWeight: tab === t.id ? 500 : 400
              }}>
                <Icon name={t.icon} size={12} /> {t.label}
              </button>
            ))}
            <div style={{ flex: 1 }} />
            {!generating && (
              <span className="chip green" style={{ alignSelf: "center" }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--accent)" }}></span>
                Generated
              </span>
            )}
          </div>

          <div style={{ padding: 24, flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            {generating ? (
              <GeneratingState progress={progress} stages={stages} />
            ) : tab === "cover" ? (
              <CoverLetter text={coverText} onChange={setCoverText} />
            ) : tab === "cv" ? (
              <CvHighlights />
            ) : (
              <CompanyBrief />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function GeneratingState({ progress, stages }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18, padding: "12px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ position: "relative", width: 36, height: 36 }}>
          <svg width="36" height="36" style={{ transform: "rotate(-90deg)" }}>
            <circle cx="18" cy="18" r="15" stroke="var(--line)" strokeWidth="3" fill="none" />
            <circle cx="18" cy="18" r="15" stroke="var(--accent)" strokeWidth="3" fill="none"
              strokeLinecap="round" strokeDasharray={2*Math.PI*15}
              strokeDashoffset={2*Math.PI*15 - progress*2*Math.PI*15} />
          </svg>
          <Icon name="sparkle" size={14} style={{ position: "absolute", top: 11, left: 11, color: "var(--accent)" }} />
        </div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.01em" }}>Generating your materials</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)" }}>Usually takes ~15 seconds</div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
        {stages.map((s, i) => {
          const done = progress >= s.at;
          const active = progress < s.at && (i === 0 || progress >= stages[i-1].at);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: done ? "var(--ink)" : active ? "var(--ink-2)" : "var(--ink-4)" }}>
              <div style={{
                width: 16, height: 16, borderRadius: "50%",
                background: done ? "var(--accent)" : "transparent",
                border: done ? "none" : `1.5px solid ${active ? "var(--accent)" : "var(--line-strong)"}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0
              }}>
                {done && <Icon name="check" size={10} style={{ color: "#fff" }} />}
                {active && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)", animation: "pulse-dot 1s ease-in-out infinite" }}></span>}
              </div>
              {s.label}
            </div>
          );
        })}
      </div>

      {/* Skeleton preview */}
      <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 8 }}>
        <div className="skeleton" style={{ height: 12, width: "70%" }} />
        <div className="skeleton" style={{ height: 12, width: "95%" }} />
        <div className="skeleton" style={{ height: 12, width: "88%" }} />
        <div className="skeleton" style={{ height: 12, width: "60%" }} />
        <div className="skeleton" style={{ height: 12, width: "92%", marginTop: 8 }} />
        <div className="skeleton" style={{ height: 12, width: "80%" }} />
      </div>
    </div>
  );
}

function CoverLetter({ text, onChange }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
        <button className="btn sm ghost"><Icon name="edit" size={11} /> Shorter</button>
        <button className="btn sm ghost">Longer</button>
        <button className="btn sm ghost">More formal</button>
        <button className="btn sm ghost">More direct</button>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: "var(--ink-4)", alignSelf: "center" }} className="mono">{text.split(/\s+/).filter(Boolean).length} words</span>
      </div>
      <textarea
        value={text}
        onChange={e => onChange(e.target.value)}
        style={{
          flex: 1, minHeight: 320,
          background: "var(--surface-2)", border: "1px solid var(--line)",
          borderRadius: 8, padding: 16,
          fontSize: 13, lineHeight: 1.65, color: "var(--ink)",
          resize: "none", outline: "none",
          fontFamily: "var(--sans)"
        }}
      />
    </div>
  );
}

function CvHighlights() {
  const highlights = [
    { section: "Summary", text: "Product designer with 5 years in B2B SaaS, specializing in design-system consolidation and cross-functional engineering partnership.", tailored: ["design-system", "engineering partnership"] },
    { section: "Glint Systems — Product Designer", text: "Led migration from 3 inconsistent component libraries to a single token-driven system across 4 product areas. Cut engineering hand-off time by 40%.", tailored: ["token-driven system", "component libraries"] },
    { section: "Key skill emphasis", text: "Design tokens · Theming · Semantic scale · Engineering partnership · Async documentation", tailored: ["Design tokens", "Theming"] }
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, overflowY: "auto", paddingRight: 4 }}>
      <div style={{ fontSize: 12, color: "var(--ink-3)", paddingBottom: 8, borderBottom: "1px solid var(--line)" }}>
        3 sections tailored to emphasize design-system fit. <span style={{ color: "var(--accent)" }}>Highlighted phrases</span> were rewritten to match job keywords.
      </div>
      {highlights.map((h, i) => (
        <div key={i} className="card" style={{ padding: 14, boxShadow: "none" }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 6 }}>{h.section}</div>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: "var(--ink-2)" }}>
            {h.text.split(/(\s+)/).map((w, j) => {
              const match = h.tailored.some(t => h.text.indexOf(t) !== -1 && t.includes(w.trim()) && w.trim());
              return <span key={j} style={match ? { background: "var(--accent-tint)", color: "var(--accent)", padding: "0 1px", borderRadius: 2 } : {}}>{w}</span>;
            })}
          </p>
        </div>
      ))}
    </div>
  );
}

function CompanyBrief() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, overflowY: "auto", paddingRight: 4, fontSize: 13, lineHeight: 1.65, color: "var(--ink-2)" }}>
      <div>
        <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", margin: "0 0 6px" }}>The pitch</h4>
        <p style={{ margin: 0 }}>Lumen Labs sells developer tooling to distributed engineering teams. Think: staging previews, shared dev environments, and feedback tooling — pitched as a single unified surface.</p>
      </div>
      <div>
        <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", margin: "0 0 6px" }}>Recent moves</h4>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          <li>Raised a €30M Series B in Jan, led by Index Ventures.</li>
          <li>Launched "Workspaces" in March — a multi-tenant rewrite of the core product.</li>
          <li>Design team grew from 4 → 8 over the last year.</li>
        </ul>
      </div>
      <div>
        <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", margin: "0 0 6px" }}>Interview rumor mill</h4>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          <li>3 rounds: portfolio review → take-home (4h) → panel (3x 45min)</li>
          <li>Take-home is typically a design-system audit of a toy product</li>
          <li>Final panel includes the CTO — technical fluency matters</li>
        </ul>
      </div>
      <div>
        <h4 style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", margin: "0 0 6px" }}>Conversation starters</h4>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          <li>Their recent blog post on semantic vs. raw tokens — you've thought about this</li>
          <li>The move from 3 libraries to 1 at Glint is a near-perfect mirror of their current project</li>
        </ul>
      </div>
    </div>
  );
}

window.Materials = Materials;
