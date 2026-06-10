import { request } from "@/lib/api-client";


export type SchedulerTriggerType =
  | "manual"
  | "scheduled_morning"
  | "scheduled_evening";


export type SchedulerRunStatus =
  | "running"
  | "success"
  | "partial_success"
  | "failed";


export type SchedulerPreference = {
  id: string;
  userId: string;
  enabled: boolean;
  timezone: string;
  morningEnabled: boolean;
  morningTime: string;
  eveningEnabled: boolean;
  eveningTime: string;
  minMatchScore: number;
  nextRunAt: string;
  createdAt: string;
  updatedAt: string;
};


export type SchedulerPreferenceValues = {
  enabled: boolean;
  timezone: string;
  morningEnabled: boolean;
  morningTime: string;
  eveningEnabled: boolean;
  eveningTime: string;
  minMatchScore: number;
};


export type SchedulerRun = {
  id: string;
  userId: string;
  triggerType: SchedulerTriggerType;
  startedAt: string;
  finishedAt: string;
  status: SchedulerRunStatus;
  totalSources: number;
  sourcesSucceeded: number;
  sourcesFailed: number;
  jobsScanned: number;
  jobsInserted: number;
  duplicatesSkipped: number;
  jobsMatched: number;
  resumesGenerated: number;
  pdfsCompiled: number;
  driveUploads: number;
  emailsSent: number;
  errorMessage: string;
  summary: Record<string, unknown> | null;
};


type SchedulerPreferenceApiRecord = {
  id: string;
  user_id: string;
  enabled: boolean;
  timezone: string;
  morning_enabled: boolean;
  morning_time: string;
  evening_enabled: boolean;
  evening_time: string;
  min_match_score: number;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
};


type SchedulerRunApiRecord = {
  id: string;
  user_id: string;
  trigger_type: SchedulerTriggerType;
  started_at: string;
  finished_at: string | null;
  status: SchedulerRunStatus;
  total_sources: number;
  sources_succeeded: number;
  sources_failed: number;
  jobs_scanned: number;
  jobs_inserted: number;
  duplicates_skipped: number;
  jobs_matched: number;
  resumes_generated: number;
  pdfs_compiled: number;
  drive_uploads: number;
  emails_sent: number;
  error_message: string | null;
  summary: Record<string, unknown> | null;
};


export const schedulerApi = {
  async preferences(): Promise<SchedulerPreference> {
    const record = await request<SchedulerPreferenceApiRecord>("/scheduler/preferences");
    return schedulerPreferenceFromApi(record);
  },

  async updatePreferences(
    values: SchedulerPreferenceValues,
  ): Promise<SchedulerPreference> {
    const record = await request<SchedulerPreferenceApiRecord>("/scheduler/preferences", {
      body: JSON.stringify(schedulerPreferenceToApi(values)),
      method: "PUT",
    });
    return schedulerPreferenceFromApi(record);
  },

  async runs(): Promise<SchedulerRun[]> {
    const records = await request<SchedulerRunApiRecord[]>("/scheduler/runs");
    return records.map(schedulerRunFromApi);
  },

  async runNow(): Promise<SchedulerRun> {
    const record = await request<SchedulerRunApiRecord>("/scheduler/run-now", {
      method: "POST",
    });
    return schedulerRunFromApi(record);
  },
};


function schedulerPreferenceFromApi(
  record: SchedulerPreferenceApiRecord,
): SchedulerPreference {
  return {
    id: record.id,
    userId: record.user_id,
    enabled: record.enabled,
    timezone: record.timezone,
    morningEnabled: record.morning_enabled,
    morningTime: record.morning_time.slice(0, 5),
    eveningEnabled: record.evening_enabled,
    eveningTime: record.evening_time.slice(0, 5),
    minMatchScore: record.min_match_score,
    nextRunAt: record.next_run_at ?? "",
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}


function schedulerPreferenceToApi(values: SchedulerPreferenceValues) {
  return {
    enabled: values.enabled,
    timezone: values.timezone,
    morning_enabled: values.morningEnabled,
    morning_time: values.morningTime,
    evening_enabled: values.eveningEnabled,
    evening_time: values.eveningTime,
    min_match_score: values.minMatchScore,
  };
}


function schedulerRunFromApi(record: SchedulerRunApiRecord): SchedulerRun {
  return {
    id: record.id,
    userId: record.user_id,
    triggerType: record.trigger_type,
    startedAt: record.started_at,
    finishedAt: record.finished_at ?? "",
    status: record.status,
    totalSources: record.total_sources,
    sourcesSucceeded: record.sources_succeeded,
    sourcesFailed: record.sources_failed,
    jobsScanned: record.jobs_scanned,
    jobsInserted: record.jobs_inserted,
    duplicatesSkipped: record.duplicates_skipped,
    jobsMatched: record.jobs_matched,
    resumesGenerated: record.resumes_generated,
    pdfsCompiled: record.pdfs_compiled,
    driveUploads: record.drive_uploads,
    emailsSent: record.emails_sent,
    errorMessage: record.error_message ?? "",
    summary: record.summary,
  };
}
