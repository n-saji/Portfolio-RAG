# Job Tracker Project - Technical Overview

## About

Built an end-to-end job acquisition pipeline that scrapes listings, filters for eligibility and uses an LLM to score and route roles into tiers with a webhook triggered flow that generates a tailored resume per job, publishes it to Google Drive and syncs the link back to a PostgreSQL-backed dashboard built in Next.js and Go.

## 2. Backend (job_tracker_be)

### 2.1 Technology stack

- Language: Go
- HTTP routing: chi (github.com/go-chi/chi/v5)
- Database: PostgreSQL (driver: pgx)
- Migrations: goose (github.com/pressly/goose/v3)
- Environment config: godotenv for .env loading



### 2.2 Layered architecture

Backend code follows a layered architecture:

- controller: HTTP handlers, request parsing, response formatting.
- service: business rules and validation.
- dao: SQL queries and persistence logic.
- dto: request and response payloads.
- globals: shared constants and standard error types.

This separation keeps API behavior consistent and enables clear validation boundaries.

### 2.3 HTTP API surface

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

### 2.4 Request handling and error shape

The controller layer:

- Uses a structured JSON error payload: { error: { code, message } }.
- Maps service errors to HTTP codes:
  - Bad request -> 400
  - Not found -> 404
  - Conflict -> 409
  - All other errors -> 500

The DTO layer defines strongly typed request and response payloads.

### 2.5 Validation and business rules

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

### 2.6 Soft deletion

Delete operations do not remove rows. Instead, deleted_at is set and query filters always include deleted_at IS NULL. This enables uniqueness enforcement on active rows and supports possible data recovery or audit needs.

### 2.7 Filtering, paging, and sorting

List jobs uses:

- page, limit with defaults (1, 20) and max limit 100.
- status filter and discard_reason filter (discard_reason only allowed when status is discarded).
- company and location partial matching via ILIKE.
- match_rating min/max range filters.
- sort_match allows sorting by match_rating asc/desc with NULLS last and updated_at secondary ordering.

### 2.8 Apply rate statistics

Apply rate stats are aggregated in the backend:

- Daily, weekly, monthly counts from applied jobs.
- Averages computed based on the earliest applied job date.
- Statuses excluded from the applied baseline include added, discarded, and withdrawn.

### 2.9 Resume generation workflow

The resume generation flow is intentionally asynchronous:

1. Client calls POST /jobs/{id}/resume-generate.
2. Backend validates:
   - Job exists.
   - job_description is present.
   - resume_link does not exist yet.
3. Job is added to resume_generation_queue with status "added".
4. Backend calls an external webhook (N8N_WEBHOOK_URL) in a goroutine, passing job_id.

The resume generation queue can be read or cleaned via /resume-queue routes, and the frontend can later poll for a resume_link to appear.

### 2.10 Server-Sent Events (SSE)

The backend exposes GET /jobs/events and publishes a job_created event whenever a job is created. A simple in-memory broker fans out events to connected clients. Clients receive event: job_created with JSON payload containing the new job data.


### 2.11 Docker and CI/CD

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


## 9. Summary

Job Tracker is a full-stack application for tracking job applications with a layered Go backend and a feature-rich Next.js frontend. The backend focuses on strong validation, clean separation of layers, and consistent error handling. The frontend provides a modern dashboard with real-time updates, bulk operations, analytics, and a resume generation queue. Together they form a consistent workflow for capturing job applications, managing statuses, and tracking outcomes over time.
