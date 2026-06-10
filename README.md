# ApplyWise AI

ApplyWise AI is an AI-assisted job intelligence and resume tailoring platform. It helps users manage verified career profile data, analyze job postings, generate tailored LaTeX resumes, compile PDFs, upload them to Google Drive, and send email digests for matched jobs.

## Why This Project Matters

ApplyWise AI is built around a practical job-search workflow: ingest job postings from manual URLs and GitHub job repositories, extract full job descriptions, match jobs against verified user profile data, generate tailored LaTeX resumes, upload PDFs to Google Drive, send email digests, and support scheduled automation. The system is intentionally strict: resume generation should only use facts the user has provided in their profile or existing template, not invented experience, skills, companies, metrics, or projects.

## Features

- Google-only login with session-protected workspace pages.
- Resume intelligence profile for education, experience, projects, and skills.
- Manual job URL flow with job description extraction.
- GitHub markdown job source configuration with role filters and tags.
- Hybrid job matching using extracted job descriptions, deterministic skill matching, RapidFuzz, and TF-IDF similarity.
- LaTeX resume template management.
- Tailored LaTeX resume generation with safety warnings.
- PDF compilation with `tectonic` or `pdflatex`.
- Google Drive upload for generated PDFs.
- Gmail or SMTP email digests.
- APScheduler-based automation for enabled GitHub sources.
- Job summary tracking with statuses, match details, generated resumes, and source tags.

## Tech Stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui-style components, lucide-react.
- Backend: FastAPI, Python, SQLAlchemy 2 style, Alembic.
- Database: PostgreSQL.
- AI: OpenAI Python SDK, with local mock fallback when no API key is configured.
- Parsing: httpx, BeautifulSoup, readability-lxml.
- Matching: scikit-learn TF-IDF cosine similarity, RapidFuzz.
- Scheduler: APScheduler.
- Documents: LaTeX, Jinja2-ready architecture, PDF compiler.
- Integrations: Google OAuth, Google Drive API, Gmail API, SMTP fallback.

## Architecture Overview

```text
applywise-ai/
  frontend/          Next.js UI, auth flow, dashboard, jobs, profile, resumes, settings
  backend/           FastAPI app, SQLAlchemy models, repositories, services, routes
  docker-compose.yml PostgreSQL for local development
  .env.example       Safe environment variable template
```

The backend follows a simple layered structure:

- `app/api/routes/`: HTTP endpoints.
- `app/models/`: SQLAlchemy models.
- `app/repositories/`: database access.
- `app/services/`: business logic and integrations.
- `app/schemas/`: Pydantic request/response schemas.
- `alembic/versions/`: database migrations.

The scheduler reuses the existing GitHub pipeline service. It does not duplicate scan, match, resume generation, PDF, Drive, or email logic.

## Ethical Use

ApplyWise AI does not implement unauthorized LinkedIn scraping, company-site crawling, or auto-apply spam. LinkedIn jobs should be handled through manually pasted URLs or job descriptions. Automation is limited to user-configured sources and user-authorized Google integrations.

## Prerequisites

- Node.js 20+
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL, provided locally through Docker Compose
- Optional but needed for PDF compilation:
  - Preferred: `tectonic`
  - Fallback: `pdflatex` from MacTeX, BasicTeX, or TeX Live

## Environment Setup

Copy the example file:

```bash
cp .env.example .env
```

Fill in only local values in `.env`. Never commit `.env`.

Important variables:

```bash
DATABASE_URL=
AUTH_SECRET_KEY=
OPENAI_API_KEY=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
GOOGLE_INTEGRATION_REDIRECT_URI=http://localhost:8000/api/integrations/google/callback
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SCHEDULER_ENABLED=false
```

For local PostgreSQL, a typical database URL is:

```bash
DATABASE_URL=postgresql+psycopg://applywise:applywise@localhost:5432/applywise
```

Use a long random value for `AUTH_SECRET_KEY`.

## Database

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Check database status:

```bash
docker compose ps
```

Stop PostgreSQL:

```bash
docker compose stop
```

## Backend Setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The backend runs at:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok","service":"applywise-ai-backend"}
```

## Frontend Setup

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:3000
```

If needed, set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

in `frontend/.env.local`. Do not commit `frontend/.env.local`.

## Docker

Docker Compose currently provides PostgreSQL for local development:

```bash
docker compose up -d postgres
```

The frontend and backend are run locally with `npm run dev` and `uvicorn`. Full app containerization can be added later.

## Database Migrations

Run migrations from `backend/`:

```bash
alembic upgrade head
```

Create a migration after model changes:

```bash
alembic revision --autogenerate -m "describe change"
```

## Google OAuth Setup

In Google Cloud Console:

1. Create or select a Google Cloud project.
2. Configure the OAuth consent screen.
3. If the app is in Testing mode, add your Google account as a test user.
4. Create an OAuth client ID for a Web application.
5. Add authorized JavaScript origin:
   - `http://localhost:3000`
6. Add authorized redirect URIs:
   - `http://localhost:8000/api/auth/google/callback`
   - `http://localhost:8000/api/integrations/google/callback`
7. Enable the Google Drive API and Gmail API.
8. Add these OAuth scopes when requested:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/gmail.send`

The app does not request broad Drive access or Gmail read access.

## OpenAI Setup

Create an OpenAI API key and set:

```bash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

If `OPENAI_API_KEY` is empty, the backend uses a mock AI provider so local development can continue.

## Scheduler Setup

Scheduler automation is disabled by default:

```bash
SCHEDULER_ENABLED=false
```

Set it to `true` and restart the backend to enable background scheduled runs:

```bash
SCHEDULER_ENABLED=true
```

Users must connect Google Drive and Gmail permissions before enabling automation in Settings. Each GitHub source can be enabled or disabled, and the scheduler only runs enabled sources.

## Setup Verification Checklist

- Backend health:
  ```bash
  curl http://localhost:8000/api/health
  ```
- Frontend:
  ```text
  http://localhost:3000
  ```
- Database:
  ```bash
  docker compose ps
  cd backend && alembic current
  ```
- Auth:
  - Visit `http://localhost:3000/login`.
  - Continue with Google.
  - Confirm `/dashboard` is protected when logged out.
- OpenAI:
  - Set `OPENAI_API_KEY`.
  - Run a job match or resume generation flow.
  - Confirm safety warnings appear for missing profile skills.
- Google integrations:
  - Visit Settings.
  - Connect Drive and Gmail permissions.
  - Compile a generated resume PDF.
  - Upload it to Drive.
  - Send or trigger a digest.

## Git Safety Checklist

Before pushing, run:

```bash
git status --short --ignored
git diff
git check-ignore -v .env backend/storage frontend/node_modules frontend/.next backend/.venv
rg -n --hidden --glob '!.git' --glob '!frontend/node_modules/**' --glob '!frontend/.next/**' --glob '!backend/.venv/**' --glob '!backend/storage/**' '(sk-[A-Za-z0-9_-]+|AIza[0-9A-Za-z_-]+|refresh_token|access_token|private_key|client_secret)' .
```

Do not stage `.env`, credentials, generated PDFs, local storage, virtual environments, `node_modules`, or `.next`.

## GitHub Push Instructions

If you want `applywise-ai/` to be the repository root:

```bash
cd /Users/swatisingh/Documents/ApplyWise/applywise-ai
git init
git add .
git commit -m "Initial commit for ApplyWise AI"
git branch -M main
git remote add origin <MY_GITHUB_REPO_URL>
git push -u origin main
```

If you use the existing parent Git repository at `/Users/swatisingh/Documents/ApplyWise`, run:

```bash
cd /Users/swatisingh/Documents/ApplyWise
git add applywise-ai
git commit -m "Initial commit for ApplyWise AI"
git branch -M main
git remote add origin <MY_GITHUB_REPO_URL>
git push -u origin main
```

Do not run `git push` until you have reviewed `git status` and confirmed no secrets are staged.

## Future Scope

- Production-grade token encryption and secret management.
- Per-user Google Drive folder selection.
- Richer resume preview and template validation.
- More robust job page extraction adapters.
- Background worker deployment strategy.
- Better observability for scheduled runs.
- Optional deployment manifests for backend, frontend, and database.
