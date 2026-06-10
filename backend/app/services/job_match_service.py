from datetime import UTC, datetime
from dataclasses import dataclass
from uuid import UUID

from rapidfuzz import fuzz, process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.experience import Experience
from app.models.job_match import JobMatch
from app.models.job_posting import JobExtractionStatus, JobPosting
from app.models.project import Project
from app.models.skill import Skill
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_posting_repository import JobPostingRepository
from app.services.ai.openai_client import extract_job_requirements
from app.services.jobs.job_content_extractor import (
    ExtractedJobContent,
    JobContentExtractorService,
)


EXACT_SKILL_WEIGHT = 40
FUZZY_SKILL_WEIGHT = 20
RELEVANCE_WEIGHT = 30
TITLE_LOCATION_WEIGHT = 10
FUZZY_MATCH_THRESHOLD = 82
MIN_STORED_MATCH_SCORE = 20


class LowMatchScoreError(Exception):
    def __init__(self, *, score: int, minimum_score: int) -> None:
        self.score = score
        self.minimum_score = minimum_score
        super().__init__(
            f"Match score {score} is below the minimum {minimum_score}; match was not stored and resume generation was skipped.",
        )


@dataclass(frozen=True)
class ProfileSnapshot:
    skills: list[Skill]
    experiences: list[Experience]
    projects: list[Project]


class JobMatchService:
    def __init__(
        self,
        repository: JobMatchRepository,
        *,
        job_repository: JobPostingRepository | None = None,
        extractor: JobContentExtractorService | None = None,
    ) -> None:
        self.repository = repository
        self.job_repository = job_repository
        self.extractor = extractor or JobContentExtractorService()

    def match_job(self, *, user_id: UUID, job: JobPosting) -> JobMatch:
        extracted_description = self._get_matchable_description(job)
        if extracted_description is None:
            return self._create_skipped_match(
                user_id=user_id,
                job=job,
                reason=_missing_extracted_description_reason(job),
            )

        profile = ProfileSnapshot(
            skills=self.repository.list_user_skills(user_id),
            experiences=self.repository.list_user_experiences(user_id),
            projects=self.repository.list_user_projects(user_id),
        )
        requirements = extract_job_requirements(extracted_description)
        target_skills = _dedupe(
            _as_strings(requirements.get("required_skills"))
            + _as_strings(requirements.get("preferred_skills"))
        )
        profile_terms = _profile_skill_terms(profile)

        exact_matches = _exact_skill_matches(target_skills, profile_terms)
        fuzzy_matches = _fuzzy_skill_matches(target_skills, profile_terms, exact_matches)
        missing_skills = _missing_skills(target_skills, exact_matches, fuzzy_matches)

        relevance = _score_profile_relevance(extracted_description, requirements, profile)
        title_location_score = _score_title_location(job, profile)

        exact_component = _ratio_score(len(exact_matches), len(target_skills), EXACT_SKILL_WEIGHT)
        fuzzy_component = _ratio_score(
            len(fuzzy_matches),
            len(target_skills),
            FUZZY_SKILL_WEIGHT,
        )
        total_score = round(
            exact_component
            + fuzzy_component
            + relevance.component_score
            + title_location_score,
        )
        score = max(0, min(100, total_score))
        match_reason = _build_match_reason(
            exact_component=exact_component,
            fuzzy_component=fuzzy_component,
            relevance_component=relevance.component_score,
            title_location_component=title_location_score,
            exact_matches=exact_matches,
            fuzzy_matches=fuzzy_matches,
            missing_skills=missing_skills,
        )

        if score < MIN_STORED_MATCH_SCORE:
            raise LowMatchScoreError(
                score=score,
                minimum_score=MIN_STORED_MATCH_SCORE,
            )

        return self.repository.create(
            {
                "user_id": user_id,
                "job_id": job.id,
                "score": score,
                "exact_skill_matches": exact_matches,
                "fuzzy_skill_matches": fuzzy_matches,
                "missing_skills": missing_skills,
                "relevant_experiences": relevance.experiences,
                "relevant_projects": relevance.projects,
                "match_reason": match_reason,
            }
        )

    def _get_matchable_description(self, job: JobPosting) -> str | None:
        if job.extraction_status == JobExtractionStatus.FAILED:
            return None

        existing_description = _clean_optional_text(job.extracted_description)
        if existing_description is not None:
            return existing_description

        if self.job_repository is None or _clean_optional_text(job.job_url) is None:
            return None

        extracted_content = self.extractor.extract_job_content(str(job.job_url))
        _store_extraction_result(self.job_repository, job, extracted_content)
        if not extracted_content.extraction_success:
            return None

        return _clean_optional_text(extracted_content.cleaned_text)

    def _create_skipped_match(
        self,
        *,
        user_id: UUID,
        job: JobPosting,
        reason: str,
    ) -> JobMatch:
        return self.repository.create(
            {
                "user_id": user_id,
                "job_id": job.id,
                "score": 0,
                "exact_skill_matches": [],
                "fuzzy_skill_matches": [],
                "missing_skills": [],
                "relevant_experiences": [],
                "relevant_projects": [],
                "match_reason": reason,
            }
        )


@dataclass(frozen=True)
class RelevanceResult:
    component_score: float
    experiences: list[dict[str, object]]
    projects: list[dict[str, object]]


def _store_extraction_result(
    job_repository: JobPostingRepository,
    job: JobPosting,
    extracted_content: ExtractedJobContent,
) -> JobPosting:
    extraction_status = (
        JobExtractionStatus.SUCCESS
        if extracted_content.extraction_success
        else JobExtractionStatus.FAILED
    )
    values: dict[str, object] = {
        "extracted_description": extracted_content.cleaned_text or None,
        "extraction_status": extraction_status,
        "extraction_error": extracted_content.error_message,
        "extracted_at": datetime.now(UTC),
    }
    if extracted_content.posted_at is not None:
        values["posted_at"] = extracted_content.posted_at

    return job_repository.update(job, values)


def _missing_extracted_description_reason(job: JobPosting) -> str:
    if job.extraction_status == JobExtractionStatus.FAILED:
        detail = _clean_optional_text(job.extraction_error)
        if detail is not None:
            return f"Skipped matching because job description extraction failed: {detail}"

        return "Skipped matching because job description extraction failed."
    if _clean_optional_text(job.job_url) is None:
        return "Skipped matching because no job URL is available for full description extraction."

    return "Skipped matching because no full extracted job description is available."


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()
    return cleaned_value or None


def _profile_skill_terms(profile: ProfileSnapshot) -> list[str]:
    terms: list[str] = []
    for skill in profile.skills:
        terms.append(skill.name)
        terms.extend(skill.tags)
    for experience in profile.experiences:
        terms.extend(experience.tech_stack)
    for project in profile.projects:
        terms.extend(project.tech_stack)

    return _dedupe(terms)


def _exact_skill_matches(target_skills: list[str], profile_terms: list[str]) -> list[str]:
    normalized_profile = {_normalize(term) for term in profile_terms}
    return [
        skill
        for skill in target_skills
        if _normalize(skill) in normalized_profile
    ]


def _fuzzy_skill_matches(
    target_skills: list[str],
    profile_terms: list[str],
    exact_matches: list[str],
) -> list[dict[str, object]]:
    exact_normalized = {_normalize(skill) for skill in exact_matches}
    candidates = [term for term in profile_terms if _normalize(term)]
    matches: list[dict[str, object]] = []

    for target_skill in target_skills:
        if _normalize(target_skill) in exact_normalized or not candidates:
            continue

        result = process.extractOne(
            target_skill,
            candidates,
            scorer=fuzz.token_set_ratio,
        )
        if result is None:
            continue

        profile_skill, score, _ = result
        if score >= FUZZY_MATCH_THRESHOLD:
            matches.append(
                {
                    "required_skill": target_skill,
                    "profile_skill": profile_skill,
                    "score": int(round(score)),
                }
            )

    return matches


def _missing_skills(
    target_skills: list[str],
    exact_matches: list[str],
    fuzzy_matches: list[dict[str, object]],
) -> list[str]:
    matched = {_normalize(skill) for skill in exact_matches}
    matched.update(_normalize(str(match["required_skill"])) for match in fuzzy_matches)
    return [skill for skill in target_skills if _normalize(skill) not in matched]


def _score_profile_relevance(
    extracted_description: str,
    requirements: dict[str, object],
    profile: ProfileSnapshot,
) -> RelevanceResult:
    profile_items = _profile_relevance_items(profile)
    if not profile_items:
        return RelevanceResult(component_score=0.0, experiences=[], projects=[])

    job_document = " ".join(
        [
            extracted_description,
            " ".join(_as_strings(requirements.get("responsibilities"))),
            " ".join(_as_strings(requirements.get("keywords"))),
        ]
    )
    documents = [job_document] + [item["text"] for item in profile_items]

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return RelevanceResult(component_score=0.0, experiences=[], projects=[])

    similarities = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    scored_items = [
        {**item, "score": float(similarities[index])}
        for index, item in enumerate(profile_items)
    ]
    scored_items.sort(key=lambda item: item["score"], reverse=True)

    top_experiences = _top_items(scored_items, "experience")
    top_projects = _top_items(scored_items, "project")
    top_score = max((item["score"] for item in scored_items), default=0.0)
    component_score = min(RELEVANCE_WEIGHT, top_score * RELEVANCE_WEIGHT)

    return RelevanceResult(
        component_score=component_score,
        experiences=top_experiences,
        projects=top_projects,
    )


def _profile_relevance_items(profile: ProfileSnapshot) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for experience in profile.experiences:
        items.append(
            {
                "id": str(experience.id),
                "kind": "experience",
                "label": f"{experience.role} at {experience.company}",
                "text": " ".join(
                    [experience.role, experience.company, *experience.tech_stack, *experience.bullets]
                ),
            }
        )
    for project in profile.projects:
        items.append(
            {
                "id": str(project.id),
                "kind": "project",
                "label": project.name,
                "text": " ".join(
                    [
                        project.name,
                        project.description or "",
                        *project.tech_stack,
                        *project.bullets,
                    ]
                ),
            }
        )

    return items


def _top_items(scored_items: list[dict[str, object]], kind: str) -> list[dict[str, object]]:
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "score": round(float(item["score"]), 4),
        }
        for item in scored_items
        if item["kind"] == kind and float(item["score"]) > 0
    ][:3]


def _score_title_location(job: JobPosting, profile: ProfileSnapshot) -> float:
    title_score = 0.0
    location_score = 0.0
    if profile.experiences:
        title_score = max(
            fuzz.token_set_ratio(job.title, experience.role) / 100
            for experience in profile.experiences
        )

        if job.location:
            location_score = max(
                fuzz.token_set_ratio(job.location, experience.location or "") / 100
                for experience in profile.experiences
            )

    return (title_score * 6) + (location_score * 4)


def _build_match_reason(
    *,
    exact_component: float,
    fuzzy_component: float,
    relevance_component: float,
    title_location_component: float,
    exact_matches: list[str],
    fuzzy_matches: list[dict[str, object]],
    missing_skills: list[str],
) -> str:
    return (
        f"Score components: exact skills {exact_component:.1f}/40, "
        f"fuzzy skills {fuzzy_component:.1f}/20, "
        f"experience/project relevance {relevance_component:.1f}/30, "
        f"title/location {title_location_component:.1f}/10. "
        f"Exact matches: {', '.join(exact_matches) or 'none'}. "
        f"Fuzzy matches: {len(fuzzy_matches)}. "
        f"Missing skills: {', '.join(missing_skills) or 'none'}."
    )


def _ratio_score(numerator: int, denominator: int, weight: int) -> float:
    if denominator == 0:
        return 0.0

    return min(weight, (numerator / denominator) * weight)


def _as_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = value.strip()
        normalized = _normalize(cleaned)
        if cleaned and normalized not in seen:
            seen.add(normalized)
            deduped.append(cleaned)

    return deduped


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())
