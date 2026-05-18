function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("hired-theme") || window.__TWEAKS?.theme || "light");
  const [screen, setScreen] = useState(() => localStorage.getItem("hired-screen") || "feed");
  const [currentJob, setCurrentJob] = useState(window.__DATA__.JOBS[0]);
  const [tweaksOpen, setTweaksOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("hired-theme", theme);
  }, [theme]);

  useEffect(() => { localStorage.setItem("hired-screen", screen); }, [screen]);

  // Edit mode (tweaks) integration with host
  useEffect(() => {
    const onMsg = (e) => {
      if (e.data?.type === "__activate_edit_mode") setTweaksOpen(true);
      if (e.data?.type === "__deactivate_edit_mode") setTweaksOpen(false);
    };
    window.addEventListener("message", onMsg);
    window.parent.postMessage({ type: "__edit_mode_available" }, "*");
    return () => window.removeEventListener("message", onMsg);
  }, []);

  const setTheme2 = (t) => {
    setTheme(t);
    window.parent.postMessage({ type: "__edit_mode_set_keys", edits: { theme: t } }, "*");
  };

  const onOpenJob = (j) => { setCurrentJob(j); setScreen("detail"); };
  const onApply = (j) => { setCurrentJob(j); setScreen("materials"); };

  let content;
  switch (screen) {
    case "feed": content = <JobFeed onOpenJob={onOpenJob} onApply={onApply} />; break;
    case "detail": content = <JobDetail job={currentJob} onBack={() => setScreen("feed")} onApply={onApply} />; break;
    case "materials": content = <Materials job={currentJob} onBack={() => setScreen("detail")} />; break;
    case "interview": content = <Interview />; break;
    case "kanban": content = <Kanban />; break;
    case "onboarding": content = <Onboarding />; break;
    default: content = <JobFeed onOpenJob={onOpenJob} onApply={onApply} />;
  }

  return (
    <div className="app">
      <Sidebar current={screen} onNav={setScreen} theme={theme} onToggleTheme={() => setTheme2(theme === "dark" ? "light" : "dark")} />
      <main className="shell-main">{content}</main>

      <div className={`tweaks-panel ${tweaksOpen ? "open" : ""}`}>
        <div className="tweaks-title">Tweaks</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, padding: "4px 0" }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Dark mode</div>
            <div style={{ fontSize: 11, color: "var(--ink-3)" }}>Warm off-white ↔ deep ink</div>
          </div>
          <div className={`switch ${theme === "dark" ? "on" : ""}`} onClick={() => setTheme2(theme === "dark" ? "light" : "dark")}></div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
