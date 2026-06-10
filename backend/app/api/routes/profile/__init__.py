from fastapi import APIRouter

from app.api.routes.profile.education import router as education_router
from app.api.routes.profile.experience import router as experience_router
from app.api.routes.profile.projects import router as projects_router
from app.api.routes.profile.skills import router as skills_router


profile_routers: list[APIRouter] = [
    education_router,
    experience_router,
    projects_router,
    skills_router,
]
