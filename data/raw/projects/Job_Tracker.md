# Job Tracker Project - Technical Overview

## 1. Repository layout (monorepo)

The workspace contains two applications:

- job_tracker_be: Go backend API service.
- job_tracker_fe: Next.js frontend dashboard.

Each app is independently runnable and has its own dependencies, tooling, and runtime configuration.

```
job_tracker_be/
  main.go
  go.mod
  internal/
    config/
    controller/
    dao/
    db/
    dto/
    globals/
    service/
  migrations/
  Dockerfile
  Makefile
  README.md

job_tracker_fe/
  app/
  features/
  lib/
  public/
  package.json
  next.config.ts
  README.md
```

## 2. Backend (job_tracker_be)

### 2.1 Technology stack

- Language: Go
- HTTP routing: chi (github.com/go-chi/chi/v5)
- Database: PostgreSQL (driver: pgx)
- Migrations: goose (github.com/pressly/goose/v3)
- Environment config: godotenv for .env loading

### 2.2 Runtime and startup flow

Entry point is main.go. Startup is sequential and includes:

1. Load configuration from environment variables (and .env file).
2. Apply database migrations (goose Up) on startup.
3. Initialize database pool (pgxpool).
4. Construct DAOs and Services.
5. Create the HTTP router with middleware and handlers.
6. Start HTTP server and wait for shutdown signals.

The migration step is intentionally built into startup so schema changes are always applied before the server accepts requests.

### 2.3 Configuration

The backend reads configuration via internal/config/config.go:

- DATABASE_URL (required)
- APP_PORT (default: 8080)
- DB_MAX_CONNS (default: 10)
- REQUEST_TIMEOUT_SECONDS (default: 5)
- N8N_WEBHOOK_URL (default points to a local n8n webhook)

The request timeout is used in controller handlers by applying a chi timeout middleware and a context timeout wrapper.

### 2.4 Database pool and connection strategy

internal/db/pool.go builds a pgxpool configuration using DATABASE_URL and sets:

- MaxConns = DB_MAX_CONNS
- MinConns = 1
- MaxConnIdleTime = 5 minutes
- MaxConnLifetime = 30 minutes

A ping is performed on startup to fail fast if the DB is unreachable.

### 2.5 Schema and migrations

Schema is managed via goose migrations under job_tracker_be/migrations:

- 00001_create_jobs.sql
  - Creates jobs table and job_status enum (initial statuses).
  - Adds indexes for status, company name, and applied_at.

- 00002_apply_link_unique_active.sql
  - Adds unique index on apply_link for active (not deleted) rows.

- 00003_add_discarded_status_reason.sql
  - Adds discarded status to job_status enum.
  - Creates discard_reason enum and adds discard_reason column.
  - Enforces a CHECK constraint that discard_reason is present only when status = discarded.

- 00004_add_job_description.sql
  - Adds job_description column.

- 00005_create_resume_queue.sql
  - Creates resume_generation_queue table to support resume generation workflow.
  - Enforces unique apply_link in resume_generation_queue.

- 00006_add_match_rating.sql
  - Adds match_rating (DOUBLE PRECISION) with a constraint 0..10.

The migrations intentionally preserve soft deletion semantics by keeping deleted rows and using filtered indexes (deleted_at IS NULL).

### 2.6 Data model and key fields

The primary table is jobs with the following notable fields:

- id: UUID primary key
- company_name, role_title, location
- job_description
- apply_link: required, normalized, unique among active rows
- linkedin_job_url, resume_link
- status: enum
- discard_reason: optional enum, only when status = discarded
- salary_text
- is_easy_apply: boolean
- match_rating: optional numeric (0..10)
- applied_at, created_at, updated_at, deleted_at

The resume_generation_queue table stores job_id, apply_link, status, created_at, updated_at.

### 2.7 Layered architecture

Backend code follows a layered architecture:

- controller: HTTP handlers, request parsing, response formatting.
- service: business rules and validation.
- dao: SQL queries and persistence logic.
- dto: request and response payloads.
- globals: shared constants and standard error types.

This separation keeps API behavior consistent and enables clear validation boundaries.

### 2.8 HTTP API surface

Routes are wired in internal/controller/routes.go:

- GET /health
- GET /jobs/events (SSE stream for job_created events)
- POST /jobs
- POST /jobs/bulk-delete
- POST /jobs/bulk-update-status
- POST /jobs/{id}/resume-generate
- GET /jobs
- GET /jobs/apply-rate
- GET /jobs/exists
- GET /jobs/{id}
- PUT /jobs/{id}
- PATCH /jobs/{id}/resume-link
- DELETE /jobs/{id}
- GET /resume-queue
- DELETE /resume-queue/{job_id}
- GET /resumes

### 2.9 Request handling and error shape

The controller layer:

- Uses a structured JSON error payload: { error: { code, message } }.
- Maps service errors to HTTP codes:
  - Bad request -> 400
  - Not found -> 404
  - Conflict -> 409
  - All other errors -> 500

The DTO layer defines strongly typed request and response payloads.

### 2.10 Validation and business rules

Key backend rules:

- Required fields on create: company_name, role_title, location, apply_link.
- apply_link is normalized and must be non-empty.
- status must be one of the allowed statuses.
- discard_reason is required only when status = discarded.
- match_rating must be within 0..10 if provided.
- applied_at defaults to current time if not provided.

Update rules:

- Each provided field is validated individually.
- apply_link is normalized and cannot be empty.
- status changes must remain within allowed values.
- discard_reason can be cleared or set; if invalid, update fails.
- match_rating supports clearing as well as validation.
- applied_at cannot be zero if provided.

Bulk operations:

- bulk-delete accepts an array of job IDs and soft-deletes them.
- bulk-update-status enforces:
  - status must be valid.
  - discard_reason required only for discarded.
  - discard_reason rejected for all other statuses.

### 2.11 Soft deletion

Delete operations do not remove rows. Instead, deleted_at is set and query filters always include deleted_at IS NULL. This enables uniqueness enforcement on active rows and supports possible data recovery or audit needs.

### 2.12 Filtering, paging, and sorting

List jobs uses:

- page, limit with defaults (1, 20) and max limit 100.
- status filter and discard_reason filter (discard_reason only allowed when status is discarded).
- company and location partial matching via ILIKE.
- match_rating min/max range filters.
- sort_match allows sorting by match_rating asc/desc with NULLS last and updated_at secondary ordering.

### 2.13 Apply rate statistics

Apply rate stats are aggregated in the backend:

- Daily, weekly, monthly counts from applied jobs.
- Averages computed based on the earliest applied job date.
- Statuses excluded from the applied baseline include added, discarded, and withdrawn.

### 2.14 Resume generation workflow

The resume generation flow is intentionally asynchronous:

1. Client calls POST /jobs/{id}/resume-generate.
2. Backend validates:
   - Job exists.
   - job_description is present.
   - resume_link does not exist yet.
3. Job is added to resume_generation_queue with status "added".
4. Backend calls an external webhook (N8N_WEBHOOK_URL) in a goroutine, passing job_id.

The resume generation queue can be read or cleaned via /resume-queue routes, and the frontend can later poll for a resume_link to appear.

### 2.15 Server-Sent Events (SSE)

The backend exposes GET /jobs/events and publishes a job_created event whenever a job is created. A simple in-memory broker fans out events to connected clients. Clients receive event: job_created with JSON payload containing the new job data.

### 2.16 CORS policy

CORS is implemented manually in the router:

- Allowed origins include http://localhost:3000 and http://localhost:5678.
- Credentials are supported.
- OPTIONS requests are handled with preflight headers.

### 2.17 Docker and CI/CD

The backend includes a Dockerfile for containerization (multi-stage build). A GitHub Actions workflow builds and pushes the backend image to Docker Hub on push to main/master.

## 3. Frontend (job_tracker_fe)

### 3.1 Technology stack

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS v4
- Lucide icons

### 3.2 App structure

The frontend is organized into:

- app/: Next.js routes and layouts.
- features/jobs/: domain-specific UI, hooks, and utilities.
- lib/api/: API client for backend endpoints.
- lib/types/: shared domain types.

The root route redirects to /jobs. The dashboard layout provides sidebar navigation and wraps all pages.

### 3.3 Styling and typography

Tailwind CSS is used with custom font variables:

- Manrope for body text.
- Space Grotesk for headings.

The root layout injects a theme initialization script that reads localStorage and system preferences to set the dark/light mode classes before hydration.

### 3.4 Theme management

Theme is managed in use-theme.ts:

- Stored in localStorage under job-tracker-theme.
- Applies class "dark" to documentElement and sets color-scheme.
- Settings page allows user selection (light/dark), and the current theme is displayed.

### 3.5 API client layer

lib/api/jobs.ts wraps all backend calls and standardizes errors:

- API_BASE_URL is resolved from NEXT_PUBLIC_API_BASE_URL with a default of http://localhost:8000.
- requestJson handles JSON errors and normalizes the response.
- ApiError includes status and code from backend error payload.
- Functions exist for list, get, create, update, delete, bulk actions, apply link checks, resume queue operations, and SSE subscription.

The API layer also provides helper utilities:

- normalizeApplyLink
- toIsoFromDateTimeLocal
- toDateTimeLocalValue
- formatAppliedDate

### 3.6 Core dashboard behavior (Jobs page)

JobsDashboard is the main interactive UI and uses the use-jobs-dashboard hook for all state and behavior.

Key UX features:

- Status summary pills (All + each status) with counts.
- Advanced filters (company, location, discard reason, match rating range, match sort).
- Infinite scroll based on intersection observer to fetch pages.
- Inline create/edit modal with validation, error display, and uniqueness checks.
- Inline job actions: quick status update, delete, edit.
- Bulk selection with toolbar for delete and status updates.
- Resume generation trigger with loading states.
- Apply link confirmation flow (opens apply link, then marks as applied).
- SSE subscription to refresh when jobs are created elsewhere.

### 3.7 Filters and persistence

Dashboard filters are persisted in localStorage:

- jobDashboardFilters contains status and discard visibility.
- Legacy key jobStatusFilter is preserved for migration compatibility.
- When status changes to discarded, discard_reason filter is enabled and validated.

### 3.8 Validation and form management

Validation is performed client-side before submission:

- company_name, role_title, location required.
- apply_link is normalized and required.
- status must be valid.
- discard_reason required for discarded.
- applied_at required and must be valid.
- match_rating must be a number between 0 and 10 if provided.

The frontend then delegates final enforcement to the backend, with API errors surfaced to the user.

### 3.9 Analytics and statistics

The frontend maintains:

- Analytics cards for total and per-status counts (based on listJobs totals).
- Apply rate stats via /jobs/apply-rate endpoint.

Statistics page provides a separate data visualization experience and rebuilds the stats from backend data on load.

### 3.10 Resume-related UI

Two UI surfaces exist:

- Resume queue: trigger resume generation from job cards (Jobs page).
- Resume library: /resumes page lists jobs with resume_link populated and provides a direct link to each resume.

The UI also polls for resume_link after enqueueing to provide a responsive experience once the link appears.

## 4. Cross-cutting behaviors and integration flows

### 4.1 Create job

1. User fills form in the dashboard modal.
2. Frontend validates fields and optionally checks /jobs/exists for apply_link uniqueness.
3. Frontend posts to /jobs.
4. Backend validates, normalizes, inserts job.
5. Backend publishes SSE job_created event.
6. Frontend receives event and refreshes list + analytics.

### 4.2 Update job

1. User opens edit modal, frontend fetches job with /jobs/{id}.
2. Frontend computes a patch (only changed fields).
3. PUT /jobs/{id} with updated fields.
4. Backend validates and persists, returns updated job.

### 4.3 Delete job

- DELETE /jobs/{id} soft deletes the row.
- Frontend refreshes and updates analytics.

### 4.4 Bulk operations

- bulk-delete: POST /jobs/bulk-delete with ids.
- bulk-update-status: POST /jobs/bulk-update-status with ids, status, discard_reason (if discarded).

Both operations enforce server-side validation and return counts for UI feedback.

### 4.5 Resume generation

- User clicks Generate Resume in the job card.
- Backend enqueues job and calls external webhook.
- Frontend polls /jobs/{id} until resume_link appears, then updates the job card.

## 5. Status and discard logic

Supported statuses:

- added
- applied
- interview
- offer
- rejected
- withdrawn
- discarded

Supported discard reasons:

- high_applicants
- security_clearance
- less_experience
- citizenship
- not_fit

Rules enforced both in UI and backend:

- discard_reason is required only when status = discarded.
- discard_reason is not allowed for other statuses.
- Filtering by discard_reason is only allowed with discarded status.

## 6. Pagination, limits, and defaults

Backend defaults:

- Page = 1
- Limit = 20
- Max limit = 100

Frontend defaults:

- Limit = 20
- Status filter defaults to added (persisted across sessions).

## 7. Development workflow

Backend:

1. Copy .env.example to .env and set DATABASE_URL.
2. Run migrations (make migrate-up) or allow startup to run goose automatically.
3. Start server (make run or go run main.go).

Frontend:

1. npm install
2. cp .env.example .env.local
3. npm run dev
4. Open http://localhost:3000

## 8. Reliability and data integrity considerations

- Soft deletes preserve data integrity and allow unique apply_link checks for active rows only.
- Validation occurs at both UI and service layer; backend remains the source of truth.
- Match rating and discard reason constraints are enforced in both code and DB schema.
- SSE channel is in-memory (per instance), so events are not persisted across restarts.

## 9. Summary

Job Tracker is a full-stack application for tracking job applications with a layered Go backend and a feature-rich Next.js frontend. The backend focuses on strong validation, clean separation of layers, and consistent error handling. The frontend provides a modern dashboard with real-time updates, bulk operations, analytics, and a resume generation queue. Together they form a consistent workflow for capturing job applications, managing statuses, and tracking outcomes over time.
