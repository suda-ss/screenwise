from __future__ import annotations

import hashlib
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, selectinload

from .auth import (
    Principal, create_session, delete_session, get_current_user, get_principal,
    hash_password, require_editor, verify_password,
)
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .document_parser import extract_text, validate_filename
from .models import (
    Application, ApplicationStatus, AuditEvent, Candidate, Job, Membership, Organization,
    Requirement, RequirementScore, Role, RubricVersion, User, now,
)
from .schemas import (
    ATSApplication, ApplicationDetailOut, ApplicationListOut, AuthOut, JobCreate, JobOut,
    LoginInput, OrganizationCreate, OrganizationOut, RegisterInput, RubricCreate, RubricOut,
)
from .scoring import default_anchors, score_requirement, suggest_requirements


def initialize_database() -> None:
    Base.metadata.create_all(engine)
    # Lightweight compatibility migration for pre-auth local databases.
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "password_hash" not in user_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(500) DEFAULT ''"))
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Resume Screening Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def audit(db: Session, organization_id: str, action: str, entity_type: str, entity_id: str, actor_id: str | None = None, **details) -> None:
    db.add(AuditEvent(
        organization_id=organization_id, actor_user_id=actor_id, action=action,
        entity_type=entity_type, entity_id=entity_id, details=details,
    ))


def owned_job(db: Session, organization_id: str, job_id: str) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.organization_id == organization_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def approved_rubric(db: Session, job_id: str) -> RubricVersion:
    rubric = db.scalar(
        select(RubricVersion)
        .options(selectinload(RubricVersion.requirements))
        .where(RubricVersion.job_id == job_id, RubricVersion.approved.is_(True))
        .order_by(RubricVersion.version.desc())
    )
    if not rubric:
        raise HTTPException(status_code=409, detail="Approve a rubric before adding candidates")
    return rubric


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def auth_payload(db: Session, user: User) -> dict:
    organizations = db.scalars(
        select(Organization).join(Membership).where(Membership.user_id == user.id).order_by(Organization.name)
    ).all()
    return {"user": user, "organizations": organizations}


def set_session_cookie(response: Response, token: str, expires: datetime) -> None:
    response.set_cookie(
        settings.session_cookie, token, httponly=True, secure=settings.cookie_secure,
        samesite="lax", path="/", expires=expires,
    )


@app.post("/auth/register", response_model=AuthOut, status_code=201)
def register(payload: RegisterInput, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    if db.scalar(select(Organization).where(Organization.slug == payload.company_slug)):
        raise HTTPException(status_code=409, detail="Company URL is already in use")
    user = User(
        email=email, display_name=payload.name.strip(), password_hash=hash_password(payload.password)
    )
    organization = Organization(name=payload.company_name.strip(), slug=payload.company_slug)
    db.add_all([user, organization])
    db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, role=Role.owner))
    audit(db, organization.id, "organization.registered", "organization", organization.id, user.id)
    token, expires = create_session(db, user.id)
    db.commit()
    set_session_cookie(response, token, expires)
    return auth_payload(db, user)


@app.post("/auth/login", response_model=AuthOut)
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token, expires = create_session(db, user.id)
    db.commit()
    set_session_cookie(response, token, expires)
    return auth_payload(db, user)


@app.get("/auth/me", response_model=AuthOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_payload(db, user)


@app.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie),
    db: Session = Depends(get_db),
):
    delete_session(db, session_token)
    db.commit()
    response.delete_cookie(settings.session_cookie, path="/")


@app.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Organization).join(Membership).where(Membership.user_id == user.id).order_by(Organization.name)
    ).all()


@app.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    if existing_membership:
        raise HTTPException(
            status_code=409,
            detail="This account already belongs to a company. Each account can have one company workspace.",
        )
    if db.scalar(select(Organization).where(Organization.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Organization slug already exists")
    organization = Organization(name=payload.name, slug=payload.slug)
    db.add(organization)
    db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, role=Role.owner))
    audit(db, organization.id, "organization.created", "organization", organization.id, user.id)
    db.commit()
    db.refresh(organization)
    return organization


@app.get("/organizations/{organization_id}/jobs", response_model=list[JobOut])
def list_jobs(
    organization_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Job).where(Job.organization_id == organization_id).order_by(Job.created_at.desc())
    ).all()


@app.post("/organizations/{organization_id}/jobs", response_model=JobOut, status_code=201)
def create_job(
    organization_id: str,
    payload: JobCreate,
    principal: Principal = Depends(require_editor),
    db: Session = Depends(get_db),
):
    job = Job(organization_id=organization_id, **payload.model_dump())
    db.add(job)
    db.flush()
    audit(db, organization_id, "job.created", "job", job.id, principal.user.id)
    db.commit()
    db.refresh(job)
    return job


@app.get("/organizations/{organization_id}/jobs/{job_id}", response_model=JobOut)
def get_job(
    organization_id: str, job_id: str,
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db),
):
    return owned_job(db, organization_id, job_id)


@app.post("/organizations/{organization_id}/jobs/{job_id}/rubrics/suggest")
def suggest_rubric(
    organization_id: str, job_id: str,
    principal: Principal = Depends(require_editor), db: Session = Depends(get_db),
):
    job = owned_job(db, organization_id, job_id)
    return {"requirements": suggest_requirements(job.jd_text)}


@app.post("/organizations/{organization_id}/jobs/{job_id}/rubrics", response_model=RubricOut, status_code=201)
def create_rubric(
    organization_id: str, job_id: str, payload: RubricCreate,
    principal: Principal = Depends(require_editor), db: Session = Depends(get_db),
):
    owned_job(db, organization_id, job_id)
    version = (db.scalar(select(func.max(RubricVersion.version)).where(RubricVersion.job_id == job_id)) or 0) + 1
    rubric = RubricVersion(job_id=job_id, version=version)
    db.add(rubric)
    db.flush()
    for position, item in enumerate(payload.requirements, start=1):
        db.add(Requirement(
            rubric_id=rubric.id, position=position, anchors=default_anchors(), **item.model_dump()
        ))
    audit(db, organization_id, "rubric.created", "rubric", rubric.id, principal.user.id, version=version)
    db.commit()
    return db.scalar(
        select(RubricVersion).options(selectinload(RubricVersion.requirements)).where(RubricVersion.id == rubric.id)
    )


@app.get("/organizations/{organization_id}/jobs/{job_id}/rubrics", response_model=list[RubricOut])
def list_rubrics(
    organization_id: str, job_id: str,
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db),
):
    owned_job(db, organization_id, job_id)
    return db.scalars(
        select(RubricVersion).options(selectinload(RubricVersion.requirements))
        .where(RubricVersion.job_id == job_id).order_by(RubricVersion.version.desc())
    ).all()


@app.post("/organizations/{organization_id}/jobs/{job_id}/rubrics/{rubric_id}/approve", response_model=RubricOut)
def approve_rubric(
    organization_id: str, job_id: str, rubric_id: str,
    principal: Principal = Depends(require_editor), db: Session = Depends(get_db),
):
    owned_job(db, organization_id, job_id)
    rubric = db.scalar(
        select(RubricVersion).options(selectinload(RubricVersion.requirements))
        .where(RubricVersion.id == rubric_id, RubricVersion.job_id == job_id)
    )
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    if not 1 <= len(rubric.requirements) <= 5:
        raise HTTPException(status_code=422, detail="A rubric must contain one to five requirements")
    rubric.approved = True
    rubric.approved_at = now()
    audit(db, organization_id, "rubric.approved", "rubric", rubric.id, principal.user.id)
    db.commit()
    return rubric


def persist_and_queue_application(
    db: Session, organization_id: str, job: Job, rubric: RubricVersion,
    name: str, email: str, storage_key: str, cv_text: str, source: str, source_ref: str,
) -> Application:
    candidate = Candidate(organization_id=organization_id, full_name=name, email=email)
    db.add(candidate)
    db.flush()
    application = Application(
        organization_id=organization_id, job_id=job.id, candidate_id=candidate.id,
        rubric_id=rubric.id, cv_storage_key=storage_key, cv_text=cv_text,
        source=source, source_ref=source_ref,
    )
    db.add(application)
    db.flush()
    audit(db, organization_id, "application.received", "application", application.id, source=source)
    db.commit()
    return application


def run_screening(application_id: str) -> None:
    with SessionLocal() as db:
        application = db.scalar(
            select(Application)
            .options(selectinload(Application.rubric).selectinload(RubricVersion.requirements))
            .where(Application.id == application_id)
        )
        if not application:
            return
        try:
            application.status = ApplicationStatus.scoring
            db.commit()
            db.query(RequirementScore).filter(RequirementScore.application_id == application.id).delete()
            weighted_total = 0.0
            total_weight = 0.0
            review_reasons = []
            for requirement in application.rubric.requirements:
                result = score_requirement(requirement, application.cv_text)
                db.add(RequirementScore(
                    application_id=application.id, requirement_id=requirement.id,
                    score=result.score, confidence=result.confidence, rationale=result.rationale,
                    evidence=result.evidence, gaps=result.gaps, needs_review=result.needs_review,
                ))
                weighted_total += result.score * requirement.weight
                total_weight += requirement.weight
                if result.needs_review:
                    review_reasons.append(requirement.title)
            application.aggregate_score = round(weighted_total / total_weight, 2) if total_weight else 0
            application.score_percentage = round(application.aggregate_score / 5 * 100, 1)
            application.completed_at = datetime.now(timezone.utc)
            if review_reasons:
                application.status = ApplicationStatus.needs_review
                application.review_reason = "Low-confidence or missing evidence: " + ", ".join(review_reasons)
            else:
                application.status = ApplicationStatus.completed
                application.review_reason = ""
            audit(db, application.organization_id, "application.scored", "application", application.id,
                  aggregate_score=application.aggregate_score, rubric_id=application.rubric_id)
            db.commit()
        except Exception as exc:
            db.rollback()
            application = db.get(Application, application_id)
            if application:
                application.status = ApplicationStatus.failed
                application.review_reason = f"Screening failed: {type(exc).__name__}"
                db.commit()


@app.post("/organizations/{organization_id}/jobs/{job_id}/candidates/upload", response_model=ApplicationListOut, status_code=202)
async def upload_candidate(
    organization_id: str, job_id: str, background_tasks: BackgroundTasks,
    candidate_name: str = Form(...), candidate_email: str = Form(default=""),
    cv: UploadFile = File(...), principal: Principal = Depends(require_editor),
    db: Session = Depends(get_db),
):
    job = owned_job(db, organization_id, job_id)
    rubric = approved_rubric(db, job_id)
    filename = cv.filename or "cv"
    try:
        extension = validate_filename(filename)
        data = await cv.read()
        cv_text = extract_text(data, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    digest = hashlib.sha256(data).hexdigest()
    safe_key = f"{organization_id}/{job_id}/{digest}{extension}"
    destination = Path(settings.upload_dir) / safe_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(data)
    application = persist_and_queue_application(
        db, organization_id, job, rubric, candidate_name, candidate_email,
        safe_key, cv_text, "upload", digest,
    )
    background_tasks.add_task(run_screening, application.id)
    return db.scalar(
        select(Application).options(selectinload(Application.candidate)).where(Application.id == application.id)
    )


@app.post("/organizations/{organization_id}/jobs/{job_id}/ats/webhook", response_model=ApplicationListOut, status_code=202)
def ats_webhook(
    organization_id: str, job_id: str, payload: ATSApplication, background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_editor), db: Session = Depends(get_db),
):
    job = owned_job(db, organization_id, job_id)
    existing = db.scalar(select(Application).where(
        Application.organization_id == organization_id,
        Application.source == "ats", Application.source_ref == payload.external_id,
    ))
    if existing:
        return db.scalar(select(Application).options(selectinload(Application.candidate)).where(Application.id == existing.id))
    rubric = approved_rubric(db, job_id)
    application = persist_and_queue_application(
        db, organization_id, job, rubric, payload.candidate_name, payload.candidate_email,
        "", payload.cv_text, "ats", payload.external_id,
    )
    background_tasks.add_task(run_screening, application.id)
    return db.scalar(select(Application).options(selectinload(Application.candidate)).where(Application.id == application.id))


@app.get("/organizations/{organization_id}/jobs/{job_id}/candidates", response_model=list[ApplicationListOut])
def list_candidates(
    organization_id: str, job_id: str,
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db),
):
    owned_job(db, organization_id, job_id)
    return db.scalars(
        select(Application).options(selectinload(Application.candidate))
        .where(Application.organization_id == organization_id, Application.job_id == job_id)
        .order_by(Application.score_percentage.desc().nullslast(), Application.created_at.desc())
    ).all()


@app.get("/organizations/{organization_id}/applications/{application_id}", response_model=ApplicationDetailOut)
def application_detail(
    organization_id: str, application_id: str,
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db),
):
    application = db.scalar(
        select(Application).options(
            selectinload(Application.candidate), selectinload(Application.job),
            selectinload(Application.rubric).selectinload(RubricVersion.requirements),
            selectinload(Application.scores).selectinload(RequirementScore.requirement),
        ).where(Application.id == application_id, Application.organization_id == organization_id)
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    application.scores.sort(key=lambda score: score.requirement.position)
    return application


@app.post("/organizations/{organization_id}/applications/{application_id}/rescore", response_model=ApplicationListOut, status_code=202)
def rescore_application(
    organization_id: str, application_id: str, background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_editor), db: Session = Depends(get_db),
):
    application = db.scalar(
        select(Application).options(selectinload(Application.candidate))
        .where(Application.id == application_id, Application.organization_id == organization_id)
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    application.status = ApplicationStatus.received
    application.review_reason = ""
    audit(db, organization_id, "application.rescore_requested", "application", application.id, principal.user.id)
    db.commit()
    background_tasks.add_task(run_screening, application.id)
    return application
