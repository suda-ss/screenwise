# Resume Screening Agent for Companies

Multi-tenant application for screening candidate CVs against a job description (JD) with evidence-backed requirement scores and a recruiter dashboard.

Each account belongs to exactly one isolated company workspace. That company can create multiple jobs/JDs and screen any number of candidates against the approved rubric for each job.

## Proposed outcome

1. A recruiter creates a job and supplies a JD.
2. The system extracts and normalizes the JD into a versioned knowledge base.
3. The recruiter reviews and locks up to five key requirements and their weights before candidates are scored.
4. CVs arrive through secure upload or an ATS connector.
5. Each CV is parsed, matched against the same locked rubric, and scored per requirement with supporting CV evidence.
6. The dashboard lists candidates and aggregate scores. Opening a candidate shows every requirement score, evidence, gaps, confidence, and audit history.
7. A recruiter makes the hiring decision; the system is decision support and never performs automatic rejection.

## Planning documents

- [Architecture](ARCHITECTURE.md)
- [Multi-agent plan](MULTI_AGENT_PLAN.md)

## Current implementation

- Company workspaces with membership-based tenant isolation
- Company account registration, password login, HttpOnly sessions, and logout
- Multiple jobs and JDs per company
- Suggested, recruiter-approved, versioned rubrics with up to five requirements
- PDF, DOCX, and text CV upload plus an idempotent generic ATS endpoint
- Evidence retrieval, provisional 0–5 requirement scores, confidence, gaps, and deterministic weighted averages
- Candidate dashboard and detailed evidence report
- Audit events for material workflow actions

The built-in scorer is intentionally a local, explainable baseline. The agent/provider adapter and production retrieval model are the next implementation layer; the API and data contracts are already separated for that change.

## Run locally

For the quickest local start using SQLite:

```bash
./local-start.sh
```

Open `http://127.0.0.1:3008`. API documentation is at `http://127.0.0.1:8020/docs`.

Stop both services cleanly with:

```bash
./local-stop.sh
```

The defaults can be changed with `RESUME_API_PORT` and `RESUME_WEB_PORT`. Runtime PID and log files are stored under `.run/`. The launcher refuses to overwrite an occupied port or install dependencies implicitly.

For the containerized PostgreSQL deployment:

```bash
cp .env.example .env
docker compose up --build
```

Open the frontend at `http://localhost:3008` and the API documentation at `http://localhost:8000/docs`.

For backend-only development without Docker, `DATABASE_URL` defaults to SQLite:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Registration creates a company owner account and its first isolated workspace. Authentication uses PBKDF2 password hashes and opaque HttpOnly session cookies. Set `AUTH_COOKIE_SECURE=true` behind HTTPS in production.

## Verify

```bash
.venv/bin/python -m pytest -q
cd frontend && npm run build
```

## Remaining product decisions

1. Select the first named ATS connector after the generic webhook/API.
2. Select the production model and embedding provider.
3. Define company-specific retention periods and deployment jurisdictions.
