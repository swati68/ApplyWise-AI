from __future__ import annotations

import re
import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from app.core.config import Settings, get_settings
from app.services.ai.prompts import (
    JOB_REQUIREMENTS_SYSTEM_PROMPT,
    RESUME_TAILORING_SYSTEM_PROMPT,
    build_job_requirements_prompt,
    build_resume_tailoring_prompt,
)
from app.services.ai.schemas import JobRequirements, TailoredLatexResume


logger = logging.getLogger(__name__)


class AIProvider(ABC):
    @abstractmethod
    def extract_job_requirements(self, job_text: str) -> JobRequirements:
        raise NotImplementedError

    @abstractmethod
    def tailor_latex_resume(
        self,
        *,
        profile_json: Any,
        job_json: Any,
        latex_template: str,
    ) -> TailoredLatexResume:
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, timeout=12.0, max_retries=1)
        self.model = model

    def extract_job_requirements(self, job_text: str) -> JobRequirements:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": JOB_REQUIREMENTS_SYSTEM_PROMPT},
                {"role": "user", "content": build_job_requirements_prompt(job_text)},
            ],
            text_format=JobRequirements,
            temperature=0,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned an empty job requirements response.")

        return response.output_parsed

    def tailor_latex_resume(
        self,
        *,
        profile_json: Any,
        job_json: Any,
        latex_template: str,
    ) -> TailoredLatexResume:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": RESUME_TAILORING_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_resume_tailoring_prompt(
                        profile_json=profile_json,
                        job_json=job_json,
                        latex_template=latex_template,
                    ),
                },
            ],
            text_format=TailoredLatexResume,
            temperature=0,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned an empty tailored resume response.")

        return response.output_parsed


class MockAIProvider(AIProvider):
    def extract_job_requirements(self, job_text: str) -> JobRequirements:
        cleaned_text = job_text.strip()
        role_title = _extract_role_title(cleaned_text)
        skills = _extract_known_skills(cleaned_text)

        return JobRequirements(
            role_title=role_title,
            seniority=_extract_seniority(cleaned_text),
            required_skills=skills,
            preferred_skills=[],
            responsibilities=_extract_responsibilities(cleaned_text),
            keywords=skills,
            location_constraints=_extract_location_constraints(cleaned_text),
            summary=cleaned_text[:240],
        )

    def tailor_latex_resume(
        self,
        *,
        profile_json: Any,
        job_json: Any,
        latex_template: str,
    ) -> TailoredLatexResume:
        profile_text = str(profile_json).casefold()
        required_skills = _get_required_skills(job_json)
        safety_warnings = [
            f"Required skill missing from verified profile: {skill}"
            for skill in required_skills
            if skill.casefold() not in profile_text
        ]

        return TailoredLatexResume(
            tailored_latex=latex_template,
            selected_experiences=[],
            selected_projects=[],
            selected_skills=[
                skill for skill in required_skills if skill.casefold() in profile_text
            ],
            change_summary=[
                "Mock AI provider returned the original LaTeX template unchanged.",
            ],
            safety_warnings=safety_warnings,
        )


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    return _build_ai_provider(settings)


def extract_job_requirements(job_text: str) -> dict[str, object]:
    try:
        return get_ai_provider().extract_job_requirements(job_text).model_dump()
    except Exception as error:
        logger.warning("Falling back to mock job requirements extraction: %s", error)
        return MockAIProvider().extract_job_requirements(job_text).model_dump()


def tailor_latex_resume(
    profile_json: Any,
    job_json: Any,
    latex_template: str,
) -> dict[str, object]:
    try:
        return get_ai_provider().tailor_latex_resume(
            profile_json=profile_json,
            job_json=job_json,
            latex_template=latex_template,
        ).model_dump()
    except Exception as error:
        logger.warning("Falling back to mock LaTeX tailoring: %s", error)
        return MockAIProvider().tailor_latex_resume(
            profile_json=profile_json,
            job_json=job_json,
            latex_template=latex_template,
        ).model_dump()


def _build_ai_provider(settings: Settings) -> AIProvider:
    if settings.openai_api_key.strip() == "":
        return MockAIProvider()

    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def _extract_role_title(job_text: str) -> str:
    for line in job_text.splitlines():
        cleaned_line = line.strip(" #*-")
        if cleaned_line:
            return cleaned_line[:120]

    return ""


def _extract_seniority(job_text: str) -> str:
    lowered_text = job_text.casefold()
    seniority_terms = ["intern", "junior", "senior", "staff", "principal", "lead"]
    for term in seniority_terms:
        if term in lowered_text:
            return term

    return ""


def _extract_known_skills(job_text: str) -> list[str]:
    known_skills = [
        "Python",
        "JavaScript",
        "TypeScript",
        "React",
        "Next.js",
        "FastAPI",
        "SQL",
        "PostgreSQL",
        "AWS",
        "Docker",
        "Kubernetes",
        "Machine Learning",
        "Data Engineering",
    ]
    lowered_text = job_text.casefold()
    return [skill for skill in known_skills if skill.casefold() in lowered_text]


def _extract_responsibilities(job_text: str) -> list[str]:
    responsibilities: list[str] = []
    for line in job_text.splitlines():
        cleaned_line = line.strip(" -*\t")
        if len(cleaned_line) >= 24:
            responsibilities.append(cleaned_line)
        if len(responsibilities) == 5:
            break

    return responsibilities


def _extract_location_constraints(job_text: str) -> list[str]:
    patterns = ["remote", "hybrid", "onsite", "visa", "timezone", "relocation"]
    lowered_text = job_text.casefold()
    return [pattern for pattern in patterns if pattern in lowered_text]


def _get_required_skills(job_json: Any) -> list[str]:
    if isinstance(job_json, dict):
        required_skills = job_json.get("required_skills")
        if isinstance(required_skills, list):
            return [str(skill) for skill in required_skills]

    matches = re.findall(r"required_skills['\"]?:\s*\[([^\]]*)\]", str(job_json))
    if not matches:
        return []

    return [
        skill.strip(" '\"")
        for skill in matches[0].split(",")
        if skill.strip(" '\"")
    ]
