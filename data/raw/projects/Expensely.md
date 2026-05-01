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

## 3. Application entry, layouts, and global behavior

### 3.1 Root layout
- The app-level layout is defined in `app/layout.tsx`.
- It wraps the UI in a Redux provider and injects Vercel Analytics + Speed Insights.
- It reads `NEXT_WEBSITE_DOWN` to optionally show a maintenance splash screen for the entire app.
- Global CSS is imported via `app/globals.css`.

### 3.2 Route group layouts
The app uses App Router route groups to separate public and protected flows.

- `app/(pages)/layout.tsx` is the protected layout:
  - Reads cookies to initialize the sidebar open/close state (`sidebar_state`).
  - Redirects to `/login` when `NEXT_MAINTENANCE_MODE` is true.
  - Wraps pages with a `SidebarProvider` and a top-level dashboard shell component.

- `app/(auth)/layout.tsx` is the authentication layout:
  - Provides a full-screen auth background and a maintenance lockout overlay.
  - Uses `UserPreferences` to sync theme and theme color to the DOM.

### 3.3 Landing page
- `app/page.tsx` provides the public marketing/landing page.
- It renders a hero section, feature blocks, and CTA panels.
- Navigation uses the shared landing page navbar component.

## 4. Routing and feature modules

The application is organized by App Router segments and route groups:
- `app/(auth)/` contains auth flows: login, register, forgot/reset password, OTP verification, and onboarding.
- `app/(pages)/` contains protected pages for dashboard, expenses, income, budgets, categories, recurring expenses, profile, settings, and admin.
- `app/about/` contains the public About page.

A high-level feature map:
- Dashboard: analytics summaries, chart visualizations, time-range comparisons.
- Expense and Income: CRUD tables, filters, and aggregations.
- Budget and Recurring Expense: period-based budgeting and recurring schedule logic.
- Category: typed categories that drive reporting and CRUD forms.
- Profile and Settings: user preferences, theme selection, and profile media.
- Admin: user management (activate/deactivate and role elevation).

## 5. State management and persistence

State management uses Redux Toolkit with redux-persist and a client-only storage fallback for SSR.

### 5.1 Store configuration
- Store defined in `redux/store.ts`.
- Combines slices: `sidebar`, `user`, `categoryExpense`, and `notification`.
- Redux persistence uses `localStorage` on the client and a noop storage in SSR.
- Persisted slices: `user`, `categoryExpense`, `notification`.

### 5.2 Provider composition
- `redux/provider.tsx` wraps the app with:
  - `Provider` from `react-redux`.
  - `PersistGate` from `redux-persist`.
  - `SessionProvider` from NextAuth.
- NextAuth types are augmented to include `accessToken` and `idToken`.

## 6. API integration and network behavior

### 6.1 API client
- The API client is defined in `lib/api.tsx` using Axios.
- Base URL is `/api`, which is mapped to the backend via Next.js rewrites.
- `withCredentials: true` ensures cookie-backed sessions are included.

### 6.2 Token refresh and auth sync
- Responses to `/users/me` are intercepted to sync user state into Redux.
- Theme and theme color are normalized and applied to the DOM based on user preferences.
- If a request returns 401, the client attempts `/users/refresh`, then retries.
- If refresh fails, the user is redirected to `/login`.
- Inactive user errors trigger a forced logout and a reset of persisted slices.

### 6.3 Next.js rewrites
- `next.config.ts` defines rewrites that map `/api/*` routes to the backend URL:
  - `/api/users/*`, `/api/expenses/*`, `/api/incomes/*`, `/api/budgets/*`, `/api/categories/*`, `/api/recurring-expenses/*`, `/api/web_sockets/*`, `/api/admins/*`.
- This keeps frontend requests relative while enabling backend proxying.

## 7. WebSocket notifications

- Real-time notifications use `hooks/useWebSocket.ts`.
- The hook connects to `NEXT_PUBLIC_WS_URL` and passes `uuid=<userId>`.
- It sends heartbeat messages at a configured interval.
- It automatically reconnects on disconnect unless manually closed.
- Incoming messages are parsed and dispatched to the `notification` slice.

## 8. Theming, preferences, and UI state

### 8.1 Theme system
- Theme definitions and color palette are in `global/constants.tsx`.
- `ThemeId` values: `light`, `dark`, `system`.
- Theme color IDs include `teal`, `blue`, `indigo`, `emerald`, `amber`, `rose`, `slate`.

### 8.2 User preference sync
- `utils/userPreferences.tsx` watches the Redux user state and applies:
  - The theme class (`dark` or system preference).
  - A `data-theme-color` attribute for theming tokens.
  - `localStorage` values for theme and theme color.

## 9. Domain types and DTOs

Shared domain types are centralized in `global/dto.tsx`.

This file defines:
- Category and user skeletons used across forms and data tables.
- Budget and recurring expense request/response types.
- Expense and income overview aggregates for dashboards.
- Enums for `Period`, `OverviewEnum`, and `Recurrence`.
- DTOs for alerts and bulk import validation responses.

These types ensure consistent shape alignment across UI components and API client logic.

## 10. Notifications UI

- `components/notifications.tsx` renders the notification popover.
- It uses shadcn-style composition with Radix UI primitives.
- Unread counts are computed from the Redux `notification` slice.
- Each notification supports actions: mark as read and delete.

## 11. Supabase integration

- The Supabase client is created in `utils/supabase.tsx`.
- This supports profile image storage and related media flows.
- The Next.js image domain allowlist includes the Supabase project domain.

## 12. Environment configuration

The frontend expects the following variables in `.env.local`:
- `NEXT_PUBLIC_API_URL` for the backend API base URL.
- `NEXT_PUBLIC_WS_URL` for WebSocket notifications.
- `NEXTAUTH_SECRET`, `NEXT_PUBLIC_CLIENT_ID`, `NEXT_PUBLIC_CLIENT_SECRET` for NextAuth.
- `NEXT_MAINTENANCE_MODE` and `NEXT_WEBSITE_DOWN` for maintenance control.
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` for storage access.

## 13. Build and development commands

Defined in `package.json`:
- `npm run dev` starts the Next.js dev server.
- `npm run build` creates a production build.
- `npm run start` starts the production server.
- `npm run lint` runs Next.js lint.
- `npm run format` formats via Prettier.

## 14. Deployment and hosting

The frontend is deployed on Vercel. It includes Vercel Analytics and Speed Insights in production. Any hosting provider must be configured with the required environment variables for API access, auth, and WebSocket URLs.

## 15. Repository structure recap

- `app/` App Router pages, layouts, and route groups.
- `components/` shared UI and feature-level components.
- `components/ui/` shadcn-style primitives and wrappers.
- `redux/` store and Redux slices.
- `hooks/` custom hooks (WebSocket, responsiveness).
- `lib/` API client logic.
- `utils/` helpers (auth, preferences, formatting, API tokens).
- `config/` runtime configuration constants.
- `global/` shared constants and DTO types.
- `public/` static assets.


# Expensely Backend (expensely_backend)

## Purpose
Expensely Backend is a Spring Boot service that powers the Expensely expense tracking app. It exposes REST APIs for authentication, user profile management, expenses, incomes, budgets, categories, recurring expenses, and notifications/alerts. PostgreSQL is the primary datastore, JWT cookies are used for auth, and WebSocket alerts are supported.

Frontend repo reference: https://github.com/n-saji/Expensely-FE

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

## Build and Run
- Gradle build produces `build/libs/expensely_backend-1.0.0.jar`.
- Dockerfile builds the jar in a builder stage and runs it on JRE 17.
- `docker-compose.yml` spins up Postgres and the app with env vars.
- Kubernetes manifests under `k8/` define configmap, secret, deployment, and service.

## Configuration and Environment
### Application Properties (`src/main/resources/application.properties`)
- `spring.datasource.url=${DB_URL}`
- `server.port=${SERVER_PORT:8080}`
- `jwt.secret=${JWT_SECRET}`
- `GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}`
- JPA and Hikari pool tuning are configured for a small DB pool.

### Docker Compose (`docker-compose.yml`)
- `DB_URL=jdbc:postgresql://db:5432/expensely`
- `DB_USERNAME=postgres`
- `DB_PASSWORD=postgres`
- `JWT_SECRET=your-super-secret-key-which-is-32-characters`

### Kubernetes (`k8/`)
- `configmap.yaml` provides `ALLOWED_ORIGINS`, `GOOGLE_CLIENT_ID`, `SERVER_PORT`.
- `secret.yaml` provides base64-encoded `DB_URL`, `JWT_SECRET`, `MAILGUN_API_KEY`.
- `deployment.yaml` runs `nikhilsaji/expensely-app:latest`, 4 replicas.
- `service.yaml` exposes NodePort `30007`.

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

### `UserController` — `/api/users`
- `POST /register`: create user, send verification OTP via email.
- `POST /login`: authenticate and set JWT cookies.
- `POST /verify-otp`, `POST /resend-otp`: email verification flow.
- `POST /request-password-reset`, `POST /confirm-password-reset`: password reset flow.
- `GET /check-auth`: validate access token from cookie.
- `GET /me`: return current user profile.
- `PATCH /update-profile`, `PATCH /update-settings`, `PATCH /update-password`.
- `DELETE /delete-account/{id}`: soft delete by deactivating user.
- `PATCH /{id}/update-profile-picture`.
- `POST /verify-oauth-login`: Google ID token verification and login/registration.
- `GET /all`: admin-only list of all users.
- `GET /refresh`: refresh access token using refresh cookie.
- `GET /logout`: clear auth cookies.
- `GET /alerts`: fetch user alerts (respects `alertsEnabled`).
- `GET /send-mail-test`: send a Mailgun test email.

### `ExpenseController` — `/api/expenses`
- CRUD: `POST /create`, `GET /{id}`, `PUT /update/{id}`, `DELETE /{id}`.
- User lists: `GET /user/{userId}` and by category/timeframe.
- Overview: `GET /user/{userId}/overview` (monthly/yearly aggregation).
- Filtering: `GET /user/{userId}/fetch-with-conditions` (search, sort, paginate).
- Export: `GET /user/{userId}/export` (CSV).
- Bulk: `POST /user/{userId}/bulk-delete`.
- Bulk upload: `POST /bulk_upload/validate` and `GET /bulk_upload/upload`.
- Monthly charts: `GET /monthly`, `GET /monthly/category`.

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

## Data Model (Entities)
Key JPA entities under `src/main/java/com/example/expensely_backend/model`:
- `User`: account profile, settings, auth flags, admin flag, active flag.
- `Expense`, `Income`: financial records linked to user and category.
- `Category`: expense/income categories.
- `Budget`: category budgets per user with soft delete.
- `RecurringExpense`: scheduling for recurring expenses.
- `ExpenseFiles`: bulk upload tracking.
- `EmailOtp`: OTP storage for email verify and password reset.
- `Messages`: alert/notification storage.
- `ExpiredToken`, `ApiRequestLog`, `FunctionLog`: security and operational logs.

## DTOs and Aggregations
DTOs under `src/main/java/com/example/expensely_backend/dto` represent:
- Auth responses and user responses.
- Expense/income overviews, daily aggregates, monthly category aggregates.
- Bulk upload validation and error reporting.
- OTP and password reset requests.
- WebSocket message payloads.

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

## Project Layout (Key Paths)
- `src/main/java/com/example/expensely_backend/controller`: REST controllers.
- `src/main/java/com/example/expensely_backend/service`: business logic.
- `src/main/java/com/example/expensely_backend/repository`: JPA repositories.
- `src/main/java/com/example/expensely_backend/model`: entity definitions.
- `src/main/java/com/example/expensely_backend/utils`: auth, logging, jobs, helpers.
- `src/main/java/com/example/expensely_backend/handler`: WebSocket handler.
- `src/main/resources/application.properties`: app config.
- `docker-compose.yml`, `Dockerfile`: local containerized run.
- `k8/`: Kubernetes manifests for deployment.
- `db-backup/`: sample backup text exports.
- `scripts/perf/overview-latency.sh`: perf comparison for overview endpoint.

## Notes and Potential Inconsistencies
- `README.md` mentions Maven, but the build uses Gradle (`build.gradle`).
- Security config currently permits all routes due to a noted bug; JWT filter still enforces auth for most routes.

