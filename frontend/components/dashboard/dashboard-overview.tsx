"use client";

import Link from "next/link";
import {
  AlertCircle,
  BriefcaseBusiness,
  Clock3,
  FileCode2,
  FileText,
  Loader2,
  Play,
  ShieldCheck,
  Star,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { MetricCard } from "@/components/metric-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ProfileData,
  profileApi,
} from "@/lib/profile-api";
import {
  type JobPosting,
  jobsApi,
} from "@/lib/jobs-api";
import {
  type ResumeTemplate,
  resumeTemplateApi,
} from "@/lib/resume-template-api";
import {
  type SchedulerPreference,
  type SchedulerRun,
  schedulerApi,
} from "@/lib/scheduler-api";


const emptyProfileData: ProfileData = {
  education: [],
  experience: [],
  projects: [],
  skills: [],
};


function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}


function countProfileFacts(data: ProfileData) {
  return (
    data.education.length +
    data.experience.length +
    data.projects.length +
    data.skills.length
  );
}


type DashboardJobStats = {
  activeJobs: number;
  matchedJobs: number;
  resumesGenerated: number;
  totalJobs: number;
};


function buildDashboardJobStats(jobs: JobPosting[]): DashboardJobStats {
  return jobs.reduce<DashboardJobStats>(
    (stats, job) => ({
      activeJobs: stats.activeJobs + (isActiveJob(job) ? 1 : 0),
      matchedJobs:
        stats.matchedJobs + (isMatchedJob(job) || job.latestMatch !== null ? 1 : 0),
      resumesGenerated:
        stats.resumesGenerated + (jobHasGeneratedResume(job) ? 1 : 0),
      totalJobs: stats.totalJobs + 1,
    }),
    {
      activeJobs: 0,
      matchedJobs: 0,
      resumesGenerated: 0,
      totalJobs: 0,
    },
  );
}


function normalizedStatusName(job: JobPosting): string {
  return (job.currentStatus?.name ?? formatJobStatus(job.status)).trim().toLowerCase();
}


function formatJobStatus(status: JobPosting["status"]): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}


function currentStatusLabel(job: JobPosting): string {
  return job.currentStatus?.name ?? formatJobStatus(job.status);
}


function isMatchedJob(job: JobPosting): boolean {
  return normalizedStatusName(job) === "matched" || job.status === "matched";
}


function jobHasGeneratedResume(job: JobPosting): boolean {
  return (
    job.latestGeneratedResume !== null ||
    normalizedStatusName(job) === "resume generated" ||
    job.status === "resume_generated" ||
    job.status === "emailed"
  );
}


function isActiveJob(job: JobPosting): boolean {
  return [
    "applied",
    "phone screen",
    "interview 1",
    "interview 2",
    "offer",
  ].includes(normalizedStatusName(job));
}


function sortByNewestJob(jobs: JobPosting[]): JobPosting[] {
  return [...jobs].sort(
    (firstJob, secondJob) =>
      new Date(secondJob.createdAt).getTime() - new Date(firstJob.createdAt).getTime(),
  );
}


function formatDateTime(value: string): string {
  if (value === "") {
    return "Not scheduled";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


function schedulerStatusLabel(status: SchedulerRun["status"]): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}


export function DashboardOverview() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<ProfileData>(emptyProfileData);
  const [isRunningScheduler, setIsRunningScheduler] = useState(false);
  const [schedulerNotice, setSchedulerNotice] = useState<string | null>(null);
  const [schedulerPreference, setSchedulerPreference] =
    useState<SchedulerPreference | null>(null);
  const [schedulerRuns, setSchedulerRuns] = useState<SchedulerRun[]>([]);
  const [templates, setTemplates] = useState<ResumeTemplate[]>([]);
  const [jobs, setJobs] = useState<JobPosting[]>([]);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboardData() {
      try {
        const [
          nextProfileData,
          nextTemplates,
          nextJobs,
          nextSchedulerPreference,
          nextSchedulerRuns,
        ] = await Promise.all([
          profileApi.list(),
          resumeTemplateApi.list(),
          jobsApi.list(),
          schedulerApi.preferences(),
          schedulerApi.runs(),
        ]);

        if (isMounted) {
          setProfileData(nextProfileData);
          setTemplates(nextTemplates);
          setJobs(nextJobs);
          setSchedulerPreference(nextSchedulerPreference);
          setSchedulerRuns(nextSchedulerRuns);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(getErrorMessage(error));
        }
      }
    }

    void loadDashboardData();

    return () => {
      isMounted = false;
    };
  }, []);

  const sectionCounts = useMemo(
    () => [
      { label: "Education", value: profileData.education.length },
      { label: "Experience", value: profileData.experience.length },
      { label: "Projects", value: profileData.projects.length },
      { label: "Skills", value: profileData.skills.length },
    ],
    [profileData],
  );

  const completedSections = sectionCounts.filter((section) => section.value > 0).length;
  const defaultTemplate = templates.find((template) => template.isDefault);
  const jobStats = useMemo(() => buildDashboardJobStats(jobs), [jobs]);
  const recentJobs = useMemo(() => sortByNewestJob(jobs).slice(0, 5), [jobs]);
  const lastSchedulerRun = schedulerRuns[0] ?? null;

  async function handleRunNow() {
    setIsRunningScheduler(true);
    setSchedulerNotice(null);
    setErrorMessage(null);

    try {
      const run = await schedulerApi.runNow();
      const nextRuns = await schedulerApi.runs();
      setSchedulerRuns(nextRuns.length > 0 ? nextRuns : [run]);
      setSchedulerNotice("Scheduler run completed.");
    } catch (error) {
      setSchedulerNotice(getErrorMessage(error));
    } finally {
      setIsRunningScheduler(false);
    }
  }

  return (
    <div className="space-y-6">
      {errorMessage ? (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex gap-3 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <h2 className="font-semibold text-destructive">Workspace data unavailable</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {errorMessage}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          helper="Education, experience, projects, and skills saved in profile"
          icon={ShieldCheck}
          label="Verified facts"
          tone="emerald"
          value={String(countProfileFacts(profileData))}
        />
        <MetricCard
          helper="Profile sections with at least one saved record"
          icon={UserRound}
          label="Profile sections"
          tone="blue"
          value={`${completedSections}/4`}
        />
        <MetricCard
          helper="Saved LaTeX templates"
          icon={FileCode2}
          label="Resume templates"
          tone="coral"
          value={String(templates.length)}
        />
        <MetricCard
          helper={defaultTemplate?.name ?? "No default template selected"}
          icon={FileText}
          label="Default template"
          tone="slate"
          value={defaultTemplate ? "Set" : "None"}
        />
      </section>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Clock3 className="h-4 w-4 text-primary" />
                <CardTitle>Automation</CardTitle>
              </div>
              <CardDescription>
                Scheduled GitHub scans, resume generation, Drive upload, and digest delivery.
              </CardDescription>
            </div>
            <Button disabled={isRunningScheduler} onClick={handleRunNow} size="sm">
              {isRunningScheduler ? <Loader2 className="animate-spin" /> : <Play />}
              Run Now
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {schedulerNotice ? (
            <div className="rounded-lg border bg-muted/30 p-3 text-sm font-medium">
              {schedulerNotice}
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Scheduler
              </p>
              <p className="mt-1 text-2xl font-semibold">
                {schedulerPreference?.enabled ? "Enabled" : "Disabled"}
              </p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Next run
              </p>
              <p className="mt-1 text-sm font-semibold">
                {formatDateTime(schedulerPreference?.nextRunAt ?? "")}
              </p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Last run
              </p>
              <p className="mt-1 text-sm font-semibold">
                {lastSchedulerRun
                  ? schedulerStatusLabel(lastSchedulerRun.status)
                  : "No runs yet"}
              </p>
            </div>
          </div>

          {lastSchedulerRun ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <RunMetric label="Sources" value={`${lastSchedulerRun.sourcesSucceeded}/${lastSchedulerRun.totalSources}`} />
              <RunMetric label="Inserted" value={String(lastSchedulerRun.jobsInserted)} />
              <RunMetric label="Matched" value={String(lastSchedulerRun.jobsMatched)} />
              <RunMetric label="Resumes" value={String(lastSchedulerRun.resumesGenerated)} />
            </div>
          ) : null}
        </CardContent>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Profile coverage</CardTitle>
            <CardDescription>
              Saved records available for resume and job intelligence workflows.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {sectionCounts.map((section) => (
              <div
                className="flex items-center justify-between rounded-lg border p-4"
                key={section.label}
              >
                <span className="font-medium">{section.label}</span>
                <Badge variant={section.value > 0 ? "secondary" : "outline"}>
                  {section.value} saved
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Resume templates</CardTitle>
            <CardDescription>Saved LaTeX templates in the workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {templates.length === 0 ? (
              <div className="rounded-lg border border-dashed p-6 text-center">
                <FileCode2 className="mx-auto mb-3 h-6 w-6 text-muted-foreground" />
                <h3 className="font-semibold">No templates saved</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Add a LaTeX template from the Resumes area.
                </p>
              </div>
            ) : (
              templates.map((template) => (
                <div
                  className="flex items-center justify-between rounded-lg border p-4"
                  key={template.id}
                >
                  <span className="font-medium">{template.name}</span>
                  {template.isDefault ? (
                    <Badge className="gap-1" variant="secondary">
                      <Star className="h-3 w-3" />
                      Default
                    </Badge>
                  ) : (
                    <Badge variant="outline">Saved</Badge>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <BriefcaseBusiness className="h-4 w-4 text-primary" />
                <CardTitle>Jobs</CardTitle>
              </div>
              <CardDescription>
                Saved jobs, matching outcomes, and generated resume activity.
              </CardDescription>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link href="/jobs/summary">Job Summary</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Saved
              </p>
              <p className="mt-1 text-2xl font-semibold">{jobStats.totalJobs}</p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Matched
              </p>
              <p className="mt-1 text-2xl font-semibold">{jobStats.matchedJobs}</p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Resumes
              </p>
              <p className="mt-1 text-2xl font-semibold">
                {jobStats.resumesGenerated}
              </p>
            </div>
            <div className="rounded-lg border bg-muted/20 p-4">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Applied/interviewing
              </p>
              <p className="mt-1 text-2xl font-semibold">{jobStats.activeJobs}</p>
            </div>
          </div>

          {jobs.length === 0 ? (
            <div className="rounded-lg border border-dashed p-6 text-center">
              <BriefcaseBusiness className="mx-auto mb-3 h-6 w-6 text-muted-foreground" />
              <h3 className="font-semibold">No jobs saved yet</h3>
              <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                Generate from a job URL or run a GitHub pipeline to start tracking
                jobs here.
              </p>
              <Button asChild className="mt-4" size="sm">
                <Link href="/jobs">Search jobs</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <div
                  className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between"
                  key={job.id}
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={job.source === "github" ? "secondary" : "outline"}>
                        {job.source === "github" ? "GitHub" : "Manual"}
                      </Badge>
                      <Badge variant="outline">{currentStatusLabel(job)}</Badge>
                    </div>
                    <p className="mt-2 truncate font-semibold">{job.company}</p>
                    <p className="mt-1 truncate text-sm text-muted-foreground">
                      {job.title}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant="muted">
                      Match {job.latestMatch?.score ?? "Unknown"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


function RunMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}
