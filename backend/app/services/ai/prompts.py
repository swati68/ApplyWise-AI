import json
from typing import Any


JOB_REQUIREMENTS_SYSTEM_PROMPT = """
You extract structured job requirements from a user-provided job posting.
Return valid JSON only.
Do not infer requirements that are not supported by the job text.
Keep entries concise and factual.
""".strip()


RESUME_TAILORING_SYSTEM_PROMPT = """
You tailor a LaTeX resume using only verified profile facts provided by the user.
Return valid JSON only.

Hard rules:
- Use only facts from profile_json.
- Do not invent companies, tools, skills, metrics, dates, or claims.
- Do not add fake keywords just because job_json contains them.
- Do not write new resume bullet points.
- Any LaTeX \\item bullet you add or replace must be copied exactly from profile_json.experiences[].bullets or profile_json.projects[].bullets.
- Do not paraphrase, combine, embellish, or quantify profile bullets.
- If no verified profile bullet fits a resume section, leave that section's original latex_template bullet text unchanged.
- If a required skill is missing from user profile, list it in safety_warnings.
- Preserve LaTeX validity as much as possible.
- Keep selected_experiences, selected_projects, and selected_skills anchored to profile_json.
""".strip()


def build_job_requirements_prompt(job_text: str) -> str:
    return f"""
Extract requirements from this job posting.

Job posting:
{job_text.strip()}
""".strip()


def build_resume_tailoring_prompt(
    *,
    profile_json: Any,
    job_json: Any,
    latex_template: str,
) -> str:
    return f"""
Tailor the LaTeX resume template for the job using only verified profile facts.

profile_json:
{_to_pretty_json(profile_json)}

job_json:
{_to_pretty_json(job_json)}

latex_template:
{latex_template}
""".strip()


def _to_pretty_json(value: Any) -> str:
    if isinstance(value, str):
        return value

    return json.dumps(value, indent=2, sort_keys=True)
