from pydantic import BaseModel, ConfigDict, Field


class JobRequirements(BaseModel):
    role_title: str = Field(description="Role title found in the job text.")
    seniority: str = Field(description="Seniority level inferred from the job text.")
    required_skills: list[str] = Field(description="Skills explicitly required by the job.")
    preferred_skills: list[str] = Field(description="Skills explicitly preferred by the job.")
    responsibilities: list[str] = Field(description="Core responsibilities from the job.")
    keywords: list[str] = Field(description="Relevant search and matching keywords.")
    location_constraints: list[str] = Field(
        description="Location, remote, visa, timezone, or relocation constraints.",
    )
    summary: str = Field(description="Concise summary of the job requirements.")

    model_config = ConfigDict(extra="forbid")


class TailoredLatexResume(BaseModel):
    tailored_latex: str = Field(description="Tailored LaTeX resume content.")
    selected_experiences: list[str] = Field(
        description="Experience identifiers or titles selected from the profile.",
    )
    selected_projects: list[str] = Field(
        description="Project identifiers or names selected from the profile.",
    )
    selected_skills: list[str] = Field(
        description="Skills selected from the verified profile data.",
    )
    change_summary: list[str] = Field(
        description="Human-readable summary of edits made to the template.",
    )
    safety_warnings: list[str] = Field(
        description="Missing skills, unverifiable claims, or other safety issues.",
    )

    model_config = ConfigDict(extra="forbid")
