from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?$"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=1, max_length=100, pattern=SLUG_PATTERN)

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        import re
        return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()))


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=320)
    password: str = Field(min_length=8, max_length=200)
    company_name: str = Field(min_length=2, max_length=200)
    company_slug: str = Field(min_length=1, max_length=100, pattern=SLUG_PATTERN)

    @field_validator("company_slug", mode="before")
    @classmethod
    def normalize_company_slug(cls, value: str) -> str:
        import re
        return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()))


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class UserOut(ORMModel):
    id: str
    email: str
    display_name: str


class OrganizationOut(ORMModel):
    id: str
    name: str
    slug: str
    created_at: datetime


class AuthOut(BaseModel):
    user: UserOut
    organizations: list[OrganizationOut]


class RequirementInput(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=2)
    weight: float = Field(gt=0, le=100)
    keywords: list[str] = Field(default_factory=list)


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    location: str = Field(default="", max_length=240)
    jd_text: str = Field(min_length=30)


class JobOut(ORMModel):
    id: str
    organization_id: str
    title: str
    location: str
    active: bool
    created_at: datetime


class RubricCreate(BaseModel):
    requirements: list[RequirementInput] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def weights_total_100(self):
        if abs(sum(item.weight for item in self.requirements) - 100) > 0.01:
            raise ValueError("requirement weights must total 100")
        return self


class RequirementOut(ORMModel):
    id: str
    position: int
    title: str
    description: str
    weight: float
    keywords: list[str]
    anchors: dict


class RubricOut(ORMModel):
    id: str
    job_id: str
    version: int
    approved: bool
    approved_at: datetime | None
    requirements: list[RequirementOut]


class CandidateOut(ORMModel):
    id: str
    full_name: str
    email: str


class ScoreOut(ORMModel):
    id: str
    score: float
    confidence: float
    rationale: str
    evidence: list
    gaps: list
    needs_review: bool
    requirement: RequirementOut


class ApplicationListOut(ORMModel):
    id: str
    status: str
    aggregate_score: float | None
    score_percentage: float | None
    review_reason: str
    created_at: datetime
    completed_at: datetime | None
    candidate: CandidateOut


class ApplicationDetailOut(ApplicationListOut):
    job: JobOut
    rubric: RubricOut
    scores: list[ScoreOut]


class ATSApplication(BaseModel):
    external_id: str = Field(min_length=1, max_length=240)
    candidate_name: str = Field(min_length=1, max_length=240)
    candidate_email: str = Field(default="", max_length=320)
    cv_text: str = Field(min_length=30)
