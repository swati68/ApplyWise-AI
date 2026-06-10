import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.scheduler import (
    SchedulerRun,
    SchedulerRunStatus,
    SchedulerTriggerType,
    UserSchedulerPreference,
)
from app.repositories.github_job_source_repository import GithubJobSourceRepository
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.scheduler_repository import (
    SchedulerRunRepository,
    UserSchedulerPreferenceRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.github_job_source_service import DisabledGithubSourceError, GithubSourceScanError
from app.services.github_pipeline_factory import build_github_source_pipeline_service
from app.services.google_integration_service import GoogleIntegrationService


logger = logging.getLogger(__name__)


class SchedulerRunAlreadyInProgressError(Exception):
    pass


class SchedulerNotReadyError(Exception):
    pass


@dataclass
class ScheduledDueCandidate:
    user_id: UUID
    trigger_type: SchedulerTriggerType


class SchedulerAutomationService:
    def __init__(
        self,
        *,
        db: Session,
        settings: Settings,
        api_base_url: str,
    ) -> None:
        self.db = db
        self.settings = settings
        self.api_base_url = api_base_url.rstrip("/")
        self.preference_repository = UserSchedulerPreferenceRepository(db)
        self.run_repository = SchedulerRunRepository(db)
        self.user_repository = UserRepository(db)
        self.source_repository = GithubJobSourceRepository(db)
        self.google_integration_service = GoogleIntegrationService(
            settings=settings,
            repository=GoogleIntegrationRepository(db),
        )

    def run_for_user(
        self,
        *,
        user_id: UUID,
        trigger_type: SchedulerTriggerType,
    ) -> SchedulerRun:
        running_run = self.run_repository.get_running_by_user(user_id)
        if running_run is not None:
            raise SchedulerRunAlreadyInProgressError("A scheduler run is already in progress.")

        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise SchedulerNotReadyError("User was not found.")

        preference = self.preference_repository.get_or_create_for_user(user_id)
        if trigger_type != SchedulerTriggerType.MANUAL and not preference.enabled:
            raise SchedulerNotReadyError("Scheduler is disabled for this user.")

        integration_status = self.google_integration_service.get_status(user_id)
        if not bool(integration_status["automation_ready"]):
            logger.info(
                "scheduler_user_skipped_not_ready",
                extra={"user_id": str(user_id), "trigger_type": trigger_type.value},
            )
            raise SchedulerNotReadyError(
                "Connect Google Drive and Gmail permissions before running automation.",
            )

        enabled_sources = self.source_repository.list_enabled_by_user(user_id)
        run = self.run_repository.create(
            {
                "user_id": user_id,
                "trigger_type": trigger_type,
                "status": SchedulerRunStatus.RUNNING,
                "total_sources": len(enabled_sources),
                "summary": {"sources": []},
            },
        )
        logger.info(
            "scheduled_run_started",
            extra={
                "user_id": str(user_id),
                "trigger_type": trigger_type.value,
                "total_sources": len(enabled_sources),
            },
        )

        totals: dict[str, int] = {
            "sources_succeeded": 0,
            "sources_failed": 0,
            "jobs_scanned": 0,
            "jobs_inserted": 0,
            "duplicates_skipped": 0,
            "jobs_matched": 0,
            "resumes_generated": 0,
            "pdfs_compiled": 0,
            "drive_uploads": 0,
            "emails_sent": 0,
        }
        source_summaries: list[dict[str, object]] = []
        run_errors: list[str] = []

        try:
            for source in enabled_sources:
                logger.info(
                    "scheduler_source_scan_started",
                    extra={"user_id": str(user_id), "source_id": str(source.id)},
                )
                try:
                    pipeline_service = build_github_source_pipeline_service(
                        db=self.db,
                        settings=self.settings,
                        user_id=user_id,
                        api_base_url=self.api_base_url,
                    )
                    pipeline_summary = pipeline_service.run(
                        source=source,
                        user=user,
                        min_match_score=preference.min_match_score,
                    )
                except (DisabledGithubSourceError, GithubSourceScanError, Exception) as error:
                    totals["sources_failed"] += 1
                    error_message = f"{source.name}: {error}"
                    run_errors.append(error_message)
                    source_summaries.append(
                        {
                            "source_id": str(source.id),
                            "source_name": source.name,
                            "status": "failed",
                            "error": str(error),
                        },
                    )
                    logger.exception(
                        "scheduler_source_failure",
                        extra={"user_id": str(user_id), "source_id": str(source.id)},
                    )
                    continue

                totals["sources_succeeded"] += 1
                totals["jobs_scanned"] += pipeline_summary.parsed_jobs
                totals["jobs_inserted"] += pipeline_summary.inserted_jobs
                totals["duplicates_skipped"] += pipeline_summary.duplicate_jobs
                totals["jobs_matched"] += pipeline_summary.jobs_matched
                totals["resumes_generated"] += pipeline_summary.resumes_generated
                totals["pdfs_compiled"] += pipeline_summary.pdfs_compiled
                totals["drive_uploads"] += pipeline_summary.drive_uploads_successful
                totals["emails_sent"] += pipeline_summary.emails_sent
                if pipeline_summary.emails_sent > 0:
                    logger.info(
                        "scheduler_digest_sent",
                        extra={"user_id": str(user_id), "source_id": str(source.id)},
                    )

                source_summaries.append(
                    {
                        "source_id": str(source.id),
                        "source_name": source.name,
                        "status": "success",
                        "rows_seen": pipeline_summary.total_rows_seen,
                        "parsed_jobs": pipeline_summary.parsed_jobs,
                        "inserted_jobs": pipeline_summary.inserted_jobs,
                        "duplicate_jobs": pipeline_summary.duplicate_jobs,
                        "jobs_matched": pipeline_summary.jobs_matched,
                        "resumes_generated": pipeline_summary.resumes_generated,
                        "pdfs_compiled": pipeline_summary.pdfs_compiled,
                        "drive_uploads": pipeline_summary.drive_uploads_successful,
                        "emails_sent": pipeline_summary.emails_sent,
                        "errors": pipeline_summary.errors,
                    },
                )
                logger.info(
                    "scheduler_source_scan_finished",
                    extra={
                        "user_id": str(user_id),
                        "source_id": str(source.id),
                        "jobs_matched": pipeline_summary.jobs_matched,
                    },
                )

            status = _finished_status(
                sources_succeeded=totals["sources_succeeded"],
                sources_failed=totals["sources_failed"],
            )
            updated_run = self.run_repository.update(
                run,
                {
                    **totals,
                    "finished_at": datetime.now(UTC),
                    "status": status,
                    "error_message": "; ".join(run_errors)[:2000] if run_errors else None,
                    "summary": {
                        "sources": source_summaries,
                        "errors": run_errors,
                    },
                },
            )
            logger.info(
                "scheduled_run_finished",
                extra={
                    "user_id": str(user_id),
                    "trigger_type": trigger_type.value,
                    "status": status.value,
                    "jobs_matched": totals["jobs_matched"],
                    "resumes_generated": totals["resumes_generated"],
                },
            )
            return updated_run
        except Exception as error:
            logger.exception(
                "scheduled_run_failed",
                extra={"user_id": str(user_id), "trigger_type": trigger_type.value},
            )
            return self.run_repository.update(
                run,
                {
                    "finished_at": datetime.now(UTC),
                    "status": SchedulerRunStatus.FAILED,
                    "error_message": str(error)[:2000],
                    "summary": {
                        "sources": source_summaries,
                        "errors": [*run_errors, str(error)],
                    },
                },
            )

    def due_candidates(
        self,
        *,
        trigger_type: SchedulerTriggerType,
        now_utc: datetime | None = None,
    ) -> list[ScheduledDueCandidate]:
        now = now_utc or datetime.now(UTC)
        candidates: list[ScheduledDueCandidate] = []
        for preference in self.preference_repository.list_enabled():
            if not _preference_trigger_enabled(preference, trigger_type):
                continue
            if not _is_preference_due(preference, trigger_type, now):
                continue

            day_start_utc, day_end_utc = _local_day_bounds_utc(preference, now)
            if self.run_repository.has_run_between(
                user_id=preference.user_id,
                trigger_type=trigger_type,
                started_from=day_start_utc,
                started_to=day_end_utc,
            ):
                continue

            candidates.append(
                ScheduledDueCandidate(
                    user_id=preference.user_id,
                    trigger_type=trigger_type,
                ),
            )

        return candidates


def calculate_next_run_at(
    preference: UserSchedulerPreference,
    now_utc: datetime | None = None,
) -> datetime | None:
    if not preference.enabled:
        return None

    timezone = _timezone_or_default(preference.timezone)
    now = now_utc or datetime.now(UTC)
    local_now = now.astimezone(timezone)
    candidates: list[datetime] = []
    for enabled, run_time in [
        (preference.morning_enabled, preference.morning_time),
        (preference.evening_enabled, preference.evening_time),
    ]:
        if not enabled:
            continue
        candidate = datetime.combine(local_now.date(), run_time, tzinfo=timezone)
        if candidate <= local_now:
            candidate += timedelta(days=1)
        candidates.append(candidate.astimezone(UTC))

    return min(candidates) if candidates else None


def _finished_status(
    *,
    sources_succeeded: int,
    sources_failed: int,
) -> SchedulerRunStatus:
    if sources_failed == 0:
        return SchedulerRunStatus.SUCCESS
    if sources_succeeded > 0:
        return SchedulerRunStatus.PARTIAL_SUCCESS
    return SchedulerRunStatus.FAILED


def _preference_trigger_enabled(
    preference: UserSchedulerPreference,
    trigger_type: SchedulerTriggerType,
) -> bool:
    if trigger_type == SchedulerTriggerType.SCHEDULED_MORNING:
        return preference.morning_enabled
    if trigger_type == SchedulerTriggerType.SCHEDULED_EVENING:
        return preference.evening_enabled

    return False


def _is_preference_due(
    preference: UserSchedulerPreference,
    trigger_type: SchedulerTriggerType,
    now_utc: datetime,
) -> bool:
    timezone = _timezone_or_default(preference.timezone)
    local_now = now_utc.astimezone(timezone)
    target_time = _target_time(preference, trigger_type)
    return local_now.hour == target_time.hour and local_now.minute == target_time.minute


def _target_time(
    preference: UserSchedulerPreference,
    trigger_type: SchedulerTriggerType,
) -> time:
    if trigger_type == SchedulerTriggerType.SCHEDULED_MORNING:
        return preference.morning_time
    if trigger_type == SchedulerTriggerType.SCHEDULED_EVENING:
        return preference.evening_time

    raise ValueError(f"Unsupported scheduled trigger type: {trigger_type}")


def _local_day_bounds_utc(
    preference: UserSchedulerPreference,
    now_utc: datetime,
) -> tuple[datetime, datetime]:
    timezone = _timezone_or_default(preference.timezone)
    local_now = now_utc.astimezone(timezone)
    local_start = datetime.combine(local_now.date(), time.min, tzinfo=timezone)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _timezone_or_default(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return ZoneInfo("America/New_York")
