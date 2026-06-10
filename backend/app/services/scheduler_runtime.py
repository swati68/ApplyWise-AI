import logging

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models.scheduler import SchedulerTriggerType
from app.services.scheduler_service import (
    SchedulerAutomationService,
    SchedulerNotReadyError,
    SchedulerRunAlreadyInProgressError,
)


logger = logging.getLogger(__name__)
_scheduler = None


def start_scheduler(settings: Settings | None = None) -> None:
    global _scheduler
    active_settings = settings or get_settings()
    if not active_settings.scheduler_enabled:
        logger.info("scheduler_startup_skipped", extra={"scheduler_enabled": False})
        return

    if _scheduler is not None:
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.exception("scheduler_startup_failed_missing_apscheduler")
        return

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _run_due_scheduled_jobs,
        "interval",
        minutes=1,
        id="applywise_scheduled_morning_scan",
        max_instances=1,
        coalesce=True,
        kwargs={"trigger_type": SchedulerTriggerType.SCHEDULED_MORNING},
    )
    scheduler.add_job(
        _run_due_scheduled_jobs,
        "interval",
        minutes=1,
        id="applywise_scheduled_evening_scan",
        max_instances=1,
        coalesce=True,
        kwargs={"trigger_type": SchedulerTriggerType.SCHEDULED_EVENING},
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler_startup", extra={"scheduler_enabled": True})


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return

    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("scheduler_shutdown")


def _run_due_scheduled_jobs(*, trigger_type: SchedulerTriggerType) -> None:
    settings = get_settings()
    api_base_url = f"{settings.backend_url.rstrip('/')}{settings.api_prefix}"
    with SessionLocal() as db:
        service = SchedulerAutomationService(
            db=db,
            settings=settings,
            api_base_url=api_base_url,
        )
        candidates = service.due_candidates(trigger_type=trigger_type)
        for candidate in candidates:
            try:
                service.run_for_user(
                    user_id=candidate.user_id,
                    trigger_type=candidate.trigger_type,
                )
            except SchedulerRunAlreadyInProgressError:
                logger.info(
                    "scheduler_user_skipped_run_in_progress",
                    extra={"user_id": str(candidate.user_id)},
                )
            except SchedulerNotReadyError:
                logger.info(
                    "scheduler_user_skipped_not_ready",
                    extra={"user_id": str(candidate.user_id)},
                )
            except Exception:
                logger.exception(
                    "scheduler_user_run_failed",
                    extra={
                        "user_id": str(candidate.user_id),
                        "trigger_type": candidate.trigger_type.value,
                    },
                )
