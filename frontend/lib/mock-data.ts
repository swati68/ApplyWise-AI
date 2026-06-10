export type Metric = {
  label: string;
  value: string;
  helper: string;
};


export type Job = {
  company: string;
  role: string;
  location: string;
  stage: "Researching" | "Tailoring" | "Ready";
  score: number;
  source: "Manual JD" | "Pasted URL";
  updatedAt: string;
  highlights: string[];
};


export type ResumeDraft = {
  name: string;
  targetRole: string;
  status: "Draft" | "Review" | "Ready";
  alignment: number;
  updatedAt: string;
};


export type ProfileSection = {
  title: string;
  status: string;
  completeness: number;
  details: string;
};


export const workspaceMetrics: Metric[] = [
  {
    label: "Verified facts",
    value: "42",
    helper: "Profile statements available for tailoring",
  },
  {
    label: "Active job tracks",
    value: "8",
    helper: "Manual job descriptions under review",
  },
  {
    label: "Resume drafts",
    value: "3",
    helper: "Targeted versions in progress",
  },
  {
    label: "Average alignment",
    value: "74%",
    helper: "Across active job tracks",
  },
];


export const jobs: Job[] = [
  {
    company: "Northstar Health",
    role: "Product Manager, AI Workflows",
    location: "Remote",
    stage: "Tailoring",
    score: 82,
    source: "Manual JD",
    updatedAt: "Today",
    highlights: ["Healthcare SaaS", "Workflow automation", "Stakeholder discovery"],
  },
  {
    company: "BrightLedger",
    role: "Senior Backend Engineer",
    location: "New York, NY",
    stage: "Researching",
    score: 68,
    source: "Pasted URL",
    updatedAt: "Yesterday",
    highlights: ["Python", "PostgreSQL", "API reliability"],
  },
  {
    company: "CivicStack",
    role: "Full Stack Engineer",
    location: "Hybrid",
    stage: "Ready",
    score: 91,
    source: "Manual JD",
    updatedAt: "May 15",
    highlights: ["Next.js", "FastAPI", "Design systems"],
  },
];


export const resumeDrafts: ResumeDraft[] = [
  {
    name: "AI Product Manager Resume",
    targetRole: "Product Manager, AI Workflows",
    status: "Review",
    alignment: 82,
    updatedAt: "Today",
  },
  {
    name: "Backend Platform Resume",
    targetRole: "Senior Backend Engineer",
    status: "Draft",
    alignment: 68,
    updatedAt: "Yesterday",
  },
  {
    name: "Full Stack SaaS Resume",
    targetRole: "Full Stack Engineer",
    status: "Ready",
    alignment: 91,
    updatedAt: "May 15",
  },
];


export const profileSections: ProfileSection[] = [
  {
    title: "Identity",
    status: "Verified",
    completeness: 100,
    details: "Name, email, location, and portfolio links are present.",
  },
  {
    title: "Experience",
    status: "Needs review",
    completeness: 72,
    details: "Three roles are present; impact metrics need confirmation.",
  },
  {
    title: "Skills",
    status: "In progress",
    completeness: 64,
    details: "Technical and domain skills are grouped for job matching.",
  },
  {
    title: "Projects",
    status: "Sparse",
    completeness: 38,
    details: "Project facts are limited and should stay user-verified.",
  },
];


export const recentActivity = [
  "Added CivicStack job description",
  "Updated Full Stack SaaS resume draft",
  "Flagged missing metric in profile experience",
  "Created Backend Platform resume draft",
];


export const settingsRows = [
  {
    label: "Profile data policy",
    value: "Use verified user-provided data only",
  },
  {
    label: "Job input mode",
    value: "Manual job descriptions and pasted URLs",
  },
  {
    label: "Resume export",
    value: "Not configured yet",
  },
];
