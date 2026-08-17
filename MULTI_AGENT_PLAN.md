# Multi-Agent Plan

## Orchestration principle

A deterministic workflow orchestrator owns state transitions, retries, and permissions. Specialized agents operate on narrow schemas and cannot independently change a rubric, reject a candidate, or write final hiring decisions. All agents use the same locked rubric version for a screening run.

## Runtime agents

### 1. JD Analyst Agent

Input: normalized JD text and its source locations.

Responsibilities:

- identify atomic job requirements;
- classify each as required, preferred, responsibility, certification, experience, or skill;
- propose measurable evaluation guidance and up to five key requirements;
- cite the JD passage supporting every extracted requirement;
- flag vague, discriminatory, contradictory, or non-job-related language for human review.

Output: a draft requirement schema. It cannot approve or publish the rubric.

### 2. Rubric Builder Agent

Input: extracted requirements plus recruiter edits.

Responsibilities:

- convert approved requirements into anchored 0–5 scoring criteria;
- propose weights that total 100%;
- define acceptable evidence and explicit non-evidence;
- detect overlapping requirements that could double-count the same qualification.

Output: a draft rubric version requiring recruiter approval and locking.

### 3. CV Parsing Agent

Input: safely extracted CV text with page and section markers.

Responsibilities:

- produce a structured, job-relevant candidate profile;
- normalize dates, skills, employers, education, certifications, and project claims;
- retain source references for each extracted claim;
- flag unreadable, contradictory, or incomplete content;
- exclude protected and sensitive attributes from downstream scoring context.

Output: structured profile plus evidence chunks. It never scores candidates.

### 4. Evidence Retrieval Agent

Input: locked rubric, structured profile, and indexed CV text.

Responsibilities:

- retrieve the best evidence for each requirement using hybrid lexical/vector search;
- separate direct, related, ambiguous, and absent evidence;
- return citations to CV page/section offsets;
- avoid using evidence for one requirement when it does not substantively apply.

Output: an evidence packet per requirement. It never assigns the final score.

### 5. Requirement Scoring Agent

Input: one locked requirement, its score anchors, and its evidence packet.

Responsibilities:

- assign a 0–5 score using only cited job-related evidence;
- provide a concise rationale, confidence, and identified gaps;
- distinguish lack of evidence from negative evidence;
- emit schema-valid structured output.

Output: a provisional per-requirement score. Each requirement can be processed independently for scalability.

### 6. Validation Agent

Input: provisional scores, CV text, evidence packets, and locked rubric.

Responsibilities:

- verify citations exist and support each claim;
- check scoring-anchor consistency and detect unsupported assumptions;
- detect double counting, inconsistent treatment, prompt injection, and low-confidence cases;
- send invalid or uncertain results to human review or a bounded rescore.

Output: validated scores or explicit review flags. It cannot invent replacement evidence.

### 7. Screening Report Agent

Input: validated requirement scores and deterministic aggregate calculation.

Responsibilities:

- produce the recruiter-facing summary;
- surface strongest evidence, gaps, and review flags;
- explain the aggregate without adding new claims;
- create dashboard-ready structured data.

Output: a screening report. The numeric average is calculated in application code, not by the model.

## Workflow

```text
Job setup:
JD Analyst -> Rubric Builder -> Recruiter approval -> Locked rubric + RAG index

Application screening:
CV Parsing -> Evidence Retrieval
           -> Requirement Scoring (one task per requirement)
           -> Validation
           -> deterministic weighted average
           -> Screening Report
           -> Recruiter review
```

## Agent contracts and controls

- JSON schemas validate every handoff.
- Agents receive only the minimum data needed for their task.
- CV text is treated as untrusted data; instructions embedded inside documents are never executed.
- Each output records agent, model, prompt, rubric, and source-document versions.
- Retries are bounded. Persistent disagreement or low confidence becomes `needs_review`.
- Temperature is low for extraction/scoring; deterministic application code handles aggregation and state.
- Evaluation fixtures cover adversarial CV text, missing evidence, alternative formatting, equivalent experience, and protected data.

## Implementation workstreams after approval

1. Platform and data: project scaffold, schema, tenant isolation, auth, object storage, and job queue.
2. JD/RAG: ingestion, chunking, embeddings, requirement extraction, rubric review, and versioning.
3. CV pipeline: upload/webhook intake, validation, extraction, deduplication, and structured parsing.
4. Screening: hybrid retrieval, scoring schemas, validators, deterministic aggregation, and evaluation fixtures.
5. Product UI: job setup, rubric approval, candidate dashboard, candidate detail, review and overrides.
6. ATS and operations: generic integration API, first connector, observability, privacy controls, deployment, and security testing.

## Approval gate

Implementation should begin only after the product owner approves the architecture, scoring scale, rubric-locking workflow, tenant scope, and initial ATS strategy described in these planning documents.
