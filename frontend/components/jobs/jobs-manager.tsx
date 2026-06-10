"use client";

import Link from "next/link";
import {
  AlertCircle,
  BriefcaseBusiness,
  CalendarDays,
  ChevronDown,
  CheckCircle2,
  ExternalLink,
  FileText,
  Filter,
  GitBranch,
  History,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
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
  type ManualGenerateResult,
  type JobStatusHistoryItem,
  type JobPosting,
  type JobStatus,
  jobsApi,
} from "@/lib/jobs-api";
import {
  type GithubJobSource,
  type GithubJobSourceValues,
  type GithubSourceRunSummary,
  githubSourcesApi,
} from "@/lib/github-sources-api";
import {
  type CustomJobStatus,
  jobStatusesApi,
} from "@/lib/job-statuses-api";
import {
  type ProfileCompletion,
  getProfileCompletion,
  profileSectionLabels,
} from "@/lib/profile-completion";
import { profileApi } from "@/lib/profile-api";
import { apiUrl } from "@/lib/api-client";
import { cn } from "@/lib/utils";


type SearchMode = "manual" | "auto";
type SourceFilter = string;
type StatusFilter = string;


type JobNotice =
  | {
      type: "success";
      text: string;
      job?: JobPosting;
    }
  | {
      type: "duplicate";
      text: string;
      job: JobPosting;
    }
  | {
      type: "error";
      text: string;
    };


type SimpleNotice = {
  type: "success" | "error";
  text: string;
};


type GitHubSummary = {
  lastScanAt: string;
  totalRowsSeen: number;
  parsedJobs: number;
  scannedJobs: number;
  insertedJobs: number;
  duplicateJobs: number;
  rowsSkippedByFilters: number;
  jobsTagged: number;
  extractionSuccessCount: number;
  extractionFailedCount: number;
  matchedJobs: number;
  generatedResumes: number;
  pdfsCompiled: number;
  driveUploadsSuccessful: number;
  emailsSent: number;
  durationSeconds: number;
  runNotes: string[];
};


type JobSummaryStats = {
  totalJobs: number;
  matchedJobs: number;
  resumesGenerated: number;
  appliedInterviewing: number;
  postedLast7Days: number;
};


type ManualStepStatus = "pending" | "running" | "completed" | "failed" | "skipped";


type ManualPipelineStep = {
  key: string;
  label: string;
  status: ManualStepStatus;
  message?: string;
};


const sourceOptions: Array<{ value: SourceFilter; label: string }> = [
  { value: "all", label: "All sources" },
  { value: "manual", label: "Manual" },
];


const JOBS_PER_PAGE = 20;
const MIN_VISIBLE_MATCH_SCORE = 50;


const manualPipelineStepLabels = [
  { key: "save", label: "Saving job" },
  { key: "extract", label: "Extracting job description" },
  { key: "match", label: "Matching profile" },
  { key: "resume", label: "Generating resume" },
  { key: "pdf", label: "Compiling PDF" },
  { key: "drive", label: "Uploading to Drive" },
];


const initialGithubSourceValues: GithubJobSourceValues = {
  name: "",
  repoUrl: "",
  rawReadmeUrl: "",
  branch: "main",
  enabled: true,
  scanRoleTags: [],
  includeKeywords: [],
  excludeKeywords: [],
  scanInstructions: "",
};


const simplifyJobsExample: GithubJobSourceValues = {
  name: "SimplifyJobs Summer 2026 Internships",
  repoUrl: "https://github.com/SimplifyJobs/Summer2026-Internships",
  rawReadmeUrl:
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md",
  branch: "dev",
  enabled: true,
  scanRoleTags: ["Software Engineering", "Backend", "Machine Learning"],
  includeKeywords: [
    "software engineer",
    "backend engineer",
    "AI engineer",
    "ML engineer",
  ],
  excludeKeywords: ["product manager", "designer", "sales", "marketing"],
  scanInstructions:
    "Only scan software engineering internship roles. Ignore product, design, sales, marketing, and business roles.",
};


function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}


function formatStatus(status: JobStatus): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}


function formatDateTime(value: string): string {
  if (value === "") {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


function formatDateOnly(value: string): string {
  if (value === "") {
    return "Unknown";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
  }).format(new Date(value));
}


function formatKnownDateTime(value: string): string {
  return value === "" ? "Unknown" : formatDateTime(value);
}


function formatDuration(totalSeconds: number): string {
  if (totalSeconds <= 0) {
    return "Not available";
  }

  const roundedSeconds = Math.max(1, Math.round(totalSeconds));
  const minutes = Math.floor(roundedSeconds / 60);
  const seconds = roundedSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}


function jobMatchesSearch(job: JobPosting, searchTerm: string): boolean {
  const query = searchTerm.trim().toLowerCase();
  if (query === "") {
    return true;
  }

  return `${job.company} ${job.title} ${job.jobTags.join(" ")}`.toLowerCase().includes(query);
}


function getStatusBadgeVariant(status: JobStatus) {
  if (status === "applied" || status === "matched") {
    return "secondary";
  }
  if (status === "archived") {
    return "muted";
  }

  return "outline";
}


function buildStartedManualSteps(): ManualPipelineStep[] {
  return manualPipelineStepLabels.map((step, index) => ({
    ...step,
    status: index === 0 ? "running" : "pending",
    message: index === 0 ? "Starting manual generation." : undefined,
  }));
}


function markRunningManualStepFailed(message: string): ManualPipelineStep[] {
  return manualPipelineStepLabels.map((step, index) => ({
    ...step,
    status: index === 0 ? "failed" : "pending",
    message: index === 0 ? message : undefined,
  }));
}


function buildManualStepsFromResult(result: ManualGenerateResult): ManualPipelineStep[] {
  const extractionSucceeded = result.extractionResult.extractionSuccess;
  const skippedMatch = result.matchResult?.matchReason.startsWith("Skipped matching") ?? false;
  const matchSucceeded = result.matchResult !== null && !skippedMatch;
  const resumeSucceeded = result.generatedResumeResult !== null;

  return [
    {
      key: "save",
      label: "Saving job",
      status: "completed",
      message: result.duplicate ? "Existing job reused." : "Job saved.",
    },
    {
      key: "extract",
      label: "Extracting job description",
      status: extractionSucceeded ? "completed" : "failed",
      message: extractionSucceeded
        ? extractionSummaryMessage(result)
        : result.extractionResult.errorMessage || "Could not extract a full job description.",
    },
    {
      key: "match",
      label: "Matching profile",
      status: matchSucceeded ? "completed" : extractionSucceeded ? "failed" : "skipped",
      message:
        result.matchResult !== null
          ? skippedMatch
            ? result.matchResult.matchReason
            : `Match score ${result.matchResult.score}.`
          : extractionSucceeded
            ? "Profile matching did not complete."
            : "Skipped because extraction failed.",
    },
    {
      key: "resume",
      label: "Generating resume",
      status: resumeSucceeded ? "completed" : matchSucceeded ? "failed" : "skipped",
      message: resumeSucceeded
        ? "Tailored LaTeX resume generated."
        : matchSucceeded
          ? firstManualError(result) || "Resume generation did not complete."
          : "Skipped until matching completes.",
    },
    {
      key: "pdf",
      label: "Compiling PDF",
      status: pdfStepStatus(result),
      message: pdfStepMessage(result),
    },
    {
      key: "drive",
      label: "Uploading to Drive",
      status: driveStepStatus(result),
      message: driveStepMessage(result),
    },
  ];
}


function extractionSummaryMessage(result: ManualGenerateResult): string {
  const parts = [
    result.extractionResult.companyGuess,
    result.extractionResult.titleGuess,
    result.extractionResult.locationGuess,
  ].filter((value) => value !== "");

  return parts.length > 0
    ? `Extracted ${parts.join(" - ")}.`
    : "Job description extracted.";
}


function firstManualError(result: ManualGenerateResult): string | undefined {
  return result.errors[0];
}


function pdfStepStatus(result: ManualGenerateResult): ManualStepStatus {
  if (result.pdfStatus === null) {
    return result.generatedResumeResult === null ? "skipped" : "pending";
  }
  if (result.pdfStatus.success) {
    return "completed";
  }

  return "failed";
}


function pdfStepMessage(result: ManualGenerateResult): string {
  if (result.pdfStatus === null) {
    return result.generatedResumeResult === null
      ? "Skipped until resume generation completes."
      : "PDF compilation was not started.";
  }
  if (result.pdfStatus.success) {
    return result.pdfStatus.skipped ? "PDF was already compiled." : "PDF compiled.";
  }

  return result.pdfStatus.errorMessage || "PDF compilation failed.";
}


function driveStepStatus(result: ManualGenerateResult): ManualStepStatus {
  if (result.driveStatus === null) {
    return result.generatedResumeResult === null ? "skipped" : "pending";
  }
  if (result.driveStatus.success) {
    return "completed";
  }
  if (result.driveStatus.skipped) {
    return "skipped";
  }

  return "failed";
}


function driveStepMessage(result: ManualGenerateResult): string {
  if (result.driveStatus === null) {
    return result.generatedResumeResult === null
      ? "Skipped until resume generation completes."
      : "Drive upload was not started.";
  }
  if (result.driveStatus.success) {
    return result.driveStatus.skipped
      ? "Drive upload already exists."
      : "PDF uploaded to Google Drive.";
  }
  if (result.driveStatus.skipped) {
    return result.driveStatus.errorMessage || "Drive upload skipped.";
  }

  return result.driveStatus.errorMessage || "Drive upload failed.";
}


function buildGithubPipelineNotice(result: GithubSourceRunSummary): string {
  const durationText =
    result.durationSeconds > 0 ? ` in ${formatDuration(result.durationSeconds)}` : "";
  const incompleteCount = Math.max(result.errors.length, result.extractionFailedCount);

  if (incompleteCount > 0) {
    return `GitHub pipeline completed${durationText}. ${incompleteCount} item${incompleteCount === 1 ? "" : "s"} could not be fully processed.`;
  }

  return `GitHub pipeline completed${durationText}.`;
}


function githubSourceToValues(source: GithubJobSource): GithubJobSourceValues {
  return {
    name: source.name,
    repoUrl: source.repoUrl,
    rawReadmeUrl: source.rawReadmeUrl,
    branch: source.branch,
    enabled: source.enabled,
    scanRoleTags: source.scanRoleTags,
    includeKeywords: source.includeKeywords,
    excludeKeywords: source.excludeKeywords,
    scanInstructions: source.scanInstructions,
  };
}


export function JobsSearchManager() {
  const [activeMode, setActiveMode] = useState<SearchMode>("manual");
  const [githubFormValues, setGithubFormValues] = useState(initialGithubSourceValues);
  const [editingGithubSourceId, setEditingGithubSourceId] = useState<string | null>(null);
  const [githubNotice, setGitHubNotice] = useState<SimpleNotice | null>(null);
  const [githubSources, setGithubSources] = useState<GithubJobSource[]>([]);
  const [isLoadingGithubSources, setIsLoadingGithubSources] = useState(true);
  const [isSavingGithubSource, setIsSavingGithubSource] = useState(false);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [manualJobUrl, setManualJobUrl] = useState("");
  const [manualProgressSteps, setManualProgressSteps] = useState<ManualPipelineStep[]>([]);
  const [manualResult, setManualResult] = useState<ManualGenerateResult | null>(null);
  const [lastGithubScan, setLastGithubScan] = useState<GithubSourceRunSummary | null>(
    null,
  );
  const [notice, setNotice] = useState<JobNotice | null>(null);
  const [profileCompletion, setProfileCompletion] = useState<ProfileCompletion | null>(
    null,
  );
  const [scanningSourceId, setScanningSourceId] = useState<string | null>(null);
  const [selectedGithubSourceId, setSelectedGithubSourceId] = useState("");
  const [showProfileCaution, setShowProfileCaution] = useState(false);

  async function loadGithubSources() {
    setIsLoadingGithubSources(true);
    try {
      const sources = await githubSourcesApi.list();
      setGithubSources(sources);
      setSelectedGithubSourceId((currentSourceId) => {
        if (sources.some((source) => source.id === currentSourceId)) {
          return currentSourceId;
        }

        return sources.find((source) => source.enabled)?.id ?? sources[0]?.id ?? "";
      });
    } catch (error) {
      setGitHubNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsLoadingGithubSources(false);
    }
  }

  useEffect(() => {
    void loadGithubSources();
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadProfileCompletion() {
      try {
        const nextProfileData = await profileApi.list();
        const nextCompletion = getProfileCompletion(nextProfileData);

        if (isMounted) {
          setProfileCompletion(nextCompletion);
          setShowProfileCaution(nextCompletion.percentage < 100);
        }
      } catch {
        if (isMounted) {
          setProfileCompletion(null);
          setShowProfileCaution(false);
        }
      }
    }

    void loadProfileCompletion();

    return () => {
      isMounted = false;
    };
  }, []);

  const githubSummary = useMemo(
    () => getGithubSummary(githubSources, lastGithubScan),
    [githubSources, lastGithubScan],
  );

  const selectedGithubSource = useMemo(
    () => githubSources.find((source) => source.id === selectedGithubSourceId) ?? null,
    [githubSources, selectedGithubSourceId],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice(null);
    setManualResult(null);

    if (manualJobUrl.trim() === "") {
      setNotice({
        type: "error",
        text: "Job posting URL is required.",
      });
      return;
    }

    setIsSaving(true);
    setManualProgressSteps(buildStartedManualSteps());
    try {
      const result = await jobsApi.generateManualFromUrl(manualJobUrl);
      setManualResult(result);
      setManualProgressSteps(buildManualStepsFromResult(result));
      if (result.duplicate) {
        setNotice({
          type: "duplicate",
          text: "This job already exists.",
          job: result.job,
        });
      } else if (result.errors.length > 0) {
        setNotice({
          type: "success",
          text: `Pipeline completed. ${result.errors.length} item${result.errors.length === 1 ? "" : "s"} could not be fully processed.`,
        });
      } else {
        setNotice({
          type: "success",
          text: "Resume generation completed.",
          job: result.job,
        });
        setManualJobUrl("");
      }
    } catch (error) {
      setManualProgressSteps(markRunningManualStepFailed(getErrorMessage(error)));
      setNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsSaving(false);
    }
  }

  async function handleGithubSourceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGitHubNotice(null);

    if (
      githubFormValues.name.trim() === "" ||
      githubFormValues.repoUrl.trim() === "" ||
      githubFormValues.rawReadmeUrl.trim() === "" ||
      githubFormValues.branch.trim() === ""
    ) {
      setGitHubNotice({
        type: "error",
        text: "Name, repository URL, raw README URL, and branch are required.",
      });
      return;
    }

    setIsSavingGithubSource(true);
    try {
      const source =
        editingGithubSourceId === null
          ? await githubSourcesApi.create(githubFormValues)
          : await githubSourcesApi.update(editingGithubSourceId, githubFormValues);
      setGithubSources((currentSources) =>
        editingGithubSourceId === null
          ? [source, ...currentSources]
          : upsertGithubSource(currentSources, source),
      );
      setSelectedGithubSourceId(source.id);
      setGithubFormValues(initialGithubSourceValues);
      setEditingGithubSourceId(null);
      setGitHubNotice({
        type: "success",
        text: editingGithubSourceId === null ? "GitHub source saved." : "GitHub source updated.",
      });
    } catch (error) {
      setGitHubNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsSavingGithubSource(false);
    }
  }

  async function handleToggleGithubSource(source: GithubJobSource) {
    setGitHubNotice(null);
    try {
      const updatedSource = await githubSourcesApi.update(source.id, {
        enabled: !source.enabled,
      });
      setGithubSources((currentSources) => upsertGithubSource(currentSources, updatedSource));
    } catch (error) {
      setGitHubNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    }
  }

  async function handleDeleteGithubSource(sourceId: string) {
    setGitHubNotice(null);
    try {
      await githubSourcesApi.delete(sourceId);
      setGithubSources((currentSources) => {
        const nextSources = currentSources.filter((source) => source.id !== sourceId);
        if (selectedGithubSourceId === sourceId) {
          setSelectedGithubSourceId(
            nextSources.find((source) => source.enabled)?.id ?? nextSources[0]?.id ?? "",
          );
        }

        return nextSources;
      });
      setGitHubNotice({
        type: "success",
        text: "GitHub source deleted.",
      });
    } catch (error) {
      setGitHubNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    }
  }

  async function handleScanGithubSource(sourceId: string) {
    setGitHubNotice(null);
    setScanningSourceId(sourceId);
    try {
      const result = await githubSourcesApi.scan(sourceId);
      setGithubSources((currentSources) => upsertGithubSource(currentSources, result.source));
      setLastGithubScan(result);
      setGitHubNotice({
        type: "success",
        text: result.message,
      });
    } catch (error) {
      setGitHubNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setScanningSourceId(null);
    }
  }

  async function runSelectedGithubPipeline() {
    setGitHubNotice(null);
    if (selectedGithubSource === null) {
      setGitHubNotice({
        type: "error",
        text: "Select a GitHub source before running the pipeline.",
      });
      return;
    }
    if (!selectedGithubSource.enabled) {
      setGitHubNotice({
        type: "error",
        text: "Enable the selected GitHub source before running the pipeline.",
      });
      return;
    }

    setIsRunningPipeline(true);
    try {
      const result = await githubSourcesApi.runPipeline(selectedGithubSource.id);
      setLastGithubScan(result);
      await loadGithubSources();
      setGitHubNotice({
        type: "success",
        text: buildGithubPipelineNotice(result),
      });
    } catch (error) {
      setGitHubNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsRunningPipeline(false);
    }
  }

  return (
    <div className="space-y-6">
      {showProfileCaution && profileCompletion !== null ? (
        <ProfileIncompleteModal
          completion={profileCompletion}
          onClose={() => setShowProfileCaution(false)}
        />
      ) : null}

      <PageHeader
        description="Generate job records and resumes from manual postings or supported GitHub markdown sources."
        eyebrow="Search Jobs"
        title="Search jobs"
      />

      <ModeSwitch activeMode={activeMode} onChange={setActiveMode} />

      {activeMode === "manual" ? (
        <ManualJobPanel
          jobUrl={manualJobUrl}
          isSaving={isSaving}
          manualResult={manualResult}
          notice={notice}
          onJobUrlChange={setManualJobUrl}
          onSubmit={handleSubmit}
          progressSteps={manualProgressSteps}
        />
      ) : (
        <AutoScanPanel
          githubFormValues={githubFormValues}
          githubNotice={githubNotice}
          githubSources={githubSources}
          githubSummary={githubSummary}
          isEditingGithubSource={editingGithubSourceId !== null}
          isLoadingGithubSources={isLoadingGithubSources}
          isRunningPipeline={isRunningPipeline}
          isSavingGithubSource={isSavingGithubSource}
          onDeleteSource={handleDeleteGithubSource}
          onFillExample={() => setGithubFormValues(simplifyJobsExample)}
          onGithubFormChange={setGithubFormValues}
          onCancelEditSource={() => {
            setEditingGithubSourceId(null);
            setGithubFormValues(initialGithubSourceValues);
          }}
          onEditSource={(source) => {
            setEditingGithubSourceId(source.id);
            setGithubFormValues(githubSourceToValues(source));
          }}
          onRunPipeline={runSelectedGithubPipeline}
          onSaveSource={handleGithubSourceSubmit}
          onScanSource={handleScanGithubSource}
          onSelectSource={setSelectedGithubSourceId}
          onToggleSource={handleToggleGithubSource}
          scanningSourceId={scanningSourceId}
          selectedGithubSourceId={selectedGithubSourceId}
        />
      )}
    </div>
  );
}


function ProfileIncompleteModal({
  completion,
  onClose,
}: {
  completion: ProfileCompletion;
  onClose: () => void;
}) {
  const missingLabels = completion.missingSections.map(
    (section) => profileSectionLabels[section],
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <button
        aria-label="Close profile caution"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
        type="button"
      />
      <section
        aria-labelledby="profile-caution-title"
        className="relative w-full max-w-lg overflow-hidden rounded-xl border bg-background shadow-2xl"
        role="dialog"
      >
        <div className="border-b bg-muted/25 p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-amber-600">
              <AlertCircle className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold" id="profile-caution-title">
                Complete your profile before generating
              </h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                ApplyWise can only use verified profile facts. Your profile is{" "}
                {completion.percentage}% complete, so generated resumes may miss
                important context.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4 p-5">
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="text-sm font-semibold">Missing sections</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {missingLabels.map((label) => (
                <Badge key={label} variant="outline">
                  {label}
                </Badge>
              ))}
            </div>
          </div>

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button onClick={onClose} type="button" variant="outline">
              Continue anyway
            </Button>
            <Button asChild type="button">
              <Link href="/profile">Review profile</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}


export function JobSummaryManager() {
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [jobStatuses, setJobStatuses] = useState<CustomJobStatus[]>([]);
  const [githubSources, setGithubSources] = useState<GithubJobSource[]>([]);
  const [notice, setNotice] = useState<SimpleNotice | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [tagFilter, setTagFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedJob, setSelectedJob] = useState<JobPosting | null>(null);
  const [statusHistory, setStatusHistory] = useState<JobStatusHistoryItem[]>([]);
  const [statusHistoryError, setStatusHistoryError] = useState("");
  const [isLoadingStatusHistory, setIsLoadingStatusHistory] = useState(false);
  const [isChangingStatus, setIsChangingStatus] = useState(false);
  const [isSavingJobTags, setIsSavingJobTags] = useState(false);

  async function loadSummaryData() {
    setIsLoadingJobs(true);
    try {
      const [nextJobs, nextStatuses, nextGithubSources] = await Promise.all([
        jobsApi.list(),
        jobStatusesApi.list(),
        githubSourcesApi.list(),
      ]);
      setJobs(nextJobs);
      setJobStatuses(nextStatuses);
      setGithubSources(nextGithubSources);
    } catch (error) {
      setNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsLoadingJobs(false);
    }
  }

  useEffect(() => {
    void loadSummaryData();
  }, []);

  const filteredJobs = useMemo(
    () =>
      jobs.filter((job) => {
        if (!jobMatchesSourceFilter(job, sourceFilter)) {
          return false;
        }
        if (statusFilter !== "all" && currentStatusId(job) !== statusFilter) {
          return false;
        }
        if (
          tagFilter !== "all" &&
          !job.jobTags.some((tag) => tag.toLowerCase() === tagFilter)
        ) {
          return false;
        }

        return jobMatchesSearch(job, searchTerm);
      }),
    [jobs, searchTerm, sourceFilter, statusFilter, tagFilter],
  );
  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / JOBS_PER_PAGE));
  const paginatedJobs = useMemo(() => {
    const startIndex = (currentPage - 1) * JOBS_PER_PAGE;
    return filteredJobs.slice(startIndex, startIndex + JOBS_PER_PAGE);
  }, [currentPage, filteredJobs]);

  const stats = useMemo(() => buildJobSummaryStats(jobs), [jobs]);
  const statusOptions = useMemo(
    () => [
      { value: "all", label: "All statuses" },
      ...jobStatuses.map((statusItem) => ({
        value: statusItem.id,
        label: statusItem.name,
      })),
    ],
    [jobStatuses],
  );
  const summarySourceOptions = useMemo(
    () => [
      ...sourceOptions,
      ...githubSources.map((source) => ({
        value: githubSourceFilterValue(source.id),
        label: source.name,
      })),
    ],
    [githubSources],
  );
  const tagOptions = useMemo(
    () => [
      { value: "all", label: "All tags" },
      ...Array.from(
        new Map(
          jobs
            .flatMap((job) => job.jobTags)
            .map((tag) => [tag.toLowerCase(), tag] as const),
        ).entries(),
      )
        .map(([value, label]) => ({ value, label }))
        .sort((firstOption, secondOption) =>
          firstOption.label.localeCompare(secondOption.label),
        ),
    ],
    [jobs],
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, sourceFilter, statusFilter, tagFilter]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  async function openJobDetails(job: JobPosting) {
    setSelectedJob(job);
    setStatusHistory([]);
    setStatusHistoryError("");
    setIsLoadingStatusHistory(true);
    try {
      setStatusHistory(await jobsApi.listStatusHistory(job.id));
    } catch (error) {
      setStatusHistoryError(getErrorMessage(error));
    } finally {
      setIsLoadingStatusHistory(false);
    }
  }

  async function handleChangeStatus(values: { statusId: string; note: string }) {
    if (selectedJob === null || values.statusId === "") {
      return;
    }

    setIsChangingStatus(true);
    setNotice(null);
    try {
      const updatedJob = await jobsApi.changeStatus(selectedJob.id, values);
      setJobs((currentJobs) =>
        currentJobs.map((job) => (job.id === updatedJob.id ? updatedJob : job)),
      );
      setSelectedJob(updatedJob);
      setStatusHistory(await jobsApi.listStatusHistory(updatedJob.id));
      setNotice({
        type: "success",
        text: "Job status updated.",
      });
    } catch (error) {
      setNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsChangingStatus(false);
    }
  }

  async function handleSaveJobTags(tags: string[]) {
    if (selectedJob === null) {
      return;
    }

    setIsSavingJobTags(true);
    setNotice(null);
    try {
      const updatedJob = await jobsApi.update(selectedJob.id, { jobTags: tags });
      setJobs((currentJobs) =>
        currentJobs.map((job) => (job.id === updatedJob.id ? updatedJob : job)),
      );
      setSelectedJob(updatedJob);
      setNotice({
        type: "success",
        text: "Job tags updated.",
      });
    } catch (error) {
      setNotice({
        type: "error",
        text: getErrorMessage(error),
      });
    } finally {
      setIsSavingJobTags(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        description="Review saved jobs, pipeline state, and resume follow-up status."
        eyebrow="Job Summary"
        title="Job summary"
      />

      {notice ? <SimpleNoticeMessage notice={notice} /> : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryMetric icon={<BriefcaseBusiness className="h-4 w-4" />} label="Total jobs" value={stats.totalJobs} />
        <SummaryMetric label="Matched jobs" value={stats.matchedJobs} />
        <SummaryMetric icon={<FileText className="h-4 w-4" />} label="Resumes generated" value={stats.resumesGenerated} />
        <SummaryMetric label="Applied/interviewing" value={stats.appliedInterviewing} />
        <SummaryMetric icon={<CalendarDays className="h-4 w-4" />} label="Posted last 7 days" value={stats.postedLast7Days} />
      </section>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Saved jobs</CardTitle>
              <CardDescription>
                Filter by source, status, company, or title.
              </CardDescription>
            </div>
            <Badge variant="secondary">
              {filteredJobs.length === 0
                ? "0 shown"
                : `${(currentPage - 1) * JOBS_PER_PAGE + 1}-${(currentPage - 1) * JOBS_PER_PAGE + paginatedJobs.length} of ${filteredJobs.length}`}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-[1fr_220px_200px_200px]">
            <div className="flex h-10 items-center gap-2 rounded-md border bg-background px-3">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                className="h-full min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search company or title"
                value={searchTerm}
              />
            </div>

            <SelectField
              label="Source"
              onChange={(value) => setSourceFilter(value as SourceFilter)}
              options={summarySourceOptions}
              value={sourceFilter}
            />
            <SelectField
              label="Status"
              onChange={(value) => setStatusFilter(value as StatusFilter)}
              options={statusOptions}
              value={statusFilter}
            />
            <SelectField
              label="Job Tag"
              onChange={setTagFilter}
              options={tagOptions}
              value={tagFilter}
            />
          </div>

          {isLoadingJobs ? (
            <LoadingState label="Loading jobs" />
          ) : filteredJobs.length === 0 ? (
            <EmptyState
              description="Generate a manual job, run a GitHub pipeline, or adjust the filters."
              icon={<Filter className="h-6 w-6" />}
              title="No jobs found"
            />
          ) : (
            <>
              <JobsTable jobs={paginatedJobs} onOpenJob={openJobDetails} />
              <PaginationControls
                currentPage={currentPage}
                onPageChange={setCurrentPage}
                pageSize={JOBS_PER_PAGE}
                totalItems={filteredJobs.length}
                totalPages={totalPages}
              />
            </>
          )}
        </CardContent>
      </Card>

      {selectedJob !== null ? (
        <JobDetailDrawer
          history={statusHistory}
          historyError={statusHistoryError}
          isChangingStatus={isChangingStatus}
          isSavingTags={isSavingJobTags}
          isLoadingHistory={isLoadingStatusHistory}
          job={selectedJob}
          onChangeStatus={handleChangeStatus}
          onClose={() => setSelectedJob(null)}
          onSaveTags={handleSaveJobTags}
          statuses={jobStatuses}
        />
      ) : null}
    </div>
  );
}


function ModeSwitch({
  activeMode,
  onChange,
}: {
  activeMode: SearchMode;
  onChange: (mode: SearchMode) => void;
}) {
  return (
    <div className="mx-auto grid max-w-md grid-cols-2 rounded-lg border bg-muted p-1">
      <button
        className={cn(
          "flex h-10 items-center justify-center gap-2 rounded-md text-sm font-semibold transition-colors",
          activeMode === "manual"
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
        onClick={() => onChange("manual")}
        type="button"
      >
        <BriefcaseBusiness className="h-4 w-4" />
        Manual
      </button>
      <button
        className={cn(
          "flex h-10 items-center justify-center gap-2 rounded-md text-sm font-semibold transition-colors",
          activeMode === "auto"
            ? "bg-background text-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
        onClick={() => onChange("auto")}
        type="button"
      >
        <GitBranch className="h-4 w-4" />
        Auto Scan
      </button>
    </div>
  );
}


function ManualJobPanel({
  jobUrl,
  isSaving,
  manualResult,
  notice,
  onJobUrlChange,
  onSubmit,
  progressSteps,
}: {
  jobUrl: string;
  isSaving: boolean;
  manualResult: ManualGenerateResult | null;
  notice: JobNotice | null;
  onJobUrlChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  progressSteps: ManualPipelineStep[];
}) {
  return (
    <section className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <BriefcaseBusiness className="h-5 w-5" />
            </div>
            <div>
              <CardTitle>Generate from Job URL</CardTitle>
              <CardDescription>
                Paste any public job posting URL. We'll extract the JD, match it with your profile, and generate a tailored resume.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={onSubmit}>
            <TextField
              label="Job posting URL"
              onChange={onJobUrlChange}
              placeholder="https://company.com/careers/software-engineer-intern..."
              required
              type="url"
              value={jobUrl}
            />

            {notice ? <NoticeMessage notice={notice} /> : null}

            {progressSteps.length > 0 ? (
              <ManualPipelineProgress steps={progressSteps} />
            ) : null}

            {manualResult !== null ? (
              <ManualGenerateResultSummary result={manualResult} />
            ) : null}

            <div className="flex justify-end">
              <Button disabled={isSaving} type="submit">
                {isSaving ? <Loader2 className="animate-spin" /> : <FileText />}
                Generate
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}


function ManualPipelineProgress({ steps }: { steps: ManualPipelineStep[] }) {
  return (
    <div className="space-y-2 rounded-md border bg-muted/20 p-4">
      {steps.map((step) => {
        const Icon = step.status === "failed" ? AlertCircle : CheckCircle2;
        const isRunning = step.status === "running";

        return (
          <div className="flex gap-3" key={step.key}>
            <div
              className={cn(
                "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border",
                step.status === "completed" && "border-emerald-200 bg-emerald-50 text-emerald-700",
                step.status === "failed" && "border-destructive/30 bg-destructive/5 text-destructive",
                step.status === "running" && "border-primary/30 bg-primary/10 text-primary",
                step.status === "pending" && "border-muted-foreground/20 text-muted-foreground",
                step.status === "skipped" && "border-muted bg-muted text-muted-foreground",
              )}
            >
              {isRunning ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : step.status === "pending" || step.status === "skipped" ? (
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
              ) : (
                <Icon className="h-3.5 w-3.5" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-medium">{step.label}</p>
                <Badge variant={manualStepBadgeVariant(step.status)}>
                  {manualStepStatusLabel(step.status)}
                </Badge>
              </div>
              {step.message ? (
                <p className="mt-1 text-sm text-muted-foreground">{step.message}</p>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}


function ManualGenerateResultSummary({ result }: { result: ManualGenerateResult }) {
  const downloadUrl = result.pdfStatus?.downloadUrl
    ? backendApiUrl(result.pdfStatus.downloadUrl)
    : "";

  return (
    <div className="space-y-4 rounded-md border bg-background p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold">
            {result.job.company} - {result.job.title}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {result.job.location || "Location not specified"}
          </p>
        </div>
        <Badge variant={result.duplicate ? "outline" : "secondary"}>
          {result.duplicate ? "Existing job" : "New job"}
        </Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <ResultMetric
          label="Extraction"
          value={result.extractionResult.extractionSuccess ? "Complete" : "Failed"}
        />
        <ResultMetric
          label="Match"
          value={result.matchResult ? `${result.matchResult.score}` : "Not available"}
        />
        <ResultMetric
          label="Resume"
          value={result.generatedResumeResult ? "Generated" : "Not generated"}
        />
      </div>

      {result.errors.length > 0 ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <p className="font-medium">Generation needs attention</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {result.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {result.generatedResumeResult?.safetyWarnings.length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <p className="font-medium">Safety warnings</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {result.generatedResumeResult.safetyWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-col gap-2 sm:flex-row">
        <Button asChild type="button" variant="outline">
          <a href={`/jobs/summary#job-${result.job.id}`}>
            View in Job Summary
          </a>
        </Button>
        {downloadUrl !== "" ? (
          <Button asChild type="button" variant="outline">
            <a href={downloadUrl} rel="noreferrer" target="_blank">
              Download PDF
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Button>
        ) : null}
        {result.driveStatus?.driveUrl ? (
          <Button asChild type="button" variant="outline">
            <a href={result.driveStatus.driveUrl} rel="noreferrer" target="_blank">
              Open Drive
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Button>
        ) : null}
      </div>
    </div>
  );
}


function ResultMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/20 px-3 py-2">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}


function manualStepBadgeVariant(status: ManualStepStatus) {
  if (status === "completed") {
    return "secondary";
  }
  if (status === "failed") {
    return "destructive";
  }

  return "muted";
}


function manualStepStatusLabel(status: ManualStepStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}


function backendApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (path.startsWith("/api/")) {
    return apiUrl(path.slice(4));
  }

  return apiUrl(path.startsWith("/") ? path : `/${path}`);
}


function AutoScanPanel({
  githubFormValues,
  githubNotice,
  githubSources,
  githubSummary,
  isEditingGithubSource,
  isLoadingGithubSources,
  isRunningPipeline,
  isSavingGithubSource,
  onDeleteSource,
  onCancelEditSource,
  onEditSource,
  onFillExample,
  onGithubFormChange,
  onRunPipeline,
  onSaveSource,
  onScanSource,
  onSelectSource,
  onToggleSource,
  scanningSourceId,
  selectedGithubSourceId,
}: {
  githubFormValues: GithubJobSourceValues;
  githubNotice: SimpleNotice | null;
  githubSources: GithubJobSource[];
  githubSummary: GitHubSummary;
  isEditingGithubSource: boolean;
  isLoadingGithubSources: boolean;
  isRunningPipeline: boolean;
  isSavingGithubSource: boolean;
  onDeleteSource: (sourceId: string) => void;
  onCancelEditSource: () => void;
  onEditSource: (source: GithubJobSource) => void;
  onFillExample: () => void;
  onGithubFormChange: (values: GithubJobSourceValues) => void;
  onRunPipeline: () => void;
  onSaveSource: (event: FormEvent<HTMLFormElement>) => void;
  onScanSource: (sourceId: string) => void;
  onSelectSource: (sourceId: string) => void;
  onToggleSource: (source: GithubJobSource) => void;
  scanningSourceId: string | null;
  selectedGithubSourceId: string;
}) {
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const githubSourceOptions = githubSources.map((source) => ({
    value: source.id,
    label: source.enabled ? source.name : `${source.name} (disabled)`,
  }));

  return (
    <section className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-600">
                <GitBranch className="h-5 w-5" />
              </div>
              <div>
                <CardTitle>GitHub Pipeline Runner</CardTitle>
                <CardDescription>
                  Select one configured markdown source and run the scan-to-resume pipeline.
                </CardDescription>
              </div>
            </div>
            <div className="rounded-lg border bg-muted/30 px-4 py-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Latest scan
              </p>
              <p className="mt-1 font-semibold">{githubSummary.lastScanAt}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
            <div className="space-y-2">
              <p className="text-sm font-medium">GitHub source</p>
              <SelectField
                label="GitHub source"
                onChange={onSelectSource}
                options={githubSourceOptions}
                value={selectedGithubSourceId}
              />
            </div>
            <Button
              className="w-full lg:w-auto"
              disabled={isRunningPipeline || githubSources.length === 0}
              onClick={onRunPipeline}
              type="button"
            >
              {isRunningPipeline ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              Run Pipeline
            </Button>
          </div>

          {githubNotice ? <SimpleNoticeMessage notice={githubNotice} /> : null}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryMetric label="Scanned" value={githubSummary.scannedJobs} />
            <SummaryMetric label="Inserted" value={githubSummary.insertedJobs} />
            <SummaryMetric
              label="Skipped by filters"
              value={githubSummary.rowsSkippedByFilters}
            />
            <SummaryMetric label="Could not scan" value={githubSummary.extractionFailedCount} />
            <SummaryMetric label="Duplicates skipped" value={githubSummary.duplicateJobs} />
            <SummaryMetric label="Tagged" value={githubSummary.jobsTagged} />
            <SummaryMetric label="Matched" value={githubSummary.matchedJobs} />
            <SummaryMetric
              label="Resumes generated"
              value={githubSummary.generatedResumes}
            />
            <SummaryMetric label="PDFs compiled" value={githubSummary.pdfsCompiled} />
            <SummaryMetric
              label="Drive uploads"
              value={githubSummary.driveUploadsSuccessful}
            />
            <SummaryMetric label="Email sent" value={githubSummary.emailsSent} />
            <SummaryMetric
              label="Duration"
              value={formatDuration(githubSummary.durationSeconds)}
            />
          </div>

          {githubSummary.runNotes.length > 0 ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <div className="flex gap-2 font-semibold">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                Pipeline completed
              </div>
              <p className="mt-2 text-emerald-800">
                Some rows could not be fully processed, but the completed pipeline work was saved.
              </p>
              <ul className="mt-3 list-inside list-disc space-y-1 text-emerald-800">
                {githubSummary.runNotes.slice(0, 3).map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
              {githubSummary.runNotes.length > 3 ? (
                <p className="mt-2 text-emerald-800">
                  {githubSummary.runNotes.length - 3} more item
                  {githubSummary.runNotes.length - 3 === 1 ? "" : "s"} were skipped or left for retry.
                </p>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>GitHub Source Configuration</CardTitle>
          <CardDescription>
            Add any GitHub raw markdown README URL that follows a table-style job list.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSaveSource}>
            <div className="grid gap-4 lg:grid-cols-2">
              <TextField
                label="Source name"
                onChange={(value) =>
                  onGithubFormChange({ ...githubFormValues, name: value })
                }
                placeholder="GitHub source name"
                required
                value={githubFormValues.name}
              />
              <TextField
                label="Repository URL"
                onChange={(value) =>
                  onGithubFormChange({ ...githubFormValues, repoUrl: value })
                }
                placeholder="https://github.com/org/repo"
                required
                type="url"
                value={githubFormValues.repoUrl}
              />
              <TextField
                label="Raw README URL"
                onChange={(value) =>
                  onGithubFormChange({ ...githubFormValues, rawReadmeUrl: value })
                }
                placeholder="https://raw.githubusercontent.com/org/repo/branch/README.md"
                required
                type="url"
                value={githubFormValues.rawReadmeUrl}
              />
              <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                <TextField
                  label="Branch"
                  onChange={(value) =>
                    onGithubFormChange({ ...githubFormValues, branch: value })
                  }
                  placeholder="main"
                  required
                  value={githubFormValues.branch}
                />
                <label className="flex h-10 items-center gap-2 self-end rounded-md border bg-background px-3 text-sm">
                  <input
                    checked={githubFormValues.enabled}
                    className="h-4 w-4 accent-primary"
                    onChange={(event) =>
                      onGithubFormChange({
                        ...githubFormValues,
                        enabled: event.target.checked,
                      })
                    }
                    type="checkbox"
                  />
                  Enabled
                </label>
              </div>
            </div>

            <div className="rounded-lg border bg-muted/20">
              <button
                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                onClick={() => setShowAdvancedFilters((currentValue) => !currentValue)}
                type="button"
              >
                <div>
                  <p className="text-sm font-semibold">Advanced scan filters</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Limit this source to relevant role categories before jobs are saved.
                  </p>
                </div>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                    showAdvancedFilters && "rotate-180",
                  )}
                />
              </button>

              {showAdvancedFilters ? (
                <div className="space-y-4 border-t p-4">
                  <TagInput
                    label="Role Tags"
                    onChange={(values) =>
                      onGithubFormChange({ ...githubFormValues, scanRoleTags: values })
                    }
                    placeholder="Software Engineering"
                    values={githubFormValues.scanRoleTags}
                  />
                  <TagInput
                    label="Include Keywords"
                    onChange={(values) =>
                      onGithubFormChange({ ...githubFormValues, includeKeywords: values })
                    }
                    placeholder="software engineer"
                    values={githubFormValues.includeKeywords}
                  />
                  <TagInput
                    label="Exclude Keywords"
                    onChange={(values) =>
                      onGithubFormChange({ ...githubFormValues, excludeKeywords: values })
                    }
                    placeholder="product manager"
                    values={githubFormValues.excludeKeywords}
                  />
                  <TextAreaField
                    label="Custom Instructions"
                    onChange={(value) =>
                      onGithubFormChange({ ...githubFormValues, scanInstructions: value })
                    }
                    placeholder="Only scan software engineering internship roles. Ignore non-technical roles."
                    value={githubFormValues.scanInstructions}
                  />
                </div>
              ) : null}
            </div>

            <div className="flex flex-col justify-end gap-3 sm:flex-row">
                {isEditingGithubSource ? (
                  <Button onClick={onCancelEditSource} type="button" variant="outline">
                    Cancel Edit
                  </Button>
                ) : null}
                <Button onClick={onFillExample} type="button" variant="outline">
                  <GitBranch />
                  Fill SimplifyJobs example
                </Button>
                <Button disabled={isSavingGithubSource} type="submit">
                  {isSavingGithubSource ? <Loader2 className="animate-spin" /> : <Plus />}
                  {isEditingGithubSource ? "Save Source" : "Add Source"}
                </Button>
              </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configured GitHub Sources</CardTitle>
          <CardDescription>
            Enable, scan, or remove saved GitHub markdown sources.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GithubSourcesList
            isLoading={isLoadingGithubSources}
            onDelete={onDeleteSource}
            onEdit={onEditSource}
            onScan={onScanSource}
            onToggle={onToggleSource}
            scanningSourceId={scanningSourceId}
            sources={githubSources}
          />
        </CardContent>
      </Card>
    </section>
  );
}


function TextField({
  label,
  onChange,
  placeholder,
  required = false,
  type = "text",
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  type?: string;
  value: string;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium">{label}</span>
      <input
        className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        type={type}
        value={value}
      />
    </label>
  );
}


function TextAreaField({
  label,
  onChange,
  placeholder,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder: string;
  value: string;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium">{label}</span>
      <textarea
        className="min-h-24 w-full resize-y rounded-md border bg-background px-3 py-2 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}


function TagInput({
  label,
  onChange,
  placeholder,
  values,
}: {
  label: string;
  onChange: (values: string[]) => void;
  placeholder: string;
  values: string[];
}) {
  const [draftValue, setDraftValue] = useState("");

  function addDraftValue() {
    const nextValue = draftValue.trim();
    if (nextValue === "") {
      return;
    }

    const existingValues = new Set(values.map((value) => value.toLowerCase()));
    if (!existingValues.has(nextValue.toLowerCase())) {
      onChange([...values, nextValue]);
    }
    setDraftValue("");
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{label}</p>
      <div className="flex flex-wrap gap-2">
        {values.length === 0 ? (
          <span className="text-sm text-muted-foreground">No tags configured</span>
        ) : (
          values.map((value) => (
            <Badge className="gap-1.5" key={value} variant="secondary">
              {value}
              <button
                aria-label={`Remove ${value}`}
                className="rounded-sm hover:text-destructive"
                onClick={() => onChange(values.filter((item) => item !== value))}
                type="button"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))
        )}
      </div>
      <div className="flex gap-2">
        <input
          className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
          onChange={(event) => setDraftValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addDraftValue();
            }
          }}
          placeholder={placeholder}
          value={draftValue}
        />
        <Button onClick={addDraftValue} type="button" variant="outline">
          <Plus />
          Add
        </Button>
      </div>
    </div>
  );
}


function SelectField({
  label,
  onChange,
  options,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  value: string;
}) {
  return (
    <label className="flex h-10 items-center gap-2 rounded-md border bg-background px-3">
      <span className="sr-only">{label}</span>
      <select
        className="h-full w-full bg-transparent text-sm outline-none"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.length === 0 ? (
          <option value="">No options available</option>
        ) : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}


function SummaryMetric({
  icon,
  label,
  value,
}: {
  icon?: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-2 flex min-h-4 items-center justify-between gap-3 text-xs font-semibold uppercase text-muted-foreground">
        <span>{label}</span>
        {icon}
      </div>
      <p className="text-2xl font-semibold tracking-normal">{value}</p>
    </div>
  );
}


function NoticeMessage({ notice }: { notice: JobNotice }) {
  const Icon =
    notice.type === "error"
      ? AlertCircle
      : notice.type === "duplicate"
        ? AlertCircle
        : CheckCircle2;

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border p-3 text-sm",
        notice.type === "error" && "border-destructive/30 bg-destructive/5 text-destructive",
        notice.type === "duplicate" && "border-amber-200 bg-amber-50 text-amber-800",
        notice.type === "success" && "border-emerald-200 bg-emerald-50 text-emerald-800",
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <p className="font-medium">{notice.text}</p>
        {notice.type === "duplicate" ? (
          <a
            className="mt-1 inline-flex font-semibold underline"
            href={`/jobs/summary#job-${notice.job.id}`}
          >
            View existing job
          </a>
        ) : null}
      </div>
    </div>
  );
}


function SimpleNoticeMessage({ notice }: { notice: SimpleNotice }) {
  const Icon = notice.type === "error" ? AlertCircle : CheckCircle2;

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border p-3 text-sm",
        notice.type === "error" && "border-destructive/30 bg-destructive/5 text-destructive",
        notice.type === "success" && "border-emerald-200 bg-emerald-50 text-emerald-800",
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <p className="font-medium">{notice.text}</p>
    </div>
  );
}


function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex min-h-48 items-center justify-center rounded-lg border border-dashed">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {label}
      </div>
    </div>
  );
}


function EmptyState({
  description,
  icon,
  title,
}: {
  description: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <div className="rounded-lg border border-dashed p-10 text-center">
      <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-muted text-muted-foreground">
        {icon}
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
        {description}
      </p>
    </div>
  );
}


function GithubSourcesList({
  isLoading,
  onDelete,
  onEdit,
  onScan,
  onToggle,
  scanningSourceId,
  sources,
}: {
  isLoading: boolean;
  onDelete: (sourceId: string) => void;
  onEdit: (source: GithubJobSource) => void;
  onScan: (sourceId: string) => void;
  onToggle: (source: GithubJobSource) => void;
  scanningSourceId: string | null;
  sources: GithubJobSource[];
}) {
  if (isLoading) {
    return <LoadingState label="Loading GitHub sources" />;
  }

  if (sources.length === 0) {
    return (
      <EmptyState
        description="Add a raw GitHub markdown README URL before running an auto scan."
        icon={<GitBranch className="h-6 w-6" />}
        title="No GitHub sources yet"
      />
    );
  }

  return (
    <div className="space-y-3">
      {sources.map((source) => {
        const isScanning = scanningSourceId === source.id;

        return (
          <div className="rounded-lg border p-4" key={source.id}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{source.name}</h3>
                  <Badge variant={source.enabled ? "secondary" : "muted"}>
                    {source.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Branch {source.branch} - Last scanned {formatDateTime(source.lastScannedAt)}
                </p>
                <div className="mt-3 flex flex-wrap gap-3 text-sm">
                  <a
                    className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
                    href={source.repoUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Repository
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                  <a
                    className="inline-flex min-w-0 items-center gap-1 font-medium text-primary hover:underline"
                    href={source.rawReadmeUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    <Link2 className="h-3.5 w-3.5" />
                    Raw markdown
                  </a>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {source.scanRoleTags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
                {source.scanInstructions ? (
                  <p className="mt-3 max-w-2xl text-xs leading-5 text-muted-foreground">
                    {source.scanInstructions}
                  </p>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => onEdit(source)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  Edit
                </Button>
                <Button
                  disabled={!source.enabled || isScanning}
                  onClick={() => onScan(source.id)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  {isScanning ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                  Scan
                </Button>
                <Button
                  onClick={() => onToggle(source)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  {source.enabled ? "Disable" : "Enable"}
                </Button>
                <Button
                  aria-label={`Delete ${source.name}`}
                  onClick={() => onDelete(source.id)}
                  size="icon"
                  type="button"
                  variant="ghost"
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}


function JobsTable({
  jobs,
  onOpenJob,
}: {
  jobs: JobPosting[];
  onOpenJob: (job: JobPosting) => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="w-full overflow-hidden">
        <table className="w-full table-fixed text-left text-sm">
          <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="w-[18%] px-4 py-3 font-semibold">Source</th>
              <th className="w-[38%] px-4 py-3 font-semibold">Job</th>
              <th className="w-[14%] px-4 py-3 font-semibold">Posted</th>
              <th className="w-[10%] px-4 py-3 font-semibold">Match</th>
              <th className="w-[20%] px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {jobs.map((job) => (
              <tr
                className="cursor-pointer bg-card transition-colors hover:bg-muted/30"
                id={`job-${job.id}`}
                key={job.id}
                onClick={() => onOpenJob(job)}
              >
                <td className="px-4 py-4 align-top">
                  <div className="min-w-0 space-y-2">
                    <Badge variant={job.source === "github" ? "secondary" : "outline"}>
                      {job.source === "github" ? "GitHub" : "Manual"}
                    </Badge>
                    {job.source === "github" ? (
                      <p className="truncate text-xs text-muted-foreground">
                        {githubSourceLabel(job)}
                      </p>
                    ) : null}
                  </div>
                </td>
                <td className="px-4 py-4 align-top">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-foreground">
                      {job.company}
                    </p>
                    <p className="mt-1 truncate font-medium text-foreground">
                      {job.title}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {job.location || "Location not specified"}
                    </p>
                    {job.jobTags.length > 0 ? (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {job.jobTags.slice(0, 3).map((tag) => (
                          <Badge className="px-1.5 py-0 text-[11px]" key={tag} variant="muted">
                            {tag}
                          </Badge>
                        ))}
                        {job.jobTags.length > 3 ? (
                          <Badge className="px-1.5 py-0 text-[11px]" variant="outline">
                            +{job.jobTags.length - 3}
                          </Badge>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </td>
                <td className="px-4 py-4 align-top text-muted-foreground">
                  {formatDateOnly(job.postedAt)}
                </td>
                <td className="px-4 py-4 align-top">
                  {jobHasVisibleMatch(job) ? (
                    <Badge variant="outline">Match {job.latestMatch.score}</Badge>
                  ) : (
                    <span className="text-muted-foreground">Not matched</span>
                  )}
                </td>
                <td className="px-4 py-4 align-top">
                  <StatusBadge
                    fallback={formatStatus(job.status)}
                    status={job.currentStatus}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function PaginationControls({
  currentPage,
  onPageChange,
  pageSize,
  totalItems,
  totalPages,
}: {
  currentPage: number;
  onPageChange: (page: number) => void;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}) {
  if (totalItems <= pageSize) {
    return null;
  }

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">
        Showing {startItem}-{endItem} of {totalItems}
      </p>
      <div className="flex items-center justify-end gap-2">
        <Button
          disabled={currentPage === 1}
          onClick={() => onPageChange(currentPage - 1)}
          type="button"
          variant="outline"
        >
          Previous
        </Button>
        <span className="min-w-20 text-center text-sm font-medium">
          Page {currentPage} of {totalPages}
        </span>
        <Button
          disabled={currentPage === totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          type="button"
          variant="outline"
        >
          Next
        </Button>
      </div>
    </div>
  );
}


function JobDetailDrawer({
  history,
  historyError,
  isChangingStatus,
  isLoadingHistory,
  isSavingTags,
  job,
  onChangeStatus,
  onClose,
  onSaveTags,
  statuses,
}: {
  history: JobStatusHistoryItem[];
  historyError: string;
  isChangingStatus: boolean;
  isLoadingHistory: boolean;
  isSavingTags: boolean;
  job: JobPosting;
  onChangeStatus: (values: { statusId: string; note: string }) => void;
  onClose: () => void;
  onSaveTags: (tags: string[]) => void;
  statuses: CustomJobStatus[];
}) {
  const [selectedStatusId, setSelectedStatusId] = useState(currentStatusId(job));
  const [statusNote, setStatusNote] = useState("");
  const [tagEditorValue, setTagEditorValue] = useState(job.jobTags.join(", "));

  useEffect(() => {
    setSelectedStatusId(currentStatusId(job));
    setStatusNote("");
    setTagEditorValue(job.jobTags.join(", "));
  }, [job]);

  const matchedSkills = job.latestMatch
    ? [
        ...job.latestMatch.exactSkillMatches,
        ...job.latestMatch.fuzzySkillMatches.map(
          (match) => `${match.requiredSkill} (${match.profileSkill})`,
        ),
      ]
    : [];
  const descriptionPreview = job.extractedDescription.slice(0, 1200);

  return (
    <div className="fixed inset-0 z-50 bg-black/45 p-4 sm:p-6">
      <button
        aria-label="Close job details"
        className="absolute inset-0 h-full w-full cursor-default"
        onClick={onClose}
        type="button"
      />
      <aside className="relative mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-xl border bg-background shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b bg-muted/25 px-5 py-5 sm:px-6">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant={job.source === "github" ? "secondary" : "outline"}>
                {job.source === "github" ? "GitHub" : "Manual"}
              </Badge>
              <StatusBadge status={job.currentStatus} fallback={formatStatus(job.status)} />
            </div>
            <h2 className="text-xl font-semibold tracking-normal">{job.title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {job.company} {job.location ? `- ${job.location}` : ""}
            </p>
          </div>
          <Button aria-label="Close" onClick={onClose} size="icon" type="button" variant="ghost">
            <X />
          </Button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          <div className="grid gap-4 md:grid-cols-2">
            <DetailField label="GitHub source" value={job.source === "github" ? githubSourceLabel(job) : "Not applicable"} />
            <DetailField label="Source section" value={job.sourceSection || "Unknown"} />
            <DetailField label="Posted date" value={formatDateOnly(job.postedAt)} />
            <DetailField label="Discovered date" value={formatKnownDateTime(job.discoveredAt)} />
            <DetailField label="Match score" value={job.latestMatch ? `${job.latestMatch.score}` : "Unknown"} />
          </div>

          <section className="mt-6 rounded-xl border p-4">
            <h3 className="font-semibold">Scan context</h3>
            <div className="mt-3 space-y-4">
              <SkillPills
                emptyLabel="No tags assigned."
                label="Job tags"
                values={job.jobTags}
              />
              <DetailField
                label="Scan match reason"
                value={job.scanMatchReason || "Not available"}
              />
              {job.githubSource ? (
                <DetailField
                  label="Source scan instructions"
                  value={job.githubSource.scanInstructions || "No custom instructions"}
                />
              ) : null}
              <form
                className="rounded-lg border bg-muted/20 p-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  onSaveTags(parseTagEditorValue(tagEditorValue));
                }}
              >
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Edit tags</span>
                  <input
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-ring/20"
                    onChange={(event) => setTagEditorValue(event.target.value)}
                    placeholder="Software Engineering, Backend"
                    value={tagEditorValue}
                  />
                </label>
                <div className="mt-3 flex justify-end">
                  <Button disabled={isSavingTags} size="sm" type="submit">
                    {isSavingTags ? <Loader2 className="animate-spin" /> : null}
                    Save tags
                  </Button>
                </div>
              </form>
            </div>
          </section>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <DetailLink label="Job URL" url={job.jobUrl} />
            <DetailLink
              label="Drive link"
              url={job.latestGeneratedResume?.driveUrl ?? ""}
            />
          </div>

          <section className="mt-6 rounded-xl border p-4">
            <h3 className="font-semibold">Resume status</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <ResultMetric
                label="Generated resume"
                value={jobHasGeneratedResume(job) ? "Yes" : "No"}
              />
              <ResultMetric
                label="PDF"
                value={job.latestGeneratedResume?.pdfPath ? "Compiled" : "Not available"}
              />
            </div>
            {job.latestGeneratedResume?.safetyWarnings.length ? (
              <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <p className="font-medium">Safety warnings</p>
                <ul className="mt-2 list-inside list-disc space-y-1">
                  {job.latestGeneratedResume.safetyWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="mt-6 rounded-xl border p-4">
            <h3 className="font-semibold">Match details</h3>
            {job.latestMatch ? (
              <div className="mt-3 space-y-4">
                <p className="text-sm text-muted-foreground">{job.latestMatch.matchReason}</p>
                <SkillPills
                  emptyLabel="No matched skills saved."
                  label="Matched skills"
                  values={matchedSkills}
                />
                <SkillPills
                  emptyLabel="No missing skills saved."
                  label="Missing skills"
                  muted
                  values={job.latestMatch.missingSkills}
                />
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">No match result yet.</p>
            )}
          </section>

          <section className="mt-6 rounded-xl border p-4">
            <h3 className="font-semibold">Extracted description</h3>
            {descriptionPreview ? (
              <p className="mt-3 whitespace-pre-line text-sm leading-6 text-muted-foreground">
                {descriptionPreview}
                {job.extractedDescription.length > descriptionPreview.length ? "..." : ""}
              </p>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                No extracted description is available.
              </p>
            )}
          </section>

          <section className="mt-6 rounded-xl border p-4">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-semibold">Status history</h3>
            </div>
            <form
              className="mt-4 rounded-lg border bg-muted/20 p-4"
              onSubmit={(event) => {
                event.preventDefault();
                onChangeStatus({ statusId: selectedStatusId, note: statusNote });
              }}
            >
              <div className="flex flex-col gap-1">
                <p className="text-sm font-semibold">Update current status</p>
                <p className="text-sm text-muted-foreground">
                  Choose the next stage and optionally add a note for the timeline.
                </p>
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-[240px_1fr_auto] lg:items-end">
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Status</span>
                  <select
                    className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-ring/20"
                    onChange={(event) => setSelectedStatusId(event.target.value)}
                    value={selectedStatusId}
                  >
                    {statuses.map((statusItem) => (
                      <option key={statusItem.id} value={statusItem.id}>
                        {statusItem.name}
                      </option>
                    ))}
                  </select>
                </label>
                <TextField
                  label="Note"
                  onChange={setStatusNote}
                  placeholder="Optional note"
                  value={statusNote}
                />
                <Button
                  disabled={isChangingStatus || selectedStatusId === ""}
                  type="submit"
                >
                  {isChangingStatus ? <Loader2 className="animate-spin" /> : null}
                  Update status
                </Button>
              </div>
            </form>

            {historyError ? (
              <div className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                Could not load status history: {historyError}
              </div>
            ) : isLoadingHistory ? (
              <div className="mt-4">
                <LoadingState label="Loading status history" />
              </div>
            ) : history.length === 0 ? (
              <p className="mt-4 text-sm text-muted-foreground">No status history yet.</p>
            ) : (
              <div className="mt-4 space-y-3">
                {history.map((item) => (
                  <div className="rounded-md border bg-muted/20 p-3" key={item.id}>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={item.toStatus} fallback={item.toStatus.name} />
                      <span className="text-xs text-muted-foreground">
                        {formatKnownDateTime(item.changedAt)}
                      </span>
                    </div>
                    {item.fromStatus ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        From {item.fromStatus.name}
                      </p>
                    ) : null}
                    {item.note ? (
                      <p className="mt-2 text-sm text-muted-foreground">{item.note}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}


function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium">{value || "Unknown"}</p>
    </div>
  );
}


function DetailLink({ label, url }: { label: string; url: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      {url ? (
        <a
          className="mt-1 inline-flex min-w-0 items-center gap-1 text-sm font-medium text-primary hover:underline"
          href={url}
          rel="noreferrer"
          target="_blank"
        >
          Open link
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      ) : (
        <p className="mt-1 text-sm text-muted-foreground">Not available</p>
      )}
    </div>
  );
}


function SkillPills({
  emptyLabel,
  label,
  muted = false,
  values,
}: {
  emptyLabel: string;
  label: string;
  muted?: boolean;
  values: string[];
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      {values.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{emptyLabel}</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {values.map((value) => (
            <Badge key={value} variant={muted ? "muted" : "secondary"}>
              {value}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}


function StatusBadge({
  fallback,
  status,
}: {
  fallback: string;
  status: CustomJobStatus | null;
}) {
  const color = status?.color || "";
  return (
    <Badge
      className="gap-1.5"
      style={
        color
          ? {
              borderColor: `${color}55`,
              color,
            }
          : undefined
      }
      variant="outline"
    >
      {color ? (
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: color }}
        />
      ) : null}
      {status?.name ?? fallback}
    </Badge>
  );
}


function upsertGithubSource(
  currentSources: GithubJobSource[],
  nextSource: GithubJobSource,
): GithubJobSource[] {
  const existingIndex = currentSources.findIndex((source) => source.id === nextSource.id);
  if (existingIndex === -1) {
    return [nextSource, ...currentSources];
  }

  return currentSources.map((source) =>
    source.id === nextSource.id ? nextSource : source,
  );
}


function getGithubSummary(
  sources: GithubJobSource[],
  lastScan: GithubSourceRunSummary | null,
): GitHubSummary {
  const lastScannedAt = getLatestGithubScanAt(sources);

  return {
    lastScanAt: lastScannedAt === "" ? "Not run yet" : formatDateTime(lastScannedAt),
    totalRowsSeen: lastScan?.totalRowsSeen ?? 0,
    parsedJobs: lastScan?.parsedJobs ?? 0,
    scannedJobs: lastScan?.scannedJobs ?? 0,
    insertedJobs: lastScan?.insertedJobs ?? 0,
    duplicateJobs: lastScan?.duplicateJobs ?? 0,
    rowsSkippedByFilters: lastScan?.rowsSkippedByFilters ?? 0,
    jobsTagged: lastScan?.jobsTagged ?? 0,
    extractionSuccessCount: lastScan?.extractionSuccessCount ?? 0,
    extractionFailedCount: lastScan?.extractionFailedCount ?? 0,
    matchedJobs: lastScan?.matchedJobs ?? 0,
    generatedResumes: lastScan?.generatedResumes ?? 0,
    pdfsCompiled: lastScan?.pdfsCompiled ?? 0,
    driveUploadsSuccessful: lastScan?.driveUploadsSuccessful ?? 0,
    emailsSent: lastScan?.emailsSent ?? 0,
    durationSeconds: lastScan?.durationSeconds ?? 0,
    runNotes: lastScan?.errors ?? [],
  };
}


function getLatestGithubScanAt(sources: GithubJobSource[]): string {
  return sources.reduce((latestValue, source) => {
    if (source.lastScannedAt === "") {
      return latestValue;
    }
    if (latestValue === "" || source.lastScannedAt > latestValue) {
      return source.lastScannedAt;
    }

    return latestValue;
  }, "");
}


function buildJobSummaryStats(jobs: JobPosting[]): JobSummaryStats {
  return jobs.reduce<JobSummaryStats>(
    (stats, job) => ({
      totalJobs: stats.totalJobs + 1,
      matchedJobs: stats.matchedJobs + (jobHasVisibleMatch(job) ? 1 : 0),
      resumesGenerated:
        stats.resumesGenerated + (jobHasGeneratedResume(job) ? 1 : 0),
      appliedInterviewing:
        stats.appliedInterviewing + (isAppliedOrInterviewing(job) ? 1 : 0),
      postedLast7Days:
        stats.postedLast7Days + (isPostedInLastDays(job.postedAt, 7) ? 1 : 0),
    }),
    {
      totalJobs: 0,
      matchedJobs: 0,
      resumesGenerated: 0,
      appliedInterviewing: 0,
      postedLast7Days: 0,
    },
  );
}


function jobHasGeneratedResume(job: JobPosting): boolean {
  return (
    job.latestGeneratedResume !== null ||
    normalizedStatusName(job) === "resume generated" ||
    job.status === "resume_generated" ||
    job.status === "emailed"
  );
}


function currentStatusId(job: JobPosting): string {
  return job.currentStatus?.id ?? job.currentStatusId;
}


function jobGithubSourceId(job: JobPosting): string {
  return job.githubSource?.id ?? job.githubSourceId;
}


function githubSourceFilterValue(sourceId: string): string {
  return `github:${sourceId}`;
}


function jobMatchesSourceFilter(job: JobPosting, sourceFilter: SourceFilter): boolean {
  if (sourceFilter === "all") {
    return true;
  }
  if (sourceFilter === "manual") {
    return job.source === "manual";
  }
  if (sourceFilter.startsWith("github:")) {
    return (
      job.source === "github" &&
      jobGithubSourceId(job) === sourceFilter.replace("github:", "")
    );
  }

  return true;
}


function githubSourceLabel(job: JobPosting): string {
  if (job.githubSource?.name) {
    return job.githubSource.name;
  }
  if (job.sourceRepoUrl) {
    return job.sourceRepoUrl.replace("https://github.com/", "");
  }

  return "Unknown";
}


function parseTagEditorValue(value: string): string[] {
  const tags: string[] = [];
  const seenTags = new Set<string>();
  for (const part of value.split(",")) {
    const tag = part.trim();
    const normalizedTag = tag.toLowerCase();
    if (tag === "" || seenTags.has(normalizedTag)) {
      continue;
    }
    tags.push(tag);
    seenTags.add(normalizedTag);
  }

  return tags;
}


function normalizedStatusName(job: JobPosting): string {
  return (job.currentStatus?.name ?? formatStatus(job.status)).trim().toLowerCase();
}


function jobHasVisibleMatch(job: JobPosting): job is JobPosting & {
  latestMatch: NonNullable<JobPosting["latestMatch"]>;
} {
  return job.latestMatch !== null && job.latestMatch.score > MIN_VISIBLE_MATCH_SCORE;
}


function isAppliedOrInterviewing(job: JobPosting): boolean {
  return [
    "applied",
    "phone screen",
    "interview 1",
    "interview 2",
    "offer",
  ].includes(normalizedStatusName(job));
}


function isPostedInLastDays(value: string, days: number): boolean {
  if (value === "") {
    return false;
  }

  const postedAt = new Date(value).getTime();
  if (Number.isNaN(postedAt)) {
    return false;
  }

  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return postedAt >= cutoff;
}
