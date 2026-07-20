# Phase 10 — CV-Templates, Lücken-Erkennung & Evaluation — v0.6.0 (Ziel)

**Status:** 🟡 PLANNED — noch **nicht** im Code
**Spec:** `.claude/specs/PHASE_10_templates_and_evaluation.md`
**Basis:** `docs/PROJECT_DOC.md` §2.3 Future Work

> **Achtung — Scope-Wechsel.** Phase 10 war ursprünglich „Email-Reading (Gmail)
> + Status-Auto-Detect". Das ist **zurückgestellt**, nicht gestrichen. Kurz:
> Gmail-OAuth verlangt dauerhaften Lesezugriff auf das gesamte Postfach und
> passt damit nicht zur Privacy-Aussage in §7 — und es ist der *größte*, nicht
> der kleinste offene Punkt. Ausführliche Begründung in der Spec unter
> „Why not email reading".

## Scope

1. **CV-Template-Export.** Hired. schneidet einen Lebenslauf heute nur zu, gibt
   aber nie ein formatiertes Dokument aus. Die geparsten Daten liegen bereits
   strukturiert in `profile.cv_parsed_json`, PDF-Export existiert in
   `frontend/src/lib/pdf.ts`. Wir erzeugen **LaTeX-Quelltext und kompilieren
   nicht selbst** (ADR-0011): TeX Live wiegt Gigabytes; ein Bundle würde dem
   schlanken lokalen Install widersprechen. Nutzer kompilieren lokal oder in
   Overleaf. HTML/CSS-Templates über Print-to-PDF folgen optional.
2. **Missing-Information-Detection.** Das Parsing erfindet nichts (`parse_cv`
   liefert `null`), aber niemand sagt dem Nutzer, *was fehlt*. Ein Lebenslauf
   ohne Skills-Sektion führt zu durchweg niedrigen Scores — der Feed sieht
   kaputt aus, ohne erkennbaren Grund.
3. **Evaluation gegen einen echten Provider.** `eval/run_eval.py` und
   `eval/bias_audit.py` liefen bisher nur gegen `MockProvider`; drei Metriken in
   §12 stehen deshalb auf „not measured".
4. **Installer-Größe senken.** Das Voice-Bundling in v0.5.0 hat die Installer
   um das Drei- bis Vierfache wachsen lassen — Runtime-Libraries, nicht Modelle.

## Übernommen aus dem alten Phase-10-Plan

Die alte Fassung führte drei Backend-Punkte aus Phase 7 mit. Stand jetzt:

- ✅ **#19** CompanyMark-Fallback / Company-Parser — erledigt in v0.5.0.
- ✅ **#20** Title-Parsing (z. B. Bitpanda) — erledigt in v0.5.0.
- 🟡 **#21** Score auf `ApplicationSummary` (JOIN mit `jobs`) → `MatchRing` in
  Kanban- und Detail-Ansicht. **Weiterhin offen**, wandert in diese Phase.

## PR-Schnitt

Sieben PRs, neun falls beide Template-Engines landen. Tracks B–D sind
unabhängig; nur der Template-Strang (1–3) ist eine Kette.

| # | PR | Track | Aufwand |
|---|---|---|---|
| 1 | `docs: ADR-0011 CV template export strategy` | A | 1 h |
| 2 | `feat: render parsed CV to .tex (moderncv)` | A | ~1 Tag |
| 3 | `feat: template picker + download` | A | ~0,5 Tag |
| 4 | `feat: flag missing CV sections after parsing` | B | ~0,5 Tag |
| 5 | `docs: eval results against the Anthropic API` | C | ~2 h |
| 6 | `perf: exclude GPU execution providers from the bundle` | D | ~0,5 Tag |
| 7 | `chore: release v0.6.0` | — | 1 h |

Optional als achter PR: **#21** (`feat: score on ApplicationSummary`) — ein JOIN,
kein neuer Endpunkt.

PR 6 braucht evtl. eine zweite Runde, falls das Entfernen der GPU-Provider den
macOS- oder Linux-Build bricht. PR 4 lässt sich in Backend und Frontend teilen.

## Definition of Done

Vollständige Kriterien in der Spec. Kurz:

- [ ] ADR-0011 hält die Entscheidung „Quelltext ja, Compiler nein" fest.
- [ ] Ein geparster CV exportiert nach `.tex` und kompiliert unter `moderncv` —
      auch mit LaTeX-Sonderzeichen (`&`, `%`, `_`, `#`, `\`) in den Daten.
- [ ] Ein CV ohne Skills-Sektion erzeugt eine sichtbare Warnung, die die
      *Folge* erklärt, nicht nur die Lücke.
- [ ] `docs/eval-results.md` enthält echte Zahlen; §12 verweist darauf.
- [ ] Installer-Größe vorher/nachher gemessen und im Changelog dokumentiert.
- [ ] Alle drei Plattformen bauen, und ein Packaged Build meldet weiterhin
      `deps_available: true` für Voice.
- [ ] Erledigte Punkte sind aus PROJECT_DOC §2.3 herausgezogen.

## Out-of-scope / Deferrals

- Email-Reading (Gmail) + Status-Auto-Detect → zurückgestellt, eigene Phase mit
  eigenem ADR zur Privacy-Abwägung.
- Auto-Crawl, Auto-Submit, Auto-Reply → Phasen 11–13.
- TeX-Compiler bündeln → explizit verworfen, siehe ADR-0011.
