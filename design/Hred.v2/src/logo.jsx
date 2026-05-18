// Hired. brand mark — reusable logo component
// Mark: black circle with serif "h" + orange dot bottom-right
// Wordmark: Archivo Black with orange period

function HiredMark({ size = 32, className = "" }) {
  // Sized proportionally to the original 110px hero (h=58, dot=14, dot offset=18)
  const fontSize = size * (58 / 110);
  const dotSize = size * (14 / 110);
  const dotOffset = size * (18 / 110);
  return (
    <div className={className} style={{
      width: size, height: size, borderRadius: "50%",
      background: "var(--brand-ink)",
      position: "relative",
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0
    }}>
      <span style={{
        fontFamily: "'Fraunces', Georgia, serif",
        fontWeight: 900,
        fontSize: fontSize,
        color: "var(--mark-h, #fff)",
        letterSpacing: "-0.05em",
        lineHeight: 1,
        // Optical centering — the serif h sits a touch low without nudge
        marginTop: -size * 0.02
      }}>h</span>
      <span style={{
        position: "absolute",
        bottom: dotOffset, right: dotOffset,
        width: dotSize, height: dotSize, borderRadius: "50%",
        background: "var(--brand-orange)"
      }}></span>
    </div>
  );
}

function HiredWordmark({ size = 22, color }) {
  return (
    <span style={{
      fontFamily: "'Archivo', system-ui, sans-serif",
      fontWeight: 900,
      fontSize: size,
      letterSpacing: "-0.04em",
      lineHeight: 1,
      color: color || "var(--ink)"
    }}>
      hired<span style={{ color: "var(--brand-orange)" }}>.</span>
    </span>
  );
}

// Horizontal lockup (sidebar default)
function HiredLockup({ markSize = 30, wordSize = 20, gap = 10 }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap }}>
      <HiredMark size={markSize} />
      <HiredWordmark size={wordSize} />
    </div>
  );
}

// Stacked lockup (onboarding hero)
function HiredStacked({ markSize = 64, wordSize = 28, gap = 14 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap }}>
      <HiredMark size={markSize} />
      <HiredWordmark size={wordSize} />
    </div>
  );
}

// In dark mode, mark inverts: white circle, dark "h"
// We toggle via CSS var on <html data-theme="dark">
const __injectMarkVars = () => {
  if (document.getElementById("hired-mark-vars")) return;
  const s = document.createElement("style");
  s.id = "hired-mark-vars";
  s.textContent = `
    :root { --mark-h: #fff; }
    html[data-theme="dark"] { --mark-h: #1a1a1a; }
  `;
  document.head.appendChild(s);
};
__injectMarkVars();

Object.assign(window, { HiredMark, HiredWordmark, HiredLockup, HiredStacked });
