import { request } from "@/lib/api-client";
import type { GithubJobSource } from "@/lib/github-sources-api";
import type { CustomJobStatus } from "@/lib/job-statuses-api";


export type JobSource = "manual" | "github";


export type JobStatus =
  | "new"
  | "matched"
  | "resume_generated"
  | "emailed"
  | "archived"
  | "applied";


export type JobPosting = {
  id: string;
  githubSourceId: string;
  currentStatusId: string;
  source: JobSource;
  sourceRepoUrl: string;
  sourceRawUrl: string;
  externalJobId: string;
  sourceSection: string;
  jobTags: string[];
  scanMatchReason: string;
  company: string;
  title: string;
  location: string;
  jobUrl: string;
  description: string;
  rawText: string;
  extractedDescription: string;
  extractionStatus: string;
  extractionError: string;
  extractedAt: string;
  postedAt: string;
  discoveredAt: string;
  status: JobStatus;
  contentHash: string;
  createdAt: string;
  updatedAt: string;
  currentStatus: CustomJobStatus | null;
  githubSource: GithubJobSource | null;
  latestMatch: JobMatchResult | null;
  latestGeneratedResume: GeneratedResumeResult | null;
};


export type ManualJobValues = {
  company: string;
  title: string;
  location: string;
  jobUrl: string;
  description: string;
};


export type JobUpdateValues = Partial<{
  company: string;
  title: string;
  location: string;
  jobUrl: string;
  description: string;
  rawText: string;
  sourceSection: string;
  jobTags: string[];
  scanMatchReason: string;
}>;


export type CreateJobResult = {
  job: JobPosting;
  duplicate: boolean;
  message: string;
};


export type JobExtractionResult = {
  cleanedText: string;
  pageTitle: string;
  companyGuess: string;
  titleGuess: string;
  locationGuess: string;
  postedAt: string;
  extractionSuccess: boolean;
  extractionMethod: string;
  errorMessage: string;
};


export type JobMatchResult = {
  id: string;
  jobId: string;
  score: number;
  matchReason: string;
  exactSkillMatches: string[];
  fuzzySkillMatches: FuzzySkillMatch[];
  missingSkills: string[];
  relevantExperiences: RelevantProfileItem[];
  relevantProjects: RelevantProfileItem[];
  createdAt: string;
};


export type FuzzySkillMatch = {
  requiredSkill: string;
  profileSkill: string;
  score: number;
};


export type RelevantProfileItem = {
  id: string;
  label: string;
  score: number;
};


export type GeneratedResumeResult = {
  id: string;
  jobId: string;
  pdfPath: string;
  driveUrl: string;
  safetyWarnings: string[];
  createdAt: string;
};


export type ManualGeneratePdfStatus = {
  attempted: boolean;
  success: boolean;
  skipped: boolean;
  pdfPath: string;
  downloadUrl: string;
  compiler: string;
  errorMessage: string;
};


export type ManualGenerateDriveStatus = {
  attempted: boolean;
  success: boolean;
  skipped: boolean;
  driveUrl: string;
  errorMessage: string;
};


export type ManualGenerateResult = {
  job: JobPosting;
  extractionResult: JobExtractionResult;
  matchResult: JobMatchResult | null;
  generatedResumeResult: GeneratedResumeResult | null;
  pdfStatus: ManualGeneratePdfStatus | null;
  driveStatus: ManualGenerateDriveStatus | null;
  duplicate: boolean;
  errors: string[];
};


export type JobStatusHistoryItem = {
  id: string;
  jobId: string;
  fromStatusId: string;
  toStatusId: string;
  note: string;
  changedAt: string;
  fromStatus: CustomJobStatus | null;
  toStatus: CustomJobStatus;
};


type JobPostingApiRecord = {
  id: string;
  github_source_id: string | null;
  current_status_id: string | null;
  source: JobSource;
  source_repo_url: string | null;
  source_raw_url: string | null;
  external_job_id: string | null;
  source_section: string | null;
  job_tags: string[];
  scan_match_reason: string | null;
  company: string;
  title: string;
  location: string | null;
  job_url: string | null;
  description: string | null;
  raw_text: string | null;
  extracted_description: string | null;
  extraction_status: string;
  extraction_error: string | null;
  extracted_at: string | null;
  posted_at: string | null;
  discovered_at: string;
  status: JobStatus;
  content_hash: string;
  created_at: string;
  updated_at: string;
  current_status: CustomJobStatusApiRecord | null;
  github_source: GithubJobSourceApiRecord | null;
  latest_match: JobMatchApiResult | null;
  latest_generated_resume: GeneratedResumeApiResult | null;
};


type CreateJobApiResult = {
  job: JobPostingApiRecord;
  duplicate: boolean;
  message: string;
};


type JobExtractionApiResult = {
  cleaned_text: string;
  page_title: string;
  company_guess: string | null;
  title_guess: string | null;
  location_guess: string | null;
  posted_at: string | null;
  extraction_success: boolean;
  extraction_method: string;
  error_message: string | null;
};


type JobMatchApiResult = {
  id: string;
  job_id: string;
  score: number;
  match_reason: string;
  exact_skill_matches: string[];
  fuzzy_skill_matches: FuzzySkillMatchApiRecord[];
  missing_skills: string[];
  relevant_experiences: RelevantProfileItemApiRecord[];
  relevant_projects: RelevantProfileItemApiRecord[];
  created_at: string;
};


type FuzzySkillMatchApiRecord = {
  required_skill: string;
  profile_skill: string;
  score: number;
};


type RelevantProfileItemApiRecord = {
  id: string;
  label: string;
  score: number;
};


type GeneratedResumeApiResult = {
  id: string;
  job_id: string;
  pdf_path: string | null;
  drive_url: string | null;
  safety_warnings: string[];
  created_at: string;
};


type CustomJobStatusApiRecord = {
  id: string;
  user_id: string;
  name: string;
  color: string | null;
  sort_order: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};


type GithubJobSourceApiRecord = {
  id: string;
  user_id: string;
  name: string;
  repo_url: string;
  raw_readme_url: string;
  branch: string;
  enabled: boolean;
  scan_role_tags: string[];
  include_keywords: string[];
  exclude_keywords: string[];
  scan_instructions: string | null;
  last_scanned_at: string | null;
  created_at: string;
  updated_at: string;
};


type JobStatusHistoryApiRecord = {
  id: string;
  job_id: string;
  from_status_id: string | null;
  to_status_id: string;
  note: string | null;
  changed_at: string;
  from_status: CustomJobStatusApiRecord | null;
  to_status: CustomJobStatusApiRecord;
};


type ManualGeneratePdfApiStatus = {
  attempted: boolean;
  success: boolean;
  skipped: boolean;
  pdf_path: string | null;
  download_url: string | null;
  compiler: string | null;
  error_message: string | null;
};


type ManualGenerateDriveApiStatus = {
  attempted: boolean;
  success: boolean;
  skipped: boolean;
  drive_url: string | null;
  error_message: string | null;
};


type ManualGenerateApiResult = {
  job: JobPostingApiRecord;
  extraction_result: JobExtractionApiResult;
  match_result: JobMatchApiResult | null;
  generated_resume_result: GeneratedResumeApiResult | null;
  pdf_status: ManualGeneratePdfApiStatus | null;
  drive_status: ManualGenerateDriveApiStatus | null;
  duplicate: boolean;
  errors: string[];
};


export const jobsApi = {
  async list(): Promise<JobPosting[]> {
    const records = await request<JobPostingApiRecord[]>("/jobs");
    return records.map(jobFromApi);
  },

  async listStatusHistory(jobId: string): Promise<JobStatusHistoryItem[]> {
    const records = await request<JobStatusHistoryApiRecord[]>(
      `/jobs/${jobId}/status-history`,
    );
    return records.map(statusHistoryFromApi);
  },

  async changeStatus(
    jobId: string,
    values: { statusId: string; note: string },
  ): Promise<JobPosting> {
    const record = await request<JobPostingApiRecord>(`/jobs/${jobId}/status`, {
      body: JSON.stringify({
        status_id: values.statusId,
        note: optionalApiString(values.note),
      }),
      method: "POST",
    });
    return jobFromApi(record);
  },

  async update(jobId: string, values: JobUpdateValues): Promise<JobPosting> {
    const record = await request<JobPostingApiRecord>(`/jobs/${jobId}`, {
      body: JSON.stringify(jobUpdateToApi(values)),
      method: "PUT",
    });
    return jobFromApi(record);
  },

  async createManual(values: ManualJobValues): Promise<CreateJobResult> {
    const result = await request<CreateJobApiResult>("/jobs/manual", {
      body: JSON.stringify({
        company: values.company,
        title: values.title,
        location: optionalApiString(values.location),
        job_url: optionalApiString(values.jobUrl),
        description: optionalApiString(values.description),
      }),
      method: "POST",
    });

    return {
      job: jobFromApi(result.job),
      duplicate: result.duplicate,
      message: result.message,
    };
  },

  async generateManualFromUrl(jobUrl: string): Promise<ManualGenerateResult> {
    const result = await request<ManualGenerateApiResult>("/jobs/manual/generate", {
      body: JSON.stringify({ job_url: jobUrl }),
      method: "POST",
    });

    return {
      job: jobFromApi(result.job),
      extractionResult: extractionResultFromApi(result.extraction_result),
      matchResult:
        result.match_result === null ? null : matchResultFromApi(result.match_result),
      generatedResumeResult:
        result.generated_resume_result === null
          ? null
          : generatedResumeFromApi(result.generated_resume_result),
      pdfStatus:
        result.pdf_status === null ? null : pdfStatusFromApi(result.pdf_status),
      driveStatus:
        result.drive_status === null ? null : driveStatusFromApi(result.drive_status),
      duplicate: result.duplicate,
      errors: result.errors,
    };
  },
};


function jobFromApi(record: JobPostingApiRecord): JobPosting {
  return {
    id: record.id,
    githubSourceId: optionalString(record.github_source_id),
    currentStatusId: optionalString(record.current_status_id),
    source: record.source,
    sourceRepoUrl: optionalString(record.source_repo_url),
    sourceRawUrl: optionalString(record.source_raw_url),
    externalJobId: optionalString(record.external_job_id),
    sourceSection: optionalString(record.source_section),
    jobTags: record.job_tags,
    scanMatchReason: optionalString(record.scan_match_reason),
    company: record.company,
    title: record.title,
    location: optionalString(record.location),
    jobUrl: optionalString(record.job_url),
    description: optionalString(record.description),
    rawText: optionalString(record.raw_text),
    extractedDescription: optionalString(record.extracted_description),
    extractionStatus: record.extraction_status,
    extractionError: optionalString(record.extraction_error),
    extractedAt: optionalString(record.extracted_at),
    postedAt: optionalString(record.posted_at),
    discoveredAt: record.discovered_at,
    status: record.status,
    contentHash: record.content_hash,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
    currentStatus:
      record.current_status === null ? null : jobStatusFromApi(record.current_status),
    githubSource:
      record.github_source === null ? null : githubSourceFromApi(record.github_source),
    latestMatch:
      record.latest_match === null ? null : matchResultFromApi(record.latest_match),
    latestGeneratedResume:
      record.latest_generated_resume === null
        ? null
        : generatedResumeFromApi(record.latest_generated_resume),
  };
}


function extractionResultFromApi(record: JobExtractionApiResult): JobExtractionResult {
  return {
    cleanedText: record.cleaned_text,
    pageTitle: record.page_title,
    companyGuess: optionalString(record.company_guess),
    titleGuess: optionalString(record.title_guess),
    locationGuess: optionalString(record.location_guess),
    postedAt: optionalString(record.posted_at),
    extractionSuccess: record.extraction_success,
    extractionMethod: record.extraction_method,
    errorMessage: optionalString(record.error_message),
  };
}


function matchResultFromApi(record: JobMatchApiResult): JobMatchResult {
  return {
    id: record.id,
    jobId: record.job_id,
    score: record.score,
    matchReason: record.match_reason,
    exactSkillMatches: record.exact_skill_matches,
    fuzzySkillMatches: record.fuzzy_skill_matches.map((match) => ({
      requiredSkill: match.required_skill,
      profileSkill: match.profile_skill,
      score: match.score,
    })),
    missingSkills: record.missing_skills,
    relevantExperiences: record.relevant_experiences.map(relevantProfileItemFromApi),
    relevantProjects: record.relevant_projects.map(relevantProfileItemFromApi),
    createdAt: record.created_at,
  };
}


function generatedResumeFromApi(record: GeneratedResumeApiResult): GeneratedResumeResult {
  return {
    id: record.id,
    jobId: record.job_id,
    pdfPath: optionalString(record.pdf_path),
    driveUrl: optionalString(record.drive_url),
    safetyWarnings: record.safety_warnings,
    createdAt: record.created_at,
  };
}


function relevantProfileItemFromApi(
  record: RelevantProfileItemApiRecord,
): RelevantProfileItem {
  return {
    id: record.id,
    label: record.label,
    score: record.score,
  };
}


function jobStatusFromApi(record: CustomJobStatusApiRecord): CustomJobStatus {
  return {
    id: record.id,
    userId: record.user_id,
    name: record.name,
    color: optionalString(record.color),
    sortOrder: record.sort_order,
    isDefault: record.is_default,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}


function githubSourceFromApi(record: GithubJobSourceApiRecord): GithubJobSource {
  return {
    id: record.id,
    userId: record.user_id,
    name: record.name,
    repoUrl: record.repo_url,
    rawReadmeUrl: record.raw_readme_url,
    branch: record.branch,
    enabled: record.enabled,
    scanRoleTags: record.scan_role_tags,
    includeKeywords: record.include_keywords,
    excludeKeywords: record.exclude_keywords,
    scanInstructions: optionalString(record.scan_instructions),
    lastScannedAt: optionalString(record.last_scanned_at),
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}


function jobUpdateToApi(values: JobUpdateValues) {
  return {
    ...(values.company !== undefined ? { company: values.company } : {}),
    ...(values.title !== undefined ? { title: values.title } : {}),
    ...(values.location !== undefined
      ? { location: optionalApiString(values.location) }
      : {}),
    ...(values.jobUrl !== undefined ? { job_url: optionalApiString(values.jobUrl) } : {}),
    ...(values.description !== undefined
      ? { description: optionalApiString(values.description) }
      : {}),
    ...(values.rawText !== undefined ? { raw_text: optionalApiString(values.rawText) } : {}),
    ...(values.sourceSection !== undefined
      ? { source_section: optionalApiString(values.sourceSection) }
      : {}),
    ...(values.jobTags !== undefined ? { job_tags: values.jobTags } : {}),
    ...(values.scanMatchReason !== undefined
      ? { scan_match_reason: optionalApiString(values.scanMatchReason) }
      : {}),
  };
}


function statusHistoryFromApi(record: JobStatusHistoryApiRecord): JobStatusHistoryItem {
  return {
    id: record.id,
    jobId: record.job_id,
    fromStatusId: optionalString(record.from_status_id),
    toStatusId: record.to_status_id,
    note: optionalString(record.note),
    changedAt: record.changed_at,
    fromStatus:
      record.from_status === null ? null : jobStatusFromApi(record.from_status),
    toStatus: jobStatusFromApi(record.to_status),
  };
}


function pdfStatusFromApi(record: ManualGeneratePdfApiStatus): ManualGeneratePdfStatus {
  return {
    attempted: record.attempted,
    success: record.success,
    skipped: record.skipped,
    pdfPath: optionalString(record.pdf_path),
    downloadUrl: optionalString(record.download_url),
    compiler: optionalString(record.compiler),
    errorMessage: optionalString(record.error_message),
  };
}


function driveStatusFromApi(
  record: ManualGenerateDriveApiStatus,
): ManualGenerateDriveStatus {
  return {
    attempted: record.attempted,
    success: record.success,
    skipped: record.skipped,
    driveUrl: optionalString(record.drive_url),
    errorMessage: optionalString(record.error_message),
  };
}


function optionalString(value: string | null): string {
  return value ?? "";
}


function optionalApiString(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue === "" ? null : cleanedValue;
}
