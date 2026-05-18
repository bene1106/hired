function JobDetail({ job, onBack, onApply }) {
  if (!job) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--ink-3)" }}>
        Select a job from the feed.
      </div>
    );
  }

  return (
    <div className="screen" style={{ maxWidth: 960, margin: "0 auto", padding: "24px 40px 80px" }}>
      <button className="btn ghost sm" onClick={onBack} style={{ marginBottom: 18 }}>
        <Icon name="arrowLeft" size={13} /> Back to feed
      </button>

      {/* Hero */}
      <div className="card" style={{ padding: 28, marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
          <CompanyMark initial={job.companyInitial} size={56} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginBottom: 4 }}>{job.company} · {job.tagline || "Company"}</div>
            <h1 style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em", margin: "0 0 12px" }}>{job.title}</h1>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 13, color: "var(--ink-2)" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="pin" size={13} /> {job.location}</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="euro" size={13} /> {job.salary}</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="briefcase" size={13} /> {job.seniority}</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="clock" size={13} /> Posted {job.posted}</span>
            </div>
          </div>
          <MatchRing score={job.score} size={80} stroke={5} />
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 22, paddingTop: 20, borderTop: "1px solid var(--line)" }}>
          <button className="btn primary" onClick={() => onApply(job)}>
            <Icon name="bolt" size={13} /> Generate application materials
          </button>
          <button className="btn">
            <Icon name="save" size={13} /> Save for later
          </button>
          <button className="btn ghost">
            <Icon name="skip" size={13} /> Skip
          </button>
        </div>
      </div>

      {/* Two-column */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 12px", letterSpacing: "-0.01em" }}>About the role</h3>
          <p style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.65, textWrap: "pretty", margin: "0 0 20px" }}>
            {job.description || "We're hiring a designer to join our small, senior team. You'll work across discovery, interaction design, and polish, shipping end-to-end alongside engineering and product."}
          </p>

          <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 12px", letterSpacing: "-0.01em" }}>Requirements</h3>
          <ul style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.7, paddingLeft: 18, margin: "0 0 20px" }}>
            <li>4+ years designing B2B SaaS products end-to-end</li>
            <li>Strong portfolio showing design-system and component-level thinking</li>
            <li>Comfort partnering with engineering on tokens, theming, and a11y</li>
            <li>Excellent written communication — we're mostly async</li>
          </ul>

          <h3 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 12px", letterSpacing: "-0.01em" }}>Team</h3>
          <p style={{ fontSize: 13, color: "var(--ink-2)", lineHeight: 1.65, margin: 0 }}>
            {job.team || "4 designers"}, reporting to the Head of Design. You'll partner day-to-day with 2 engineers and a PM on the Platform squad.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Match breakdown */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <Icon name="target" size={14} style={{ color: "var(--accent)" }} />
              <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>Why this match</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
              {(job.scoreReasons || []).map((r, i) => (
                <div key={i}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 5 }}>
                    <span style={{ color: "var(--ink-2)" }}>{r.label}</span>
                    <span className="mono" style={{ color: r.weight > 0.8 ? "var(--accent)" : r.weight > 0.6 ? "var(--info)" : "var(--ink-4)" }}>{Math.round(r.weight*100)}</span>
                  </div>
                  <div style={{ width: "100%", height: 3, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ width: `${r.weight*100}%`, height: "100%", background: r.weight > 0.8 ? "var(--accent)" : r.weight > 0.6 ? "var(--info)" : "var(--ink-4)" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Company snapshot */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <Icon name="building" size={14} style={{ color: "var(--ink-3)" }} />
              <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Company</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ink-3)" }}>Stage</span><span>{job.stage || "Series B"}</span></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ink-3)" }}>Size</span><span>120 people</span></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ink-3)" }}>Founded</span><span>2019</span></div>
              <div style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ink-3)" }}>Glassdoor</span><span className="mono">4.4 ★</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.JobDetail = JobDetail;
