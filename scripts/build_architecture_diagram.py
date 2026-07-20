"""Render the Hired. architecture diagram (boxes & arrows) to PNG.

The Requirements template asks for an architecture diagram in section 4.
Drawn programmatically so it can be regenerated when the architecture moves.

Run: uv run --with pillow python build_diagram.py <out.png>
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])

S = 2  # supersample factor, downscaled at the end for clean edges
W, H = 1180 * S, 830 * S

INK = (28, 32, 38)
MUTED = (110, 118, 128)
GREEN = (46, 110, 88)
GREEN_BG = (233, 243, 239)
BLUE_BG = (234, 240, 248)
BLUE = (54, 88, 140)
AMBER_BG = (250, 243, 228)
AMBER = (150, 110, 30)
PAPER = (255, 255, 255)
LINE = (150, 158, 168)


def font(size: int, bold: bool = False):
    names = (
        ["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf"]
    )
    for n in names:
        try:
            return ImageFont.truetype(n, size * S)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)

F_TITLE = font(20, True)
F_BOX = font(13, True)
F_SM = font(10)
F_TINY = font(9)
F_LBL = font(10, True)


def box(x, y, w, h, title, lines=None, fill=PAPER, edge=LINE, tc=INK, radius=10):
    d.rounded_rectangle(
        [x * S, y * S, (x + w) * S, (y + h) * S],
        radius=radius * S,
        fill=fill,
        outline=edge,
        width=2 * S,
    )
    ty = y + (12 if lines else h / 2 - 8)
    d.text(((x + w / 2) * S, ty * S), title, font=F_BOX, fill=tc, anchor="ma")
    if lines:
        for i, ln in enumerate(lines):
            d.text(
                ((x + w / 2) * S, (ty + 21 + i * 15) * S),
                ln,
                font=F_SM,
                fill=MUTED,
                anchor="ma",
            )


def arrow(x1, y1, x2, y2, label=None, dashed=False):
    if dashed:
        total = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        steps = max(int(total / 9), 1)
        for i in range(steps):
            if i % 2:
                continue
            t0, t1 = i / steps, (i + 1) / steps
            d.line(
                [
                    (x1 + (x2 - x1) * t0) * S,
                    (y1 + (y2 - y1) * t0) * S,
                    (x1 + (x2 - x1) * t1) * S,
                    (y1 + (y2 - y1) * t1) * S,
                ],
                fill=LINE,
                width=2 * S,
            )
    else:
        d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=LINE, width=2 * S)
    # arrowhead
    import math

    ang = math.atan2(y2 - y1, x2 - x1)
    for sign in (1, -1):
        a = ang + sign * 2.6
        d.line(
            [x2 * S, y2 * S, (x2 + 9 * math.cos(a)) * S, (y2 + 9 * math.sin(a)) * S],
            fill=LINE,
            width=2 * S,
        )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        tw = d.textlength(label, font=F_TINY) / S
        d.rectangle(
            [(mx - tw / 2 - 4) * S, (my - 8) * S, (mx + tw / 2 + 4) * S, (my + 8) * S],
            fill=PAPER,
        )
        d.text((mx * S, my * S), label, font=F_TINY, fill=MUTED, anchor="mm")


# ── Title ────────────────────────────────────────────────────────────────
d.text((40 * S, 26 * S), "Hired. — System Architecture", font=F_TITLE, fill=INK)
d.text(
    (40 * S, 54 * S),
    "Everything inside the green boundary runs on the user machine. There is no backend operated by us.",
    font=F_SM,
    fill=MUTED,
)

# ── Local machine boundary ───────────────────────────────────────────────
d.rounded_rectangle(
    [30 * S, 84 * S, 800 * S, 792 * S], radius=14 * S, outline=GREEN, width=2 * S
)
d.rectangle([48 * S, 76 * S, 250 * S, 96 * S], fill=PAPER)
d.text((56 * S, 78 * S), "USER'S MACHINE  (local-first)", font=F_LBL, fill=GREEN)

# ── Tauri shell ──────────────────────────────────────────────────────────
box(56, 108, 718, 58, "Tauri 2.x Desktop Shell  (Rust)",
    ["Cross-platform window · native APIs · installer distribution (macOS · Windows · Linux)"],
    fill=BLUE_BG, edge=BLUE, tc=BLUE)

# ── Frontend ─────────────────────────────────────────────────────────────
box(56, 188, 718, 62, "React 18 + TypeScript + Tailwind  (Vite)",
    ["Onboarding wizard · ranked job feed · Kanban dashboard · materials editor · interview coach"])

arrow(415, 250, 415, 288, "HTTP  127.0.0.1:8765")

# ── Backend ──────────────────────────────────────────────────────────────
box(56, 288, 718, 58, "FastAPI Sidecar  (Python 3.11, bundled with PyInstaller)",
    ["50 REST endpoints · business logic · provider routing · background tasks"],
    fill=GREEN_BG, edge=GREEN, tc=GREEN)

# ── Three subsystems ─────────────────────────────────────────────────────
box(56, 380, 228, 96, "LLM Provider  (Protocol)",
    ["11 methods · 5 adapters", "Anthropic API · Claude Code", "Codex CLI · Ollama · Mock"])
box(301, 380, 228, 96, "Job Ingestion",
    ["Paste-URL (primary path)", "7 source modules", "pre-filter before scoring"])
box(546, 380, 228, 96, "On-Device Speech",
    ["Piper — text to speech", "faster-whisper — speech", "to text · no audio uploaded"])

for x in (170, 415, 660):
    arrow(415, 346, x, 378)

# ── Storage ──────────────────────────────────────────────────────────────
# Each subsystem sits directly above the store it uses.
arrow(170, 476, 170, 516)   # LLM Provider -> OS Keychain (reads the API key)
arrow(415, 476, 415, 516)   # Job Ingestion -> SQLite (writes jobs)
arrow(660, 476, 660, 516)   # Speech -> Model Cache
arrow(212, 476, 372, 516)   # LLM Provider -> SQLite (call + token log)

box(56, 518, 228, 88, "OS Keychain",
    ["Keychain · Credential Manager", "· Secret Service", "API keys never in the DB"],
    fill=AMBER_BG, edge=AMBER, tc=AMBER)
box(301, 518, 228, 88, "SQLite  — source of truth",
    ["~/.hired/data.db", "profile · jobs · applications", "12 Alembic migrations"],
    fill=AMBER_BG, edge=AMBER, tc=AMBER)
box(546, 518, 228, 88, "Model Cache",
    ["~/.hired/models/", "Piper voices + whisper", "downloaded once, then offline"],
    fill=AMBER_BG, edge=AMBER, tc=AMBER)

d.text((415 * S, 632 * S),
       "All user data — CV, jobs, applications, generated materials, interview transcripts — stays here.",
       font=F_SM, fill=MUTED, anchor="ma")
d.text((415 * S, 650 * S),
       "Uninstalling removes 100% of it. One click wipes it from inside the app.",
       font=F_SM, fill=MUTED, anchor="ma")

# ── Evaluation / quality box ─────────────────────────────────────────────
box(56, 676, 718, 96, "Quality & Evaluation  (development-time)",
    ["Versioned prompts in backend/prompts/  ·  goldset of 20 CV/job pairs  ·  name-swap bias audit",
     "MockProvider is the default in tests: 333 backend + 149 frontend tests run with no network and no cost",
     "GitHub Actions: lint · typecheck · tests · OpenAPI drift guard · 3-OS installer build"])

# ── External services ────────────────────────────────────────────────────
d.text((850 * S, 78 * S), "LEAVES THE DEVICE", font=F_LBL, fill=MUTED)

box(836, 108, 310, 128, "LLM Provider  (user chooses one)",
    ["Anthropic API — pay-per-token, canonical",
     "Claude Code CLI — user's Claude subscription",
     "OpenAI Codex CLI — user's ChatGPT subscription",
     "Ollama — localhost:11434, never leaves device",
     "Company research adds a live web search"])

box(836, 260, 310, 104, "Job Sources  (public pages)",
    ["Pasted URLs — the reliable path",
     "Wellfound · Indeed · Remotive · StepStone",
     "Greenhouse · Lever by board URL",
     "LinkedIn via Playwright — fragile by design"])

box(836, 388, 310, 86, "Hugging Face",
    ["One-time download of Piper voice",
     "models and the whisper model.",
     "Nothing is uploaded."])

arrow(774, 172, 834, 172, dashed=True)
arrow(774, 428, 834, 310, dashed=True)
arrow(774, 428, 834, 430, dashed=True)

d.text((991 * S, 500 * S), "Only a single prompt, a public page", font=F_SM, fill=MUTED, anchor="ma")
d.text((991 * S, 517 * S), "request, or a model download ever", font=F_SM, fill=MUTED, anchor="ma")
d.text((991 * S, 534 * S), "crosses this boundary.", font=F_SM, fill=MUTED, anchor="ma")

img.resize((W // S, H // S), Image.LANCZOS).save(OUT, "PNG")
print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
