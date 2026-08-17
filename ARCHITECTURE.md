# Architecture Proposal

## Approved tenancy model

The platform is multi-tenant. An organization represents one company and owns its users, memberships, jobs, JDs, rubrics, candidates, applications, documents, scores, integrations, and audit events. Each company can create multiple jobs and screen candidates independently against the locked rubric for the selected job. Tenant context is derived from authenticated membership and enforced in every query; it is never trusted from an unverified client claim.

## Product boundaries

The system evaluates job-related evidence in a CV against a recruiter-approved rubric derived from a JD. It does not make final employment decisions, infer sensitive or protected attributes, rank candidates using demographic proxies, or automatically reject candidates. Recruiters can inspect and override every score, with the reason recorded.

## High-level flow

```text
JD upload/paste
    -> JD parsing and requirement extraction
    -> recruiter reviews top requirements and weights
    -> immutable rubric version + RAG index

CV upload / ATS webhook
    -> malware/type validation + encrypted document storage
    -> text extraction and structured candidate profile
    -> evidence retrieval against locked JD rubric
    -> requirement scoring and validation
    -> aggregate score + explanation
    -> dashboard and candidate detail view
```

## Proposed stack

| Area | Choice | Responsibility |
|---|---|---|
| Web UI | Next.js + TypeScript | Jobs, rubric review, candidate dashboard, score details |
| API | FastAPI + Python | Authentication, jobs, candidates, uploads, scoring APIs, ATS webhooks |
| Workflow | Background worker with Redis queue | Durable document processing and scoring jobs |
| Relational data | PostgreSQL | Tenants, users, jobs, rubric versions, candidates, scores, audits |
| Retrieval | pgvector | JD chunks, requirement embeddings, and CV evidence embeddings |
| Documents | S3-compatible object storage | Encrypted original CVs and extracted artifacts |
| Models | Provider abstraction | Structured extraction, retrieval assistance, and rubric scoring |
| Deployment | Docker Compose initially | Reproducible local and server deployment, consistent with nearby projects |

The model provider and ATS connector remain adapters so either can be replaced without changing core scoring data.

## Core components

### JD knowledge and rubric service

- Accepts pasted text, PDF, or DOCX.
- Extracts responsibilities, required skills, qualifications, experience, certifications, and preferred criteria.
- Stores source chunks with page/section references and embeddings.
- Proposes up to five key requirements, but requires recruiter confirmation.
- Versions the JD and rubric. Existing candidate scores always retain the rubric version used.
- Prevents candidate-specific changes to requirements or weights.

### CV ingestion service

- Supports batch upload and an authenticated, idempotent ATS webhook/API.
- Validates file extension, MIME type, size, malware scan result, and duplicate hash.
- Stores the original privately and sends extraction/scoring work to the queue.
- Tracks states: `received`, `extracting`, `ready`, `scoring`, `completed`, `needs_review`, and `failed`.

### Parsing and evidence service

- Converts PDF/DOCX CVs to normalized text while retaining page/section references.
- Extracts only job-relevant claims such as employment, projects, skills, education, and certifications.
- Retrieves evidence independently for each rubric requirement.
- Treats missing evidence as unknown or unsupported, not automatically false.
- Ignores photos and removes protected or sensitive fields from model scoring context where practical.

### Scoring service

Each locked requirement is scored on a fixed 0–5 scale:

| Score | Meaning |
|---:|---|
| 0 | No relevant evidence found |
| 1 | Minimal or weakly related evidence |
| 2 | Partial evidence; important gaps remain |
| 3 | Meets the requirement |
| 4 | Strong evidence exceeding the baseline |
| 5 | Exceptional, directly supported evidence |

Every requirement result contains:

- score and confidence;
- short rationale;
- exact CV evidence references;
- missing or ambiguous evidence;
- model/rubric/prompt version;
- validation flags.

The default aggregate is the weighted mean across the approved requirements:

```text
aggregate_score = sum(requirement_score * weight) / sum(weight)
percentage = aggregate_score / 5 * 100
```

If all requirements have equal weight, this is the ordinary average. Scores with extraction failures, insufficient evidence, or low confidence are marked `needs_review` rather than silently finalized.

### Dashboard

The job dashboard shows candidate name, processing state, aggregate score, completion time, and review flags. Filters include score range, status, and requirement-level thresholds. It must not use protected-attribute filters.

The candidate detail view shows:

- aggregate score and the rubric version;
- all requirement scores and weights;
- cited evidence and gaps for each score;
- original CV access subject to permission;
- processing history, recruiter notes, overrides, and override reasons.

## Suggested data model

- `organizations`, `users`, `memberships`, `roles`
- `jobs`, `job_documents`, `job_chunks`
- `rubric_versions`, `requirements`, `requirement_weights`
- `candidates`, `applications`, `cv_documents`, `cv_chunks`
- `processing_runs`, `requirement_scores`, `aggregate_scores`
- `ats_connections`, `webhook_events`
- `review_actions`, `score_overrides`, `audit_events`

All tenant-owned rows carry `organization_id`; APIs enforce tenant scoping. Documents are referenced by storage keys rather than public URLs.

## API outline

- `POST /jobs` and `POST /jobs/{id}/jd`
- `POST /jobs/{id}/rubrics/generate`
- `POST /jobs/{id}/rubrics/{version}/approve`
- `POST /jobs/{id}/candidates/upload`
- `POST /integrations/ats/{provider}/webhook`
- `GET /jobs/{id}/candidates`
- `GET /applications/{id}`
- `POST /applications/{id}/rescore`
- `POST /requirement-scores/{id}/override`
- `GET /processing-runs/{id}`

## Security, privacy, and hiring safeguards

- Encrypt traffic, database storage, and CV objects; use short-lived signed download URLs.
- Apply role-based access and tenant isolation to every candidate and job operation.
- Never place CVs or JDs in logs; redact model-provider telemetry where supported.
- Define retention and deletion policies, including ATS-originated deletion requests.
- Record consent/legal basis and model-processing region as required by deployment jurisdiction.
- Exclude names, photos, addresses, age/date of birth, gender, nationality, disability, and other protected information from scoring context when feasible.
- Do not use school prestige, employment gaps, names, or location as proxy scores unless a lawful, job-related requirement is explicitly approved.
- Require meaningful human review; no automatic rejection or hiring decision.
- Run bias, consistency, hallucination, and adverse-impact evaluations before production use and periodically afterward.
- Preserve immutable evidence, rubric, prompt, and model versions for auditability.

## Reliability and evaluation

- Idempotency keys prevent duplicate ATS applications and repeated scores.
- Durable workflow retries isolate extraction, embedding, and model failures.
- Structured model outputs are schema-validated; a validation stage checks that cited evidence exists in the CV.
- A frozen evaluation set measures extraction accuracy, evidence citation precision/recall, score agreement with trained reviewers, consistency across equivalent CV formats, latency, and cost.
- Production monitoring tracks queue health, failure rates, low-confidence rates, score drift, and reviewer override rates without exposing CV contents.

## Delivery phases

1. Foundation: tenants, authentication, job/JD ingestion, approved rubric, manual CV upload.
2. Screening: parsing, retrieval, evidence-backed scoring, validation, and background processing.
3. Experience: candidate dashboard, detail view, overrides, audit trail, and batch operations.
4. Integration: generic ATS webhook/API and one approved ATS connector.
5. Hardening: security review, evaluation suite, bias testing, retention controls, observability, and deployment automation.
