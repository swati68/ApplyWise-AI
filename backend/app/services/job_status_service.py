from dataclasses import dataclass
from uuid import UUID

from app.models.job_posting import JobPosting
from app.models.job_posting import JobStatus as LegacyJobStatus
from app.models.job_status import JobStatus
from app.models.job_status_history import JobStatusHistory
from app.repositories.job_posting_repository import JobPostingRepository
from app.repositories.job_status_history_repository import JobStatusHistoryRepository
from app.repositories.job_status_repository import JobStatusRepository


DEFAULT_JOB_STATUSES: tuple[tuple[str, str | None], ...] = (
    ("New", "#64748b"),
    ("Matched", "#2563eb"),
    ("Resume Generated", "#7c3aed"),
    ("Applied", "#059669"),
    ("Phone Screen", "#0891b2"),
    ("Interview 1", "#ea580c"),
    ("Interview 2", "#c2410c"),
    ("Offer", "#16a34a"),
    ("Rejected", "#dc2626"),
    ("Archived", "#71717a"),
)


LEGACY_STATUS_NAME_BY_VALUE: dict[LegacyJobStatus, str] = {
    LegacyJobStatus.NEW: "New",
    LegacyJobStatus.MATCHED: "Matched",
    LegacyJobStatus.RESUME_GENERATED: "Resume Generated",
    LegacyJobStatus.EMAILED: "Resume Generated",
    LegacyJobStatus.APPLIED: "Applied",
    LegacyJobStatus.ARCHIVED: "Archived",
}


@dataclass(frozen=True)
class StatusChangeResult:
    job: JobPosting
    history: JobStatusHistory | None


class JobStatusService:
    def __init__(
        self,
        *,
        status_repository: JobStatusRepository,
        history_repository: JobStatusHistoryRepository,
        job_repository: JobPostingRepository | None = None,
    ) -> None:
        self.status_repository = status_repository
        self.history_repository = history_repository
        self.job_repository = job_repository

    def ensure_default_statuses(self, user_id: UUID) -> list[JobStatus]:
        existing_statuses = self.status_repository.list_by_user(user_id)
        existing_names = {
            _normalize_status_name(status.name): status for status in existing_statuses
        }

        next_statuses = list(existing_statuses)
        for index, (name, color) in enumerate(DEFAULT_JOB_STATUSES):
            if _normalize_status_name(name) in existing_names:
                continue

            status = self.status_repository.create(
                user_id,
                {
                    "name": name,
                    "color": color,
                    "sort_order": (index + 1) * 10,
                    "is_default": True,
                },
            )
            next_statuses.append(status)

        return sorted(next_statuses, key=lambda status: (status.sort_order, status.name))

    def get_default_status(self, user_id: UUID, name: str) -> JobStatus:
        self.ensure_default_statuses(user_id)
        status = self.status_repository.find_by_name(user_id, name)
        if status is None:
            raise RuntimeError(f"Default job status was not created: {name}")

        return status

    def status_for_legacy_status(
        self,
        user_id: UUID,
        legacy_status: LegacyJobStatus,
    ) -> JobStatus:
        return self.get_default_status(
            user_id,
            LEGACY_STATUS_NAME_BY_VALUE.get(legacy_status, "New"),
        )

    def ensure_job_current_status(self, job: JobPosting) -> JobPosting:
        if job.current_status_id is not None:
            return job
        if self.job_repository is None:
            return job

        status = self.status_for_legacy_status(job.user_id, job.status)
        updated_job = self.job_repository.update(
            job,
            {"current_status_id": status.id},
        )
        self.history_repository.create(
            {
                "user_id": job.user_id,
                "job_id": job.id,
                "from_status_id": None,
                "to_status_id": status.id,
                "note": "Initial status.",
            }
        )
        return updated_job

    def record_initial_status(
        self,
        *,
        job: JobPosting,
        note: str = "Initial status.",
    ) -> JobStatusHistory | None:
        if job.current_status_id is None:
            return None

        return self.history_repository.create(
            {
                "user_id": job.user_id,
                "job_id": job.id,
                "from_status_id": None,
                "to_status_id": job.current_status_id,
                "note": note,
            }
        )

    def set_status_by_name(
        self,
        *,
        job: JobPosting,
        name: str,
        note: str | None = None,
    ) -> StatusChangeResult:
        status = self.get_default_status(job.user_id, name)
        return self.change_status(job=job, status=status, note=note)

    def change_status(
        self,
        *,
        job: JobPosting,
        status: JobStatus,
        note: str | None = None,
    ) -> StatusChangeResult:
        if status.user_id != job.user_id:
            raise ValueError("Status does not belong to this user.")
        if self.job_repository is None:
            raise RuntimeError("Job repository is required to change status.")

        from_status_id = job.current_status_id
        legacy_status = legacy_status_for_custom_name(status.name)
        update_values: dict[str, object] = {
            "current_status_id": status.id,
            "status": legacy_status,
        }

        if from_status_id == status.id:
            updated_job = self.job_repository.update(job, update_values)
            return StatusChangeResult(job=updated_job, history=None)

        updated_job = self.job_repository.update(job, update_values)
        history = self.history_repository.create(
            {
                "user_id": job.user_id,
                "job_id": job.id,
                "from_status_id": from_status_id,
                "to_status_id": status.id,
                "note": note,
            }
        )
        return StatusChangeResult(job=updated_job, history=history)


def legacy_status_for_custom_name(name: str) -> LegacyJobStatus:
    normalized_name = _normalize_status_name(name)
    if normalized_name == "new":
        return LegacyJobStatus.NEW
    if normalized_name == "resume generated":
        return LegacyJobStatus.RESUME_GENERATED
    if normalized_name == "applied":
        return LegacyJobStatus.APPLIED
    if normalized_name in {"archived", "rejected"}:
        return LegacyJobStatus.ARCHIVED

    return LegacyJobStatus.MATCHED


def _normalize_status_name(value: str) -> str:
    return " ".join(value.strip().casefold().split())
