import type { ComponentType } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  FileSearch,
  LogIn,
  Layers3,
  LockKeyhole,
  PenLine,
  Radar,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiUrl } from "@/lib/api-client";


type Capability = {
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
};


const capabilities: Capability[] = [
  {
    title: "Decode the job",
    description:
      "Turn a pasted job description into structured signals: responsibilities, keywords, seniority, and likely evaluation criteria.",
    icon: FileSearch,
  },
  {
    title: "Match against verified facts",
    description:
      "Compare job requirements to user-provided resume and profile evidence without inventing skills, companies, or metrics.",
    icon: ShieldCheck,
  },
  {
    title: "Shape targeted resume drafts",
    description:
      "Plan role-specific versions that highlight relevant facts while preserving the user's real experience.",
    icon: PenLine,
  },
  {
    title: "Track application context",
    description:
      "Keep job notes, resume versions, gaps, and follow-up context organized in one focused workspace.",
    icon: Layers3,
  },
];


const workflowSteps = [
  "Paste a job description or URL",
  "Review extracted role signals",
  "Confirm profile evidence",
  "Prepare a tailored draft",
];


const workspaceSignals = [
  {
    label: "Verified profile",
    value: "User-provided facts",
  },
  {
    label: "Job input",
    value: "Manual review",
  },
  {
    label: "Template source",
    value: "Saved LaTeX",
  },
];


function PublicBrand() {
  return (
    <Link className="flex items-center gap-3" href="/">
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-950 text-base font-bold text-white shadow-sm">
        AW
      </div>
      <span className="text-xl font-semibold tracking-normal text-slate-950">
        ApplyWise AI
      </span>
    </Link>
  );
}


function ProductPreview() {
  return (
    <div className="relative pb-14">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-[0_30px_90px_rgba(15,23,42,0.12)]">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-base font-semibold text-slate-950">
              Tailoring Workspace
            </p>
            <p className="mt-1 text-sm font-medium text-slate-500">
              Verified inputs first
            </p>
          </div>
          <Badge className="bg-[#f9735b] text-white hover:bg-[#f9735b]">
            Workspace
          </Badge>
        </div>

        <div className="rounded-lg border border-slate-200 p-5">
          <div className="mb-4 h-2 w-32 rounded-full bg-blue-600" />
          <div className="space-y-3">
            <div className="h-2.5 rounded-full bg-slate-200" />
            <div className="h-2.5 w-5/6 rounded-full bg-slate-200" />
            <div className="h-2.5 w-3/5 rounded-full bg-slate-200" />
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-emerald-100 bg-emerald-100 p-5">
            <p className="text-sm font-semibold text-emerald-950">
              Resume source
            </p>
            <p className="mt-4 text-2xl font-semibold tracking-normal text-emerald-950">
              Verified facts
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-semibold text-slate-500">Job context</p>
            <p className="mt-4 text-2xl font-semibold tracking-normal text-slate-950">
              User pasted
            </p>
          </div>
        </div>
      </div>

      <div className="absolute bottom-0 left-6 right-6 hidden rounded-lg border border-slate-200 bg-white/95 p-4 shadow-[0_18px_55px_rgba(15,23,42,0.12)] backdrop-blur md:block">
        <div className="grid gap-3 md:grid-cols-3">
          {workspaceSignals.map((row) => (
            <div key={row.label}>
              <p className="text-xs font-semibold uppercase text-slate-400">
                {row.label}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-800">
                {row.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


export default function Home() {
  return (
    <main className="min-h-screen bg-white text-slate-950">
      <div className="h-2 bg-[linear-gradient(90deg,#2563eb,#16a34a,#f9735b)]" />

      <section className="border-b border-slate-200">
        <div className="mx-auto flex min-h-[92vh] max-w-7xl flex-col px-6 py-8 sm:px-8 lg:px-10">
          <header className="flex items-center justify-between gap-4">
            <PublicBrand />
            <nav className="hidden items-center gap-7 text-sm font-medium text-slate-500 md:flex">
              <a className="transition hover:text-slate-950" href="#capabilities">
                Capabilities
              </a>
              <a className="transition hover:text-slate-950" href="#workflow">
                Workflow
              </a>
              <a className="transition hover:text-slate-950" href="#guardrails">
                Guardrails
              </a>
            </nav>
            <div className="flex items-center gap-2">
              <Button asChild className="bg-white text-slate-950 hover:bg-slate-50" variant="outline">
                <Link href="/login">
                  <LogIn />
                  Log in
                </Link>
              </Button>
              <Button asChild className="bg-slate-950 text-white hover:bg-slate-800">
                <a href={apiUrl("/auth/google/login")}>Continue with Google</a>
              </Button>
            </div>
          </header>

          <div className="grid flex-1 items-center gap-14 py-16 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="max-w-3xl">
              <Badge className="mb-6 bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-950 hover:bg-emerald-100">
                AI-assisted job intelligence
              </Badge>
              <h1 className="max-w-4xl text-5xl font-semibold leading-[1.02] tracking-normal text-slate-950 sm:text-6xl 2xl:text-8xl">
                ApplyWise AI
              </h1>
              <p className="mt-8 max-w-2xl text-xl leading-9 text-slate-600">
                A focused workspace for understanding job descriptions,
                identifying fit, and tailoring resumes from verified
                user-provided experience.
              </p>
              <div className="mt-10 flex flex-col gap-3 sm:flex-row">
                <Button
                  asChild
                  className="h-12 bg-blue-600 px-7 text-base text-white hover:bg-blue-700"
                >
                  <a href={apiUrl("/auth/google/login")}>
                    Get Started
                    <ArrowRight />
                  </a>
                </Button>
                <Button asChild className="h-12 px-7 text-base" variant="outline">
                  <Link href="/login">Log in</Link>
                </Button>
              </div>
            </div>

            <ProductPreview />
          </div>
        </div>
      </section>

      <section className="bg-slate-50" id="capabilities">
        <div className="mx-auto max-w-7xl px-6 py-20 sm:px-8 lg:px-10">
          <div className="mb-10 max-w-3xl">
            <Badge className="mb-4" variant="outline">
              What it can do
            </Badge>
            <h2 className="text-4xl font-semibold tracking-normal text-slate-950">
              Job search work, organized around truth.
            </h2>
            <p className="mt-4 text-lg leading-8 text-slate-600">
              ApplyWise is designed to help users move from messy job posts to
              clear, evidence-backed application material.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {capabilities.map((capability) => {
              const Icon = capability.icon;

              return (
                <article
                  className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
                  key={capability.title}
                >
                  <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-lg bg-slate-950 text-white">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-950">
                    {capability.title}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    {capability.description}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-white" id="workflow">
        <div className="mx-auto grid max-w-7xl gap-10 px-6 py-20 sm:px-8 lg:grid-cols-[0.75fr_1.25fr] lg:px-10">
          <div>
            <Badge className="mb-4 bg-blue-50 text-blue-700 hover:bg-blue-50">
              Workflow
            </Badge>
            <h2 className="text-4xl font-semibold tracking-normal text-slate-950">
              A calmer way to prepare each application.
            </h2>
            <p className="mt-4 text-lg leading-8 text-slate-600">
              The product experience is meant to feel like a review room, not a
              black box. Each step keeps the user in control.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {workflowSteps.map((step, index) => (
              <div className="rounded-lg border border-slate-200 bg-white p-6" key={step}>
                <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-sm font-semibold text-slate-950">
                  {index + 1}
                </div>
                <h3 className="text-lg font-semibold text-slate-950">{step}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  {index === 0
                    ? "LinkedIn can be represented by a manually pasted URL or job description, with no scraping automation."
                    : "The workspace keeps profile facts, resume templates, and job context separated so users can verify inputs before tailoring."}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        className="border-y border-slate-200 bg-slate-950 text-white"
        id="guardrails"
      >
        <div className="mx-auto grid max-w-7xl gap-8 px-6 py-16 sm:px-8 lg:grid-cols-3 lg:px-10">
          <div className="lg:col-span-1">
            <Badge className="mb-4 bg-white text-slate-950 hover:bg-white">
              Product guardrails
            </Badge>
            <h2 className="text-3xl font-semibold tracking-normal">
              Built for credible applications.
            </h2>
          </div>

          <div className="grid gap-4 md:grid-cols-3 lg:col-span-2">
            {[
              {
                icon: LockKeyhole,
                title: "User-owned data",
                text: "Resume and profile facts must come from the user.",
              },
              {
                icon: BadgeCheck,
                title: "No invention",
                text: "No fabricated companies, projects, skills, or metrics.",
              },
              {
                icon: Radar,
                title: "Manual job inputs",
                text: "Job descriptions and URLs are pasted by the user.",
              },
            ].map((item) => {
              const Icon = item.icon;

              return (
                <div
                  className="rounded-lg border border-white/15 bg-white/5 p-5"
                  key={item.title}
                >
                  <Icon className="mb-4 h-5 w-5 text-emerald-300" />
                  <h3 className="font-semibold">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-300">
                    {item.text}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-14 sm:px-8 md:flex-row md:items-center md:justify-between lg:px-10">
          <div>
            <p className="text-sm font-semibold uppercase text-slate-400">
              Workspace
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">
              Start with your profile and templates.
            </h2>
          </div>
          <Button asChild className="bg-blue-600 text-white hover:bg-blue-700">
            <a href={apiUrl("/auth/google/login")}>
              Continue with Google
              <ArrowRight />
            </a>
          </Button>
        </div>
      </section>
    </main>
  );
}
