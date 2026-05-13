# Expensely Frontend 

## 1. Project scope and runtime goals

Expensely is a personal finance and expense management web application. This repository contains the frontend, built with Next.js App Router and TypeScript. The app provides authentication, onboarding, finance CRUD flows (expenses, income, budgets, recurring expenses), analytics dashboards, and notifications. The backend is a separate service and is accessed through API proxy rewrites.

Key runtime goals of the frontend:
- Present a cohesive, responsive UI for finance management workflows.
- Maintain a cookie-backed authenticated session with the backend.
- Persist user preferences and core application state across refreshes.
- Provide real-time notifications through WebSockets.
- Support a maintenance mode that can lock down access.

## 2. Core framework and dependencies

The application is a Next.js 16.1.6 App Router project using React 19 and TypeScript. Styling is done with Tailwind CSS 4 and a shadcn-style component architecture on top of Radix UI primitives.

Notable runtime libraries:
- Redux Toolkit with redux-persist for state management and persistence.
- Axios for HTTP requests, configured with interceptors for token refresh.
- NextAuth for OAuth login flows (Google provider).
- Supabase JS client for profile image storage access.
- Recharts for analytics charts.
- React Hook Form + Zod for form handling and validation.
- Framer Motion for motion and transitions.
- Vercel Analytics and Speed Insights for telemetry.


## 3. Deployment and hosting

The frontend is deployed on Vercel. It includes Vercel Analytics and Speed Insights in production. Any hosting provider must be configured with the required environment variables for API access, auth, and WebSocket URLs.




# Expensely Backend (expensely_backend)

## Purpose
Expensely Backend is a Java based application that powers the Expensely expense tracking app. It exposes REST APIs for authentication, user profile management, expenses, incomes, budgets, categories, recurring expenses, and notifications/alerts. PostgreSQL is the primary datastore, JWT cookies are used for auth, and WebSocket alerts are supported.


## Tech Stack
- Language: Java 17
- Framework: Spring Boot 3.5.x
- Build: Gradle (see `build.gradle`)
- Database: PostgreSQL, Spring Data JPA, Hibernate
- Auth: JWT (access + refresh), email OTP verification, Google OAuth token verification
- WebSocket: Spring WebSocket for alerts
- Utilities: Mailgun integration, CSV export/import, scheduled jobs

## High-Level Architecture
- Controllers expose REST endpoints under `/api/**` plus `/ping` for health.
- Services implement domain logic and orchestration across repositories.
- Repositories are Spring Data JPA interfaces for database access.
- Models are JPA entities for users, expenses, incomes, categories, budgets, messages, etc.
- DTOs provide API request/response shapes and aggregation views.
- Security layer uses a JWT filter and cookie-based auth.
- WebSocket handler pushes alerts and persists missed messages.
- A scheduled job converts recurring expenses into real expenses daily.

## Authentication and Security
- JWTs are stored in HttpOnly cookies: `accessToken` (15 min) and `refreshToken` (7 days).
- `JwtAuthFilter` reads `accessToken` from cookies and resolves a user from the token subject.
- Public endpoints include login, register, OTP verify/resend, password reset, OAuth verify, `/ping`.
- Email verification is required for authenticated access.
- CORS is configured via `ALLOWED_ORIGINS` env.

### Email OTP and Password Reset
- OTPs are stored hashed, expire in 10 minutes, and enforce resend cooldowns.
- Failed attempts trigger progressive lockouts.
- Password reset issues a token hash and validates against stored hash.

## API Surface (Controllers)
Base paths shown below; endpoints are summarized by purpose.


### `IncomeController` — `/api/incomes`
- CRUD: `POST /create`, `GET /{id}`, `PUT /update/{id}`, `DELETE /{id}`.
- User lists: `GET /user` and by category.
- Overview: `GET /overview`.
- Filtering: `GET /fetch-with-conditions`.
- Export: `GET /user/{userId}/export` (CSV).
- Bulk: `POST /bulk-delete`.
- Monthly charts: `GET /monthly`, `GET /monthly/category`.

### `CategoryController` — `/api/categories`
- Create: `POST /create`.
- Get by id: `GET /{id}`.
- User categories: `GET /user` (optional `type`).
- Update: `PATCH /update/{id}`.

### `BudgetController` — `/api/budgets`
- Create: `POST /create`.
- Get: `GET /{id}`.
- Update: `PUT /{id}`.
- Delete: `DELETE /{id}` (soft delete).
- Lists: `GET /all`, `GET /user/{userId}`.
- `GET /available-categories`: categories without an active budget.

### `RecurringExpenseController` — `/api/recurring-expenses`
- Create, update, delete, activate/deactivate recurring expenses.
- `GET /fetch-all` to list for a user.

### `AdminController` — `/api/admins`
- Admin-only user management: activate/deactivate/set-admin.

### `WebSocketController` — `/api/web_sockets`
- Alert commands: send, delete, mark read, broadcast (admin only).
- Uses cookie token to resolve user.

### `Ping` — `/ping`
- Health endpoint returning `pong`.

## WebSocket Alerts
- WebSocket endpoint: `/ws/alerts?uuid=<userId>`.
- `AlertHandler` tracks sessions per user, persists messages to DB, and delivers on connect.
- Broadcasts are supported via the web socket service.

## Scheduled Jobs
- `ExpenseRecurrenceJob` runs daily at midnight.
- Converts active recurring expenses into real expenses and advances next occurrence.

## Logging and Observability
- `ApiRequestLoggingFilter` captures request metadata into `ApiRequestLog`.
- `FunctionLogAspect` writes function-level logs to `FunctionLog`.
- `DbLogService` persists log messages for operations and jobs.

## Utilities and Helpers
- `JwtUtil` for token creation and validation.
- `CookieUtils` for extracting cookie values.
- `ExpenseCsvParser` for CSV import/validation.
- `FormatDate` for consistent date range handling.
- `Mailgun` integration for email delivery.
