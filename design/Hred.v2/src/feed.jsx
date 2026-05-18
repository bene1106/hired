function JobCard({ job, onOpen, onApply, delay = 0, onSave, onSkip, saved, skipped, animate }) {
  const [feedback, setFeedback] = useState(null); // 'up' | 'down'
  const [saveToast, setSaveToast] = useState(false);

  const handleSave = (e) => {
    e.stopPropagation();
    onSave?.(job.id);
    setSaveToast(true);
    setTimeout(() => setSaveToast(false), 1200);
  };

  return (
    <div className="card card-hover fade-up" style={{
      padding: 18,
      animationDelay: `${delay * 60}ms`,
      opacity: skipped ? 0.4 : 1,
      position: "relative",
      cursor: "pointer",
      display: "grid",
      gridTemplateColumns: "auto 1fr auto",
      gap: 16
    }} onClick={() => onOpen(job)}>
      {/* Left: Company mark */}
      <CompanyMark initial={job.companyInitial} size={40} />

      {/* Middle: content */}
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4, flexWrap: "wrap" }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>{job.title}</h3>
          <span style={{ color: "var(--ink-3)", fontSize: 13 }}>·</span>
          <span style={{ fontSize: 13, color: "var(--ink-2)", fontWeight: 500 }}>{job.company}</span>
          <span style={{ color: "var(--ink-4)", fontSize: 11, marginLeft: "auto" }}>{job.posted}</span>
        </div>

        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: "var(--ink-3)", marginBottom: 10 }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Icon name="pin" size={12} /> {job.location}</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Icon name="euro" size={12} /> {job.salary}</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><Icon name="briefcase" size={12} /> {job.seniority}</span>
        </div>

        <p style={{ margin: "0 0 10px", fontSize: 13, color: "var(--ink-2)", lineHeight: 1.5, textWrap: "pretty" }}>
          {job.rationale}
        </p>

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {job.tags.map(t => <span key={t} className="chip">{t}</span>)}
        </div>
      </div>

      {/* Right: ring + actions */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 12, minWidth: 120 }}>
        <MatchRing score={job.score} size={60} stroke={4} animate={animate} delay={delay * 60} />

        <div style={{ display: "flex", gap: 4 }} onClick={e => e.stopPropagation()}>
          <button className={`btn icon ghost`} onClick={() => setFeedback(feedback === 'up' ? null : 'up')} title="Good match">
            <Icon name="thumbUp" size={14} style={{ color: feedback === 'up' ? "var(--accent)" : "var(--ink-3)" }} />
          </button>
          <button className={`btn icon ghost`} onClick={() => setFeedback(feedback === 'down' ? null : 'down')} title="Bad match">
            <Icon name="thumbDown" size={14} style={{ color: feedback === 'down' ? "var(--warn)" : "var(--ink-3)" }} />
          </button>
        </div>

        <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
          <button className="btn sm" onClick={() => onSkip?.(job.id)} title="Skip">
            <Icon name="close" size={12} /> Skip
          </button>
          <button className="btn sm" onClick={handleSave} title="Save">
            <Icon name="save" size={12} /> Save
          </button>
          <button className="btn sm primary" onClick={(e) => { e.stopPropagation(); onApply(job); }}>
            Apply <Icon name="arrowRight" size={12} />
          </button>
        </div>
      </div>

      {saveToast && (
        <div style={{
          position: "absolute", top: 8, right: 8,
          background: "var(--accent)", color: "#fff",
          padding: "4px 8px", borderRadius: 6,
          fontSize: 11, fontWeight: 500,
          animation: "fade-up .2s ease"
        }}>Saved</div>
      )}
    </div>
  );
}

function JobFeed({ onOpenJob, onApply }) {
  const jobs = window.__DATA__.JOBS;
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("match");
  const [saved, setSaved] = useState(new Set());
  const [skipped, setSkipped] = useState(new Set());
  const [loadKey, setLoadKey] = useState(0);

  const visible = jobs
    .filter(j => !skipped.has(j.id))
    .filter(j => filter === "all" || (filter === "remote" && j.location.toLowerCase().includes("remote"))
              || (filter === "berlin" && j.location.toLowerCase().includes("berlin"))
              || (filter === "high" && j.score >= 85));

  const rescan = () => {
    setLoadKey(k => k + 1);
  };

  return (
    <div className="screen" style={{ maxWidth: 1120, margin: "0 auto", padding: "32px 40px 80px" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, marginBottom: 8 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 6 }}>
              Wednesday · April 23
            </div>
            <h1 style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.025em", margin: 0 }}>
              <span>Today's matches</span>
            </h1>
          </div>
          <button className="btn" onClick={rescan}>
            <Icon name="refresh" size={13} /> Re-scan
          </button>
        </div>
        <p style={{ margin: "4px 0 0", color: "var(--ink-3)", fontSize: 13, maxWidth: 640 }}>
          Ranked by how well each job matches your profile and preferences. Thumbs-up or skip trains your agent — it learns as you go.
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 20, alignItems: "center", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <Icon name="filter" size={13} style={{ color: "var(--ink-3)" }} />
          {[
            { id: "all", label: "All", count: jobs.length },
            { id: "high", label: "High match", count: jobs.filter(j => j.score >= 85).length },
            { id: "remote", label: "Remote", count: jobs.filter(j => j.location.toLowerCase().includes("remote")).length },
            { id: "berlin", label: "Berlin", count: jobs.filter(j => j.location.toLowerCase().includes("berlin")).length }
          ].map(f => (
            <button key={f.id} className="btn sm" onClick={() => setFilter(f.id)} style={{
              background: filter === f.id ? "var(--ink)" : "var(--surface)",
              color: filter === f.id ? "var(--bg)" : "var(--ink-2)",
              borderColor: filter === f.id ? "var(--ink)" : "var(--line)"
            }}>
              {f.label} <span style={{ opacity: .6, marginLeft: 4 }} className="mono">{f.count}</span>
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--ink-3)" }}>
          <span>Sort by</span>
          <select value={sort} onChange={e => setSort(e.target.value)} style={{
            background: "var(--surface)", border: "1px solid var(--line)",
            padding: "5px 8px", borderRadius: 6, fontSize: 12
          }}>
            <option value="match">Match score</option>
            <option value="recent">Most recent</option>
            <option value="salary">Salary</option>
          </select>
        </div>
      </div>

      {/* Job list */}
      <div key={loadKey} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {visible.map((job, i) => (
          <JobCard
            key={`${loadKey}-${job.id}`}
            job={job}
            onOpen={onOpenJob}
            onApply={onApply}
            onSave={(id) => setSaved(s => new Set([...s, id]))}
            onSkip={(id) => setSkipped(s => new Set([...s, id]))}
            saved={saved.has(job.id)}
            skipped={skipped.has(job.id)}
            delay={i}
            animate={true}
          />
        ))}
      </div>

      {skipped.size > 0 && (
        <div style={{ marginTop: 24, display: "flex", justifyContent: "center" }}>
          <button className="btn ghost sm" onClick={() => setSkipped(new Set())}>
            <Icon name="refresh" size={12} /> Restore {skipped.size} skipped
          </button>
        </div>
      )}
    </div>
  );
}

window.JobFeed = JobFeed;
