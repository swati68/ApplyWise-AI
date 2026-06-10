from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.digests import router as digests_router
from app.api.routes.generated_resumes import router as generated_resumes_router
from app.api.routes.github_sources import router as github_sources_router
from app.api.routes.google_integrations import router as google_integrations_router
from app.api.routes.health import router as health_router
from app.api.routes.job_statuses import router as job_statuses_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.profile import profile_routers
from app.api.routes.resume_templates import router as resume_templates_router
from app.api.routes.scheduler import router as scheduler_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.services.scheduler_runtime import start_scheduler, stop_scheduler


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(users_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(job_statuses_router, prefix=settings.api_prefix)
    app.include_router(digests_router, prefix=settings.api_prefix)
    app.include_router(generated_resumes_router, prefix=settings.api_prefix)
    app.include_router(github_sources_router, prefix=settings.api_prefix)
    app.include_router(google_integrations_router, prefix=settings.api_prefix)
    app.include_router(resume_templates_router, prefix=settings.api_prefix)
    app.include_router(scheduler_router, prefix=settings.api_prefix)
    for profile_router in profile_routers:
        app.include_router(profile_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def start_background_scheduler() -> None:
        start_scheduler(settings)

    @app.on_event("shutdown")
    def stop_background_scheduler() -> None:
        stop_scheduler()

    return app


app = create_app()
