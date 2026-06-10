import { request } from "@/lib/api-client";


export type GithubJobSource = {
  id: string;
  userId: string;
  name: string;
  repoUrl: string;
  rawReadmeUrl: string;
  branch: string;
  enabled: boolean;
  scanRoleTags: string[];
  includeKeywords: string[];
  excludeKeywords: string[];
  scanInstructions: string;
  lastScannedAt: string;
  createdAt: string;
  updatedAt: string;
};


export type GithubJobSourceValues = {
  name: string;
  repoUrl: string;
  rawReadmeUrl: string;
  branch: string;
  enabled: boolean;
  scanRoleTags: string[];
  includeKeywords: string[];
  excludeKeywords: string[];
  scanInstructions: string;
};


export type GithubSourceRunSummary = {
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
  uploadedPdfs: number;
  pdfsCompiled: number;
  driveUploadsSuccessful: number;
  emailsSent: number;
  durationSeconds: number;
  errors: string[];
  message: string;
};


export type GithubSourceScanResult = GithubSourceRunSummary & {
  source: GithubJobSource;
};


export type GithubSourcePipelineResult = GithubSourceRunSummary;


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


type GithubSourceScanApiResult = {
  source: GithubJobSourceApiRecord;
  total_rows_seen: number;
  parsed_jobs: number;
  scanned_jobs: number;
  inserted_jobs: number;
  duplicate_jobs: number;
  rows_skipped_by_filters: number;
  jobs_tagged: number;
  extraction_success_count: number;
  extraction_failed_count: number;
  matched_jobs: number;
  generated_resumes: number;
  uploaded_pdfs: number;
  message: string;
};


type GithubSourcePipelineApiResult = {
  total_rows_seen: number;
  parsed_jobs: number;
  rows_skipped_by_filters: number;
  inserted_jobs: number;
  duplicate_jobs: number;
  jobs_tagged: number;
  extraction_success_count: number;
  extraction_failed_count: number;
  jobs_matched: number;
  resumes_generated: number;
  pdfs_compiled: number;
  drive_uploads_successful: number;
  emails_sent: number;
  duration_seconds: number;
  errors: string[];
};


export const githubSourcesApi = {
  async list(): Promise<GithubJobSource[]> {
    const records = await request<GithubJobSourceApiRecord[]>("/github-sources");
    return records.map(githubSourceFromApi);
  },

  async create(values: GithubJobSourceValues): Promise<GithubJobSource> {
    const record = await request<GithubJobSourceApiRecord>("/github-sources", {
      body: JSON.stringify(githubSourceToApi(values)),
      method: "POST",
    });
    return githubSourceFromApi(record);
  },

  async update(
    sourceId: string,
    values: Partial<GithubJobSourceValues>,
  ): Promise<GithubJobSource> {
    const record = await request<GithubJobSourceApiRecord>(`/github-sources/${sourceId}`, {
      body: JSON.stringify(partialGithubSourceToApi(values)),
      method: "PUT",
    });
    return githubSourceFromApi(record);
  },

  async delete(sourceId: string): Promise<void> {
    await request<void>(`/github-sources/${sourceId}`, {
      method: "DELETE",
    });
  },

  async scan(sourceId: string): Promise<GithubSourceScanResult> {
    const result = await request<GithubSourceScanApiResult>(
      `/github-sources/${sourceId}/scan`,
      {
        method: "POST",
      },
    );
    return {
      source: githubSourceFromApi(result.source),
      totalRowsSeen: result.total_rows_seen,
      parsedJobs: result.parsed_jobs,
      scannedJobs: result.scanned_jobs,
      insertedJobs: result.inserted_jobs,
      duplicateJobs: result.duplicate_jobs,
      rowsSkippedByFilters: result.rows_skipped_by_filters,
      jobsTagged: result.jobs_tagged,
      extractionSuccessCount: result.extraction_success_count,
      extractionFailedCount: result.extraction_failed_count,
      matchedJobs: result.matched_jobs,
      generatedResumes: result.generated_resumes,
      uploadedPdfs: result.uploaded_pdfs,
      pdfsCompiled: 0,
      driveUploadsSuccessful: 0,
      emailsSent: 0,
      durationSeconds: 0,
      errors: [],
      message: result.message,
    };
  },

  async runPipeline(sourceId: string): Promise<GithubSourcePipelineResult> {
    const result = await request<GithubSourcePipelineApiResult>(
      `/github-sources/${sourceId}/run-pipeline`,
      {
        method: "POST",
      },
    );
    return {
      totalRowsSeen: result.total_rows_seen,
      parsedJobs: result.parsed_jobs,
      scannedJobs: result.parsed_jobs,
      rowsSkippedByFilters: result.rows_skipped_by_filters,
      insertedJobs: result.inserted_jobs,
      duplicateJobs: result.duplicate_jobs,
      jobsTagged: result.jobs_tagged,
      extractionSuccessCount: result.extraction_success_count,
      extractionFailedCount: result.extraction_failed_count,
      matchedJobs: result.jobs_matched,
      generatedResumes: result.resumes_generated,
      uploadedPdfs: result.drive_uploads_successful,
      pdfsCompiled: result.pdfs_compiled,
      driveUploadsSuccessful: result.drive_uploads_successful,
      emailsSent: result.emails_sent,
      durationSeconds: result.duration_seconds,
      errors: result.errors,
      message:
        result.errors.length > 0
          ? `GitHub pipeline completed. ${result.errors.length} item${result.errors.length === 1 ? "" : "s"} could not be fully processed.`
          : "GitHub pipeline completed.",
    };
  },
};


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
    scanInstructions: record.scan_instructions ?? "",
    lastScannedAt: record.last_scanned_at ?? "",
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}


function githubSourceToApi(values: GithubJobSourceValues) {
  return {
    name: values.name,
    repo_url: values.repoUrl,
    raw_readme_url: values.rawReadmeUrl,
    branch: values.branch,
    enabled: values.enabled,
    scan_role_tags: values.scanRoleTags,
    include_keywords: values.includeKeywords,
    exclude_keywords: values.excludeKeywords,
    scan_instructions: optionalApiString(values.scanInstructions),
  };
}


function partialGithubSourceToApi(values: Partial<GithubJobSourceValues>) {
  return {
    ...(values.name !== undefined ? { name: values.name } : {}),
    ...(values.repoUrl !== undefined ? { repo_url: values.repoUrl } : {}),
    ...(values.rawReadmeUrl !== undefined
      ? { raw_readme_url: values.rawReadmeUrl }
      : {}),
    ...(values.branch !== undefined ? { branch: values.branch } : {}),
    ...(values.enabled !== undefined ? { enabled: values.enabled } : {}),
    ...(values.scanRoleTags !== undefined ? { scan_role_tags: values.scanRoleTags } : {}),
    ...(values.includeKeywords !== undefined
      ? { include_keywords: values.includeKeywords }
      : {}),
    ...(values.excludeKeywords !== undefined
      ? { exclude_keywords: values.excludeKeywords }
      : {}),
    ...(values.scanInstructions !== undefined
      ? { scan_instructions: optionalApiString(values.scanInstructions) }
      : {}),
  };
}


function optionalApiString(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue === "" ? null : cleanedValue;
}
