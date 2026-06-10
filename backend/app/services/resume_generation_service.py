import re
from uuid import UUID

from app.models.generated_resume import GeneratedResume
from app.models.job_match import JobMatch
from app.models.job_posting import JobPosting
from app.repositories.generated_resume_repository import GeneratedResumeRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_posting_repository import JobPostingRepository
from app.repositories.profile_repository import (
    EducationRepository,
    ExperienceRepository,
    ProjectRepository,
    SkillRepository,
)
from app.repositories.resume_template_repository import ResumeTemplateRepository
from app.services.ai.openai_client import tailor_latex_resume
from app.services.job_match_service import JobMatchService


class NoDefaultResumeTemplateError(Exception):
    pass


class ResumeGenerationBlockedError(Exception):
    pass


class ResumeGenerationService:
    def __init__(
        self,
        *,
        generated_resume_repository: GeneratedResumeRepository,
        job_repository: JobPostingRepository,
        job_match_repository: JobMatchRepository,
        resume_template_repository: ResumeTemplateRepository,
        education_repository: EducationRepository,
        experience_repository: ExperienceRepository,
        project_repository: ProjectRepository,
        skill_repository: SkillRepository,
    ) -> None:
        self.generated_resume_repository = generated_resume_repository
        self.job_repository = job_repository
        self.job_match_repository = job_match_repository
        self.resume_template_repository = resume_template_repository
        self.education_repository = education_repository
        self.experience_repository = experience_repository
        self.project_repository = project_repository
        self.skill_repository = skill_repository

    def generate_for_job(self, *, user_id: UUID, job: JobPosting) -> GeneratedResume:
        match = self.job_match_repository.get_latest_for_job(user_id, job.id)
        if _needs_fresh_match(job, match):
            match = JobMatchService(
                self.job_match_repository,
                job_repository=self.job_repository,
            ).match_job(user_id=user_id, job=job)

        if _is_skipped_match(match):
            raise ResumeGenerationBlockedError(match.match_reason)

        template = self.resume_template_repository.get_default_for_user(user_id)
        if template is None:
            raise NoDefaultResumeTemplateError("Create and mark a default resume template first.")
        if template.latex_content.strip() == "":
            raise ResumeGenerationBlockedError("Default resume template is empty.")

        profile_context = self._build_profile_context(user_id)
        job_context = _build_job_context(job, match)
        ai_result = tailor_latex_resume(
            profile_json=profile_context,
            job_json=job_context,
            latex_template=template.latex_content,
        )
        tailored_latex = str(ai_result.get("tailored_latex") or "")
        if tailored_latex.strip() == "":
            raise ResumeGenerationBlockedError("AI did not return tailored LaTeX content.")

        selected_experiences = _as_string_list(ai_result.get("selected_experiences"))
        selected_projects = _as_string_list(ai_result.get("selected_projects"))
        selected_skills = _verified_selected_skills(
            _as_string_list(ai_result.get("selected_skills")),
            profile_context,
        )
        change_summary = _as_string_list(ai_result.get("change_summary"))
        safety_warnings = _as_string_list(ai_result.get("safety_warnings"))
        unverified_bullets = _find_unverified_latex_bullets(
            tailored_latex=tailored_latex,
            latex_template=template.latex_content,
            profile_context=profile_context,
        )
        if unverified_bullets:
            tailored_latex = template.latex_content
            change_summary.append(
                "Kept original LaTeX template because AI returned unverified bullet text.",
            )
            safety_warnings.append(
                "AI output contained resume bullets that were not copied from the "
                "saved profile or original template, so the original template was used.",
            )

        return self.generated_resume_repository.create(
            {
                "user_id": user_id,
                "job_id": job.id,
                "resume_template_id": template.id,
                "tailored_latex": tailored_latex,
                "selected_experiences": selected_experiences,
                "selected_projects": selected_projects,
                "selected_skills": selected_skills,
                "change_summary": change_summary,
                "safety_warnings": safety_warnings,
                "pdf_path": None,
                "drive_url": None,
            }
        )

    def _build_profile_context(self, user_id: UUID) -> dict[str, object]:
        education = self.education_repository.list_by_user(user_id)
        experiences = self.experience_repository.list_by_user(user_id)
        projects = self.project_repository.list_by_user(user_id)
        skills = self.skill_repository.list_by_user(user_id)

        return {
            "education": [
                {
                    "id": str(item.id),
                    "institution": item.institution,
                    "degree": item.degree,
                    "field_of_study": item.field_of_study,
                    "start_date": _format_date(item.start_date),
                    "end_date": _format_date(item.end_date),
                    "gpa": item.gpa,
                    "location": item.location,
                    "description": item.description,
                }
                for item in education
            ],
            "experiences": [
                {
                    "id": str(item.id),
                    "company": item.company,
                    "role": item.role,
                    "location": item.location,
                    "start_date": _format_date(item.start_date),
                    "end_date": _format_date(item.end_date),
                    "is_current": item.is_current,
                    "tech_stack": item.tech_stack,
                    "bullets": item.bullets,
                    "tags": item.tags,
                }
                for item in experiences
            ],
            "projects": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "description": item.description,
                    "tech_stack": item.tech_stack,
                    "bullets": item.bullets,
                    "links": item.links,
                    "tags": item.tags,
                }
                for item in projects
            ],
            "skills": [
                {
                    "id": str(item.id),
                    "category": item.category,
                    "name": item.name,
                    "proficiency": item.proficiency,
                    "tags": item.tags,
                }
                for item in skills
            ],
        }


def _needs_fresh_match(job: JobPosting, match: JobMatch | None) -> bool:
    if match is None:
        return True
    if _is_skipped_match(match):
        return True
    if _clean_optional_text(job.extracted_description) is None:
        return True
    if job.extracted_at is not None and match.created_at is not None:
        try:
            return match.created_at < job.extracted_at
        except TypeError:
            return False

    return False


def _is_skipped_match(match: JobMatch) -> bool:
    return match.match_reason.startswith("Skipped matching")


def _build_job_context(job: JobPosting, match: JobMatch) -> dict[str, object]:
    return {
        "job": {
            "id": str(job.id),
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "job_url": job.job_url,
            "extracted_description": job.extracted_description,
        },
        "match": {
            "id": str(match.id),
            "score": match.score,
            "exact_skill_matches": match.exact_skill_matches,
            "fuzzy_skill_matches": match.fuzzy_skill_matches,
            "missing_skills": match.missing_skills,
            "relevant_experiences": match.relevant_experiences,
            "relevant_projects": match.relevant_projects,
            "match_reason": match.match_reason,
        },
    }


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None


def _format_date(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return str(value.isoformat())

    return str(value)


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def _verified_selected_skills(
    selected_skills: list[str],
    profile_context: dict[str, object],
) -> list[str]:
    verified_skills = {
        _normalize_plain_text(str(skill.get("name", "")))
        for skill in _dict_items(profile_context.get("skills"))
    }
    return [
        skill
        for skill in selected_skills
        if _normalize_plain_text(skill) in verified_skills
    ]


def _find_unverified_latex_bullets(
    *,
    tailored_latex: str,
    latex_template: str,
    profile_context: dict[str, object],
) -> list[str]:
    allowed_bullets = {
        _normalize_latex_bullet(bullet)
        for bullet in [
            *_extract_latex_item_bullets(latex_template),
            *_profile_bullets(profile_context),
        ]
    }
    allowed_bullets.discard("")

    unverified_bullets: list[str] = []
    for bullet in _extract_latex_item_bullets(tailored_latex):
        normalized_bullet = _normalize_latex_bullet(bullet)
        if normalized_bullet and normalized_bullet not in allowed_bullets:
            unverified_bullets.append(bullet)

    return unverified_bullets


def _profile_bullets(profile_context: dict[str, object]) -> list[str]:
    bullets: list[str] = []
    for section in ("experiences", "projects"):
        for item in _dict_items(profile_context.get(section)):
            section_bullets = item.get("bullets", [])
            if isinstance(section_bullets, list):
                bullets.extend(str(bullet) for bullet in section_bullets)

    return bullets


def _dict_items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    return [item for item in value if isinstance(item, dict)]


def _extract_latex_item_bullets(latex_content: str) -> list[str]:
    item_pattern = re.compile(
        r"\\item\s+(.*?)(?=\s*\\item\b|\s*\\end\{itemize\}|\Z)",
        re.DOTALL,
    )
    return [
        _strip_latex_comments(match.group(1)).strip()
        for match in item_pattern.finditer(latex_content)
    ]


def _strip_latex_comments(value: str) -> str:
    return "\n".join(line.split("%", 1)[0] for line in value.splitlines())


def _normalize_latex_bullet(value: str) -> str:
    normalized_value = value
    for latex_escape, plain_text in {
        r"\&": "&",
        r"\%": "%",
        r"\$": "$",
        r"\#": "#",
        r"\_": "_",
    }.items():
        normalized_value = normalized_value.replace(latex_escape, plain_text)

    return _normalize_plain_text(normalized_value)


def _normalize_plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
