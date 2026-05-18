function Onboarding() {
  const [step, setStep] = useState(0);
  const [uploaded, setUploaded] = useState(false);
  const [parsing, setParsing] = useState(false);
  const profile = window.__DATA__.PARSED_PROFILE;

  const steps = [
    { id: "upload", name: "Upload CV" },
    { id: "review", name: "Review profile" },
    { id: "prefs", name: "Preferences" },
    { id: "priorities", name: "Priorities" }
  ];

  const handleUpload = () => {
    setParsing(true);
    setTimeout(() => { setUploaded(true); setParsing(false); setTimeout(() => setStep(1), 500); }, 1800);
  };

  return (
    <div className="screen" style={{ maxWidth: 820, margin: "0 auto", padding: "32px 40px 80px" }}>
      {/* Stepper */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 28 }}>
          <HiredStacked markSize={64} wordSize={28} gap={14} />
        </div>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>Profile setup</div>
          <h1 style={{ fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em", margin: 0, fontFamily: "'Fraunces', serif" }}>Let's get your agent ready.</h1>
        </div>

        <div style={{ display: "flex", gap: 2, alignItems: "center", justifyContent: "center" }}>
          {steps.map((s, i) => (
            <React.Fragment key={s.id}>
              <button onClick={() => setStep(i)} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "6px 10px",
                background: step === i ? "var(--surface)" : "transparent",
                border: step === i ? "1px solid var(--line)" : "1px solid transparent",
                borderRadius: 7, fontSize: 12
              }}>
                <span style={{
                  width: 20, height: 20, borderRadius: "50%",
                  background: step > i ? "var(--accent)" : step === i ? "var(--ink)" : "var(--line)",
                  color: step > i || step === i ? "#fff" : "var(--ink-3)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, fontWeight: 600, fontFamily: "var(--mono)"
                }}>
                  {step > i ? <Icon name="check" size={10} /> : i + 1}
                </span>
                <span style={{ color: step === i ? "var(--ink)" : "var(--ink-3)", fontWeight: step === i ? 500 : 400 }}>{s.name}</span>
              </button>
              {i < steps.length - 1 && <div style={{ width: 20, height: 1, background: "var(--line)" }}></div>}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: 32 }}>
        {step === 0 && <UploadStep uploaded={uploaded} parsing={parsing} onUpload={handleUpload} onNext={() => setStep(1)} />}
        {step === 1 && <ReviewStep profile={profile} onNext={() => setStep(2)} onBack={() => setStep(0)} />}
        {step === 2 && <PrefsStep onNext={() => setStep(3)} onBack={() => setStep(1)} />}
        {step === 3 && <PrioritiesStep onBack={() => setStep(2)} />}
      </div>
    </div>
  );
}

function UploadStep({ uploaded, parsing, onUpload, onNext }) {
  if (uploaded) {
    return (
      <div style={{ textAlign: "center", padding: "40px 20px" }}>
        <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--accent-tint)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
          <Icon name="check" size={24} />
        </div>
        <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px", letterSpacing: "-0.01em" }}>CV parsed</h2>
        <p style={{ fontSize: 13, color: "var(--ink-3)", margin: "0 0 20px" }}>Pulled 3 roles, 12 skills, and 1 degree.</p>
        <button className="btn primary" onClick={onNext}>Review extracted profile <Icon name="arrowRight" size={13} /></button>
      </div>
    );
  }
  if (parsing) {
    return (
      <div style={{ textAlign: "center", padding: "40px 20px" }}>
        <div style={{ position: "relative", width: 56, height: 56, margin: "0 auto 16px" }}>
          <svg width="56" height="56" style={{ transform: "rotate(-90deg)" }}>
            <circle cx="28" cy="28" r="24" stroke="var(--line)" strokeWidth="3" fill="none" />
            <circle cx="28" cy="28" r="24" stroke="var(--accent)" strokeWidth="3" fill="none"
              strokeLinecap="round" strokeDasharray={2*Math.PI*24}
              strokeDashoffset={0}
              style={{ animation: "spin 1s linear infinite" }} />
          </svg>
          <style>{`@keyframes spin { from {stroke-dashoffset: ${2*Math.PI*24}} to {stroke-dashoffset: 0}}`}</style>
        </div>
        <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px", letterSpacing: "-0.01em" }}>Reading your CV…</h2>
        <p style={{ fontSize: 13, color: "var(--ink-3)", margin: 0 }}>Pulling out roles, skills, and dates.</p>
      </div>
    );
  }
  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px", letterSpacing: "-0.01em" }}>Start with your CV.</h2>
      <p style={{ fontSize: 13, color: "var(--ink-3)", margin: "0 0 22px" }}>Drop a PDF or DOCX. Your agent will parse it in about 10 seconds and you'll review before anything is saved.</p>
      <div
        onClick={onUpload}
        style={{
          border: "2px dashed var(--line-strong)", borderRadius: 12,
          padding: "48px 24px", textAlign: "center", cursor: "pointer",
          transition: "border-color .15s ease, background .15s ease",
          background: "var(--surface-2)"
        }}
        onMouseOver={e => { e.currentTarget.style.borderColor = "var(--accent)"; e.currentTarget.style.background = "var(--accent-tint)"; }}
        onMouseOut={e => { e.currentTarget.style.borderColor = "var(--line-strong)"; e.currentTarget.style.background = "var(--surface-2)"; }}>
        <Icon name="upload" size={28} style={{ color: "var(--ink-3)", marginBottom: 10 }} />
        <div style={{ fontSize: 14, fontWeight: 500 }}>Drop your CV here, or click to browse</div>
        <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 4 }}>PDF, DOCX — up to 10 MB</div>
      </div>
      <div style={{ display: "flex", justifyContent: "center", marginTop: 14, gap: 16, fontSize: 11, color: "var(--ink-4)" }}>
        <span>🔒 Never shared with employers</span>
        <span>·</span>
        <span>Stored encrypted</span>
      </div>
    </div>
  );
}

function ReviewStep({ profile, onNext, onBack }) {
  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px", letterSpacing: "-0.01em" }}>Does this look right?</h2>
      <p style={{ fontSize: 13, color: "var(--ink-3)", margin: "0 0 22px" }}>Fix anything wrong — your agent uses this to match jobs.</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 18 }}>
        <Field label="Name" value={profile.name} />
        <Field label="Headline" value={profile.headline} />
      </div>

      <Label>Experience</Label>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
        {profile.experience.map((e, i) => (
          <div key={i} style={{ padding: 14, background: "var(--surface-2)", borderRadius: 8, border: "1px solid var(--line)" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 3 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{e.role}</div>
              <div style={{ fontSize: 12, color: "var(--ink-3)" }}>· {e.company}</div>
              <div style={{ flex: 1 }}></div>
              <div style={{ fontSize: 11, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>{e.period}</div>
              <button className="btn ghost" style={{ padding: 4 }}><Icon name="edit" size={12} /></button>
            </div>
            <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>{e.summary}</div>
          </div>
        ))}
      </div>

      <Label>Skills (12 detected)</Label>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 22 }}>
        {profile.skills.map(s => <span key={s} className="chip">{s} <Icon name="close" size={10} /></span>)}
        <button className="chip" style={{ cursor: "pointer", borderStyle: "dashed" }}><Icon name="plus" size={10} /> Add</button>
      </div>

      <StepNav onBack={onBack} onNext={onNext} nextLabel="Preferences" />
    </div>
  );
}

function PrefsStep({ onNext, onBack }) {
  const [role, setRole] = useState("Product Designer");
  const [salary, setSalary] = useState(80);
  const [locations, setLocations] = useState(["Berlin", "Remote (EU)"]);
  const [workModes, setWorkModes] = useState(["Hybrid", "Remote"]);

  const allLocations = ["Berlin", "Munich", "Hamburg", "Remote (EU)", "Remote (Global)", "Amsterdam", "London"];
  const allModes = ["Remote", "Hybrid", "On-site"];

  const toggle = (list, set, v) => set(list.includes(v) ? list.filter(x => x !== v) : [...list, v]);

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px", letterSpacing: "-0.01em" }}>What are you looking for?</h2>
      <p style={{ fontSize: 13, color: "var(--ink-3)", margin: "0 0 22px" }}>We use this to filter — but your agent learns faster from your thumbs-up/down than from these answers.</p>

      <Label>Target role</Label>
      <input value={role} onChange={e => setRole(e.target.value)} style={inputStyle} />

      <div style={{ height: 18 }}></div>

      <Label>Target salary (base, €k)</Label>
      <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "8px 14px", background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 8 }}>
        <input type="range" min={40} max={160} step={5} value={salary} onChange={e => setSalary(+e.target.value)} style={{ flex: 1, accentColor: "var(--accent)" }} />
        <div className="mono" style={{ fontSize: 14, minWidth: 90, textAlign: "right" }}>€{salary}k – €{salary+15}k</div>
      </div>

      <div style={{ height: 18 }}></div>

      <Label>Locations</Label>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {allLocations.map(l => (
          <button key={l} onClick={() => toggle(locations, setLocations, l)} className="chip" style={{
            background: locations.includes(l) ? "var(--accent-tint)" : "var(--surface)",
            borderColor: locations.includes(l) ? "var(--accent-soft)" : "var(--line)",
            color: locations.includes(l) ? "var(--accent)" : "var(--ink-2)",
            cursor: "pointer"
          }}>{locations.includes(l) && <Icon name="check" size={10} />}{l}</button>
        ))}
      </div>

      <div style={{ height: 18 }}></div>

      <Label>Work mode</Label>
      <div style={{ display: "flex", gap: 6 }}>
        {allModes.map(m => (
          <button key={m} onClick={() => toggle(workModes, setWorkModes, m)} className="chip" style={{
            background: workModes.includes(m) ? "var(--accent-tint)" : "var(--surface)",
            borderColor: workModes.includes(m) ? "var(--accent-soft)" : "var(--line)",
            color: workModes.includes(m) ? "var(--accent)" : "var(--ink-2)",
            cursor: "pointer"
          }}>{workModes.includes(m) && <Icon name="check" size={10} />}{m}</button>
        ))}
      </div>

      <div style={{ height: 24 }}></div>

      <StepNav onBack={onBack} onNext={onNext} nextLabel="Priorities" />
    </div>
  );
}

function PrioritiesStep({ onBack }) {
  const [priorities, setPriorities] = useState([
    { id: "craft", label: "Interesting problems and craft", weight: 5 },
    { id: "comp", label: "Compensation", weight: 4 },
    { id: "growth", label: "Growth + mentorship", weight: 4 },
    { id: "balance", label: "Work-life balance", weight: 5 },
    { id: "mission", label: "Mission alignment", weight: 3 },
    { id: "stage", label: "Company stage / stability", weight: 2 }
  ]);
  const update = (id, w) => setPriorities(p => p.map(x => x.id === id ? { ...x, weight: w } : x));

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px", letterSpacing: "-0.01em" }}>What matters most?</h2>
      <p style={{ fontSize: 13, color: "var(--ink-3)", margin: "0 0 22px" }}>These weights shape how your agent ranks trade-offs. You can adjust anytime.</p>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {priorities.map(p => (
          <div key={p.id} style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 14, alignItems: "center", padding: "10px 14px", background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 8 }}>
            <div style={{ fontSize: 13, color: "var(--ink)" }}>{p.label}</div>
            <div style={{ display: "flex", gap: 3 }}>
              {[1,2,3,4,5].map(n => (
                <button key={n} onClick={() => update(p.id, n)} style={{
                  width: 22, height: 22, borderRadius: 5,
                  background: n <= p.weight ? "var(--accent)" : "var(--line)",
                  border: "none"
                }} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 24, padding: 16, background: "var(--accent-tint)", border: "1px solid var(--accent-soft)", borderRadius: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <Icon name="sparkle" size={14} style={{ color: "var(--accent)" }} />
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)" }}>Your agent is ready</div>
        </div>
        <p style={{ fontSize: 12, color: "var(--ink-2)", margin: 0, lineHeight: 1.5 }}>
          First scan will run in the next few minutes. Check back tomorrow morning for your first batch of matches.
        </p>
      </div>

      <div style={{ marginTop: 20, display: "flex", justifyContent: "space-between" }}>
        <button className="btn" onClick={onBack}><Icon name="arrowLeft" size={12} /> Back</button>
        <button className="btn primary">Finish setup <Icon name="check" size={13} /></button>
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%", padding: "9px 12px",
  background: "var(--surface-2)", border: "1px solid var(--line)",
  borderRadius: 8, fontSize: 13, color: "var(--ink)",
  outline: "none", fontFamily: "var(--sans)"
};

function Field({ label, value }) {
  return (
    <div>
      <Label>{label}</Label>
      <input defaultValue={value} style={inputStyle} />
    </div>
  );
}
function Label({ children }) {
  return <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: 6 }}>{children}</div>;
}
function StepNav({ onBack, onNext, nextLabel }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
      <button className="btn" onClick={onBack}><Icon name="arrowLeft" size={12} /> Back</button>
      <button className="btn primary" onClick={onNext}>{nextLabel} <Icon name="arrowRight" size={13} /></button>
    </div>
  );
}

window.Onboarding = Onboarding;
