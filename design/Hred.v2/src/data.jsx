// Realistic mock data — fictional companies used to avoid trademark issues,
// but inspired by real roles/locations/salaries in the DE/EU tech market.

const JOBS = [
  {
    id: "j1",
    title: "Product Designer",
    company: "Lumen Labs",
    companyInitial: "L",
    tagline: "Dev tools for distributed teams",
    location: "Berlin · Hybrid",
    salary: "€75–90k",
    seniority: "Mid-level",
    posted: "2h ago",
    score: 94,
    scoreReasons: [
      { label: "Design systems experience", weight: 0.96 },
      { label: "B2B SaaS background", weight: 0.91 },
      { label: "Berlin on-site 2x/week match", weight: 0.88 }
    ],
    rationale: "Your Figma system work at Glint directly maps to their current design-token initiative. Salary matches your €80k target.",
    tags: ["Figma", "Design Systems", "B2B SaaS"],
    team: "8 designers",
    stage: "Series B",
    description: "We're rebuilding our core product around a shared design system, and we need a product designer who has done this before. You'll own the component library, partner closely with engineering on tokens, and ship features end-to-end."
  },
  {
    id: "j2",
    title: "Senior UX Designer",
    company: "Northwind Analytics",
    companyInitial: "N",
    tagline: "BI platform for mid-market",
    location: "Remote (EU)",
    salary: "€85–100k",
    seniority: "Senior",
    posted: "5h ago",
    score: 91,
    scoreReasons: [
      { label: "Data visualization portfolio", weight: 0.94 },
      { label: "Remote EU eligibility", weight: 1.0 },
      { label: "Enterprise UX track record", weight: 0.84 }
    ],
    rationale: "Your dashboard redesign case study is exactly the kind of work they need. Fully remote with €90k midpoint.",
    tags: ["Data Viz", "Enterprise", "Remote"],
    team: "4 designers",
    stage: "Series C"
  },
  {
    id: "j3",
    title: "Product Designer, Growth",
    company: "Harbor",
    companyInitial: "H",
    tagline: "Neo-banking for freelancers",
    location: "Berlin · On-site",
    salary: "€70–85k",
    seniority: "Mid-level",
    posted: "8h ago",
    score: 87,
    scoreReasons: [
      { label: "Growth experimentation", weight: 0.89 },
      { label: "Fintech adjacent", weight: 0.72 },
      { label: "On-site flexibility", weight: 0.82 }
    ],
    rationale: "Strong growth-design fit. Slight gap on fintech domain, but your onboarding work at Glint is directly relevant.",
    tags: ["Growth", "Fintech", "Onboarding"]
  },
  {
    id: "j4",
    title: "Senior Product Designer",
    company: "Meridian",
    companyInitial: "M",
    tagline: "Climate tech — carbon accounting",
    location: "Remote (Germany)",
    salary: "€80–95k",
    seniority: "Senior",
    posted: "1d ago",
    score: 82,
    scoreReasons: [
      { label: "Complex data interfaces", weight: 0.88 },
      { label: "Mission-driven teams", weight: 0.95 },
      { label: "Climate domain — new", weight: 0.55 }
    ],
    rationale: "Mission alignment is strong. New domain but their onboarding is gentle according to Glassdoor reviews.",
    tags: ["Climate", "Remote", "Mission-driven"]
  },
  {
    id: "j5",
    title: "UX Designer",
    company: "Fieldstone",
    companyInitial: "F",
    tagline: "Logistics software for SMBs",
    location: "Munich · Hybrid",
    salary: "€60–72k",
    seniority: "Mid-level",
    posted: "1d ago",
    score: 74,
    scoreReasons: [
      { label: "B2B workflow UX", weight: 0.81 },
      { label: "Salary below target", weight: 0.52 },
      { label: "Munich relocation required", weight: 0.48 }
    ],
    rationale: "Good craft fit but salary is ~15% below your €80k target and relocation isn't in your prefs.",
    tags: ["B2B", "Logistics"]
  },
  {
    id: "j6",
    title: "Design Engineer",
    company: "Sable Studio",
    companyInitial: "S",
    tagline: "Creative tools for writers",
    location: "Remote (Global)",
    salary: "€90–110k",
    seniority: "Senior",
    posted: "2d ago",
    score: 71,
    scoreReasons: [
      { label: "Code + design skills", weight: 0.78 },
      { label: "Consumer product domain", weight: 0.65 },
      { label: "Front-end depth required", weight: 0.58 }
    ],
    rationale: "Higher front-end bar than your profile (React + animation heavy). Consider if you want to invest in code skills.",
    tags: ["Design Eng", "Consumer", "Remote"]
  },
  {
    id: "j7",
    title: "Product Designer",
    company: "Kestrel Health",
    companyInitial: "K",
    tagline: "Patient-facing telemedicine",
    location: "Hamburg · Hybrid",
    salary: "€72–84k",
    seniority: "Mid-level",
    posted: "3d ago",
    score: 68,
    scoreReasons: [
      { label: "Consumer product patterns", weight: 0.72 },
      { label: "Healthcare — new domain", weight: 0.5 },
      { label: "Hamburg location", weight: 0.6 }
    ],
    rationale: "Moderate fit. Healthcare is a steep regulatory learning curve but the team is reportedly great.",
    tags: ["Healthcare", "Consumer"]
  },
  {
    id: "j8",
    title: "Interaction Designer",
    company: "Orbital",
    companyInitial: "O",
    tagline: "Developer APIs for geospatial",
    location: "Remote (EU)",
    salary: "€70–85k",
    seniority: "Mid-level",
    posted: "3d ago",
    score: 63,
    scoreReasons: [
      { label: "Complex system UX", weight: 0.74 },
      { label: "Developer audience", weight: 0.66 },
      { label: "Geospatial domain — new", weight: 0.4 }
    ],
    rationale: "Interesting product but geospatial is a niche. Could be a stretch role if you want to specialize.",
    tags: ["DevTools", "APIs", "Remote"]
  }
];

// Kanban applications
const APPLICATIONS = {
  discovered: [
    { id: "a1", company: "Lumen Labs", role: "Product Designer", score: 94, updated: "Today", notes: "Materials ready" },
    { id: "a2", company: "Northwind Analytics", role: "Senior UX Designer", score: 91, updated: "Today" },
    { id: "a3", company: "Meridian", role: "Senior Product Designer", score: 82, updated: "Yesterday" }
  ],
  applied: [
    { id: "a4", company: "Harbor", role: "Product Designer, Growth", score: 87, updated: "2d ago", notes: "Applied via portal" },
    { id: "a5", company: "Driftwood", role: "Product Designer", score: 79, updated: "3d ago" },
    { id: "a6", company: "Cairn Software", role: "UX Designer", score: 76, updated: "4d ago" },
    { id: "a7", company: "Parallel", role: "Senior Designer", score: 84, updated: "5d ago" }
  ],
  interview: [
    { id: "a8", company: "Glint Systems", role: "Product Designer", score: 89, updated: "Today", notes: "Round 2 scheduled Thu" },
    { id: "a9", company: "Basalt", role: "Senior UX Designer", score: 81, updated: "Yesterday", notes: "Take-home due Fri" }
  ],
  offer: [
    { id: "a10", company: "Slate & Co.", role: "Product Designer", score: 88, updated: "2d ago", notes: "€82k · deciding by Mon" }
  ],
  rejected: [
    { id: "a11", company: "Vanta Media", role: "Product Designer", score: 72, updated: "1w ago", notes: "No feedback" },
    { id: "a12", company: "Thornhill", role: "Senior Designer", score: 68, updated: "1w ago", notes: "Role put on hold" },
    { id: "a13", company: "Arcadia", role: "UX Designer", score: 75, updated: "2w ago" }
  ]
};

const REJECTION_PATTERNS = [
  { pattern: "Senior roles with <3y of design systems work", count: 4, severity: "high" },
  { pattern: "Applications without tailored cover letter", count: 3, severity: "medium" },
  { pattern: "Companies with >500 employees", count: 2, severity: "low" }
];

// Interview questions
const INTERVIEW_CATEGORIES = [
  {
    id: "behavioral",
    name: "Behavioral",
    practiced: 7,
    total: 12,
    questions: [
      "Tell me about a time you pushed back on a product decision.",
      "Describe a project where you had to work with difficult stakeholders.",
      "How do you handle receiving harsh design critique?",
      "Walk me through a failure and what you learned.",
    ]
  },
  {
    id: "craft",
    name: "Design Craft",
    practiced: 4,
    total: 10,
    questions: [
      "Walk me through a recent project end-to-end.",
      "How do you balance user needs with business goals?",
      "Explain your process for starting on an ambiguous brief.",
      "How do you measure the success of a design?",
    ]
  },
  {
    id: "systems",
    name: "Design Systems",
    practiced: 2,
    total: 8,
    questions: [
      "How would you structure tokens for a multi-brand product?",
      "When do you promote a pattern into the design system?",
      "How do you handle adoption and governance?",
    ]
  },
  {
    id: "company",
    name: "Company-specific (Lumen)",
    practiced: 1,
    total: 6,
    questions: [
      "Why Lumen Labs specifically?",
      "How would you approach our current design token rollout?",
      "What would your first 30 days look like?",
    ]
  }
];

const SAMPLE_CHAT = [
  { from: "coach", text: "Let's warm up with a behavioral question. Take your time — aim for STAR structure (Situation, Task, Action, Result)." },
  { from: "coach", q: true, text: "Tell me about a time you pushed back on a product decision." },
  { from: "user", text: "At Glint, the PM wanted to ship a simplified onboarding in 2 weeks. I reviewed our drop-off data and found 3 specific friction points that a 2-week scope wouldn't address. I proposed a 4-week alternative with a prototype test in week 2 as an off-ramp if results were weak. We did the test, activation lifted 18%, and we shipped the full scope." },
  { from: "coach", feedback: true, text: "Strong STAR structure and quantified outcome. Two refinements to consider:", bullets: [
    "The 'pushback' moment is light — what did the PM object to? Show the conflict.",
    "Name the specific friction points. Specificity is trust.",
    "Great landing — the 18% lift is memorable."
  ], rating: 4 }
];

// Parsed CV profile (for onboarding review step)
const PARSED_PROFILE = {
  name: "Alex Morgan",
  headline: "Product Designer · Berlin",
  email: "alex.morgan@email.com",
  phone: "+49 151 2345 6789",
  experience: [
    { role: "Product Designer", company: "Glint Systems", period: "2022 — Present", summary: "Led design-system rollout across 4 product areas. Shipped onboarding redesign that lifted activation 18%." },
    { role: "UX Designer", company: "Fable Studio", period: "2020 — 2022", summary: "Consumer product work across mobile and web. Owned the checkout flow and 3 A/B tests that improved conversion 11%." },
    { role: "Junior Designer", company: "Freelance", period: "2019 — 2020", summary: "Brand + product work for 8 early-stage startups." }
  ],
  skills: ["Figma", "Design Systems", "Prototyping", "User Research", "Front-end basics", "Design Ops"],
  education: [
    { degree: "M.A. Interaction Design", school: "HfK Bremen", period: "2017 — 2019" }
  ]
};

window.__DATA__ = { JOBS, APPLICATIONS, REJECTION_PATTERNS, INTERVIEW_CATEGORIES, SAMPLE_CHAT, PARSED_PROFILE };
