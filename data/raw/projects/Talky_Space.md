# Talky Space BE 
## 1. Purpose and scope
- A Go backend for a chat application with users, chatrooms, messages, authentication, and WebSocket realtime delivery.
- REST endpoints for auth, users, chatrooms, messages, and WebSocket connection.
- PostgreSQL for persistence, with SQL migrations managed by Goose.
- JWT access and refresh tokens stored in HttpOnly cookies.

## 2. Tech stack and key dependencies
- Go 1.24.2 (see [go.mod](go.mod))
- Routing: `github.com/go-chi/chi/v5`
- Validation: `github.com/go-playground/validator/v10` (used in auth handler only)
- Auth tokens: `github.com/golang-jwt/jwt/v5`
- UUIDs: `github.com/google/uuid`
- WebSockets: `github.com/gorilla/websocket`
- Database access: `github.com/jackc/pgx/v5/pgxpool` (direct SQL, not ORM)
- Env loading: `github.com/joho/godotenv`
- Migrations: `github.com/pressly/goose/v3`
- Password hashing: `golang.org/x/crypto/bcrypt`
- GORM is present only for model hooks and error sentinel (`gorm.ErrRecordNotFound`), but not used for database operations.

## 3. Runtime startup flow
Entry point is [main.go](main.go).

1. Load config using `config.Load()`.
2. Create a context that cancels on SIGINT or SIGTERM.
3. Create a pgx connection pool with `config.ConnectToDb(ctx)`.
4. Ping the DB using `config.PingDb(ctx, pool)`.
5. Run SQL migrations using Goose with embedded migrations.
6. Build DAOs and services, then router.
7. Start the WebSocket hub in a goroutine.
8. Start HTTP server and wait for shutdown signal.

The HTTP server uses timeouts:
- Read timeout: 5s
- Write timeout: 10s
- Idle timeout: 120s
- Read header timeout: 5s

## 4. Configuration and environment variables
Configuration is loaded from `.env` (via `godotenv.Load`) or defaults.

Relevant keys (see [config/config.go](config/config.go)):
- `DATABASE_URL` default `postgres://user:password@localhost:5432/talky_space`
- `SERVER_PORT` default `8080`
- `FRONTEND_URL` default `http://localhost:3000`
- `ACCESS_TOKEN_SECRET` (required for JWT)
- `REFRESH_TOKEN_SECRET` (required for JWT)
- `REQUEST_TIMEOUT_SECONDS` default `5`

Database pool settings (see [config/db.go](config/db.go)):
- Max conns: 20
- Min conns: 5
- Max lifetime: 1 hour
- Max idle: 10 minutes
- Connect timeout: 30 seconds
- Health check period: 1 minute

## 5. Database schema and migrations
All schema is defined in [migrations/20251013213454_all_tables.sql](migrations/20251013213454_all_tables.sql), executed at startup.

Tables:
- `users`: id, username, email (unique), phone_number (unique), password_hash, avatar_url, created_at, updated_at
- `chatrooms`: id, name, description, is_group, created_by (FK users), created_at, updated_at
- `chatroom_members`: id, chatroom_id, user_id, joined_at, unique(chatroom_id, user_id)
- `messages`: id, chatroom_id, user_id, content, created_at + indexes on chatroom_id and user_id
- `summaries`: id, chatroom_id, content, generated_by, generated_at (not referenced elsewhere in code)
- `sessions`: id, user_id, refresh_token, expires_at, created_at (optional, not wired in auth flow)

## 6. HTTP routing and middleware
Routing is defined in [handlers/router.go](handlers/router.go) with `chi`.

Global middleware:
- Custom CORS handler: allows `Origin` only when `http://localhost:3000` and sets CORS headers
- Request ID, RealIP, Logger, Recoverer from chi

Routes:
- `GET /health` -> returns `ok`

Auth routes (public):
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`

Authenticated routes (JWT cookie or Authorization header):
- `GET /channel/{id}` (not implemented)
- `POST /channel/` (not implemented)
- `POST /chatrooms/` (not implemented)
- `GET /chatrooms/` (not implemented)
- `GET /chatrooms/{chatroom_id}`
- `PUT /chatrooms/{chatroom_id}` (not implemented)
- `DELETE /chatrooms/{chatroom_id}` (not implemented)
- `GET /chatrooms/find-by-users/user1/{uid1}/user2/{uid2}`
- `GET /chatrooms/user`
- `POST /messages/new-chat`
- `GET /messages/chatroom/{cid}`
- `GET /ws/connect` (WebSocket upgrade)
- `GET /users/me`
- `PUT /users/update`
- `DELETE /users/delete`
- `GET /users/look-up`

Public user route:
- `POST /users/register`

## 7. Authentication flow
Auth logic lives in [handlers/authHandler.go](handlers/authHandler.go) and [service/authService.go](service/authService.go), with JWT helpers in [auth/jwt.go](auth/jwt.go).

Login:
1. Validate `email` and `password` using validator.
2. Service `AuthenticateUser` fetches user by email and compares bcrypt password hash.
3. JWT access token (15 minutes) and refresh token (7 days) created with `user_id` claim.
4. Set `refresh_token` and `access_token` as HttpOnly cookies.
5. Response JSON includes `access_token`.

Refresh:
1. Read refresh token from cookie.
2. Verify JWT using refresh secret.
3. Generate new access and refresh tokens.
4. Set cookies again and return JSON with access token.

Logout:
- Clears both cookies by setting MaxAge -1.

Auth middleware (see [middleware/auth_middleware.go](middleware/auth_middleware.go)):
- Reads access token from `Authorization: Bearer` or `access_token` cookie.
- Verifies token with access secret.
- Extracts `user_id` claim and puts it in request context.

## 8. Service layer responsibilities
Services are thin orchestration over DAOs and model converters.

Users (see [service/usersService.go](service/usersService.go)):
- Create user: validate, check for existing email or phone, hash password, insert.
- Get user by ID, update fields, delete.
- Look-up users by username/email/phone, excluding current user.

Chatrooms (see [service/chatroomService.go](service/chatroomService.go)):
- Validate and create chatroom
- Get chatroom by ID
- Update chatroom
- Delete chatroom
- Find chatroom by two users (private chat)
- Fetch all chatrooms for a user; for private chats, replace chatroom name with the other member username

Chatroom members (see [service/chatroomMembersService.go](service/chatroomMembersService.go)):
- Create member, list by chatroom, remove member, check membership

Messages (see [service/messagesService.go](service/messagesService.go)):
- Create a message; if no chatroom exists for sender/recipient, a new private chatroom is created
- Store message in DB
- Fetch messages by chatroom

WebSocket broadcast helper (see [service/webSockets.go](service/webSockets.go)):
- Sends a server-origin message into the hub broadcast channel

## 9. DAO layer and SQL usage
DAO objects in [daos](daos) use `pgxpool` and raw SQL for all access. There is no ORM-based query building.

Key DAO methods:
- Users: create, get by email/id/phone, update, delete, lookup
- Chatrooms: create, read, update, delete
- Chatroom members: add, list, remove, membership check
- Messages: create, fetch by chatroom, delete by chatroom
- Sessions: save refresh token (defined but not used)

## 10. Models and DTOs
Models define DB shapes and conversion to DTOs. DTOs define HTTP payloads.

Models:
- [models/users.go](models/users.go), [models/chatrooms.go](models/chatrooms.go), [models/chatroomMembers.go](models/chatroomMembers.go), [models/messages.go](models/messages.go), [models/sessions.go](models/sessions.go)
- GORM hooks exist but are not triggered by pgx queries. The code manually sets timestamps and UUIDs.

DTOs:
- Auth: [dtos/auth.go](dtos/auth.go)
- Users: [dtos/users.go](dtos/users.go)
- Chatrooms: [dtos/chatrooms.go](dtos/chatrooms.go)
- Chatroom members: [dtos/chatroomMembers.go](dtos/chatroomMembers.go)
- Messages: [dtos/messages.go](dtos/messages.go)
- WebSockets DTO file exists but is empty ([dtos/webSockets.go](dtos/webSockets.go))

## 11. WebSocket hub behavior
The hub is in [utils/webSockets.go](utils/webSockets.go) and is started from main with `go utils.HubInstance.Run(ctx)`.

Core behavior:
- On connection, a client is registered in `HubInstance.Clients` by user ID.
- `ReadPump` reads raw WS messages and forwards them to `HubInstance.Broadcast`.
- `Run` listens to `Broadcast` and decodes JSON into `MessagePayload`.
- It queries chatroom members and sends the message to each member's websocket connection except the sender.
- When the message is not marked as `source = "server"`, it also stores the message to DB when it encounters the sender member record.

Important integration requirement:
- `Hub` has a `pool *pgxpool.Pool` but it is never assigned in current code. `Run` immediately does `db := daos.NewPgxDao(h.pool)`.
- This will lead to a nil pointer if `HubInstance.pool` is not set before `Run` starts. The current `main.go` does not set it.

## 12. Error handling and response shape
- Handlers mostly return JSON errors using simple `{ "error": "message" }` or `writeError` with code and message (see [handlers/router.go](handlers/router.go)).
- Global error codes exist in [global/errors.go](global/errors.go) but are only partially used.

## 13. Dockerfile
A simple Docker build is defined in [Dockerfile](Dockerfile):
1. Base image `golang:1.24-alpine`
2. Copy `go.mod` and `go.sum`, download dependencies
3. Copy source and build `main`
4. Expose port 8080
5. Run `./main`

## 14. Not implemented or partially wired features
- Chatroom create/update/delete endpoints are present but return Not Implemented.
- Channel routes are present but not implemented.
- Session persistence for refresh tokens is defined in DAOs and models but commented out in auth service.
- `summaries` table exists in migrations but has no usage in code.
- WebSocket DTO file is empty.
- Hub database pool wiring is missing (see WebSocket note above).

## 15. Suggested high level data flows

Login:
1. Client posts credentials to `/auth/login`.
2. Service validates and returns tokens.
3. Cookies are set and access token is also returned in JSON.

Send a message (REST):
1. Client POST `/messages/new-chat` with sender/recipient/content.
2. Service verifies or creates chatroom, stores message, and broadcasts to WebSocket hub.

Send a message (WebSocket):
1. Client sends JSON message to `/ws/connect` socket.
2. Hub reads and broadcasts to all members in the chatroom.
3. Message is stored in DB for sender member only (non server messages).

Fetch chat history:
- Client GET `/messages/chatroom/{cid}` returns all messages ordered by created_at.

## 16. Files and directories at a glance
- `main.go`: application boot, config, DB, migrations, router, WebSocket hub
- `config/`: env config and DB pool
- `auth/`: JWT helpers
- `middleware/`: auth middleware
- `handlers/`: HTTP handlers and routing
- `service/`: business logic
- `daos/`: SQL layer using pgxpool
- `models/`: DB models and converters
- `dtos/`: request and response payloads
- `utils/`: WebSocket hub, client, and broadcast helpers
- `migrations/`: database schema

## 17. Operational notes for RAG consumers
- The code uses cookies for JWT tokens, not just Authorization headers.
- The CORS logic only permits `http://localhost:3000` origin and short-circuits OPTIONS.
- DB migrations run automatically at startup, using embedded SQL.
- The API is designed around UUIDs for all main entities.
- There is a mix of SQL and model-based transformations; do not assume GORM handles persistence.



# Talky Space - Fronted

## 1) Project Purpose and Scope

TalkySpace is a modern chat application built on the Next.js App Router. It provides:

- A public landing page with basic marketing content.
- Authentication flows (sign in and sign up).
- A dashboard shell with sidebar navigation.
- A real-time chat experience that uses WebSockets for live messages.
- User profile management, including avatar uploads stored in Supabase.

The UI uses Tailwind CSS and a collection of reusable UI primitives built on Radix UI and shadcn-style components.

## 2) Core Technology Stack

- Framework: Next.js 15 (App Router)
- Language: TypeScript (React 19)
- Styling: Tailwind CSS v4 + CSS variables + tw-animate-css
- State management: Redux Toolkit + redux-persist
- Forms and validation: react-hook-form + zod
- Real-time transport: WebSocket (browser WebSocket API)
- API client: Axios (with refresh-token retry)
- Auth and user storage: Custom backend API (JWT stored in cookies) + Supabase storage for avatar files
- UI primitives: Radix UI and custom components under src/components/ui

## 3) App Structure (High Level)

Top-level routing and layout are handled by the App Router under src/app.

- Global layout sets up providers (Redux + theme) and fonts.
- A landing page lives at / with a navbar, hero, and footer.
- Auth is handled under /login with sign-in and sign-up tabs.
- Application pages live under the (pages) route group (e.g. /dashboard, /chat, /profile).
- Chat uses nested dynamic routes under /chat/[recipient].

## 4) Global Layout and Providers

The root layout (src/app/layout.tsx) sets up:

- Next.js metadata and Geist font loading.
- ReduxProvider (store + redux-persist gate).
- ThemeProvider (next-themes for dark/light system support).
- Global UI notifications with Sonner.

This ensures all pages share the same state and theme context.

## 5) Routing and Page Groups

Next.js App Router route groups are used for logical organization.

- (landingPage) group: home page sections
- (auth) group: /login
- (pages) group: app shell with sidebar and nested pages

Key routes:

- /: landing page
- /login: sign-in / sign-up
- /dashboard: placeholder dashboard
- /chat: search and entry into a chat room
- /chat/[recipient]: active chat thread with a user
- /profile: user profile and avatar editing

## 6) Authentication Flow

Authentication is based on a backend API and cookies:

- The access token is stored in a cookie named access_token.
- Middleware checks the cookie and redirects /login to /dashboard if a token exists.
- Protected route checks for /chat are present but currently commented out.

### Sign In

- Form validates input with zod and react-hook-form.
- Submits POST /auth/login?remember_me=true|false via Axios.
- On success, it fetches /users/me to populate Redux user state.
- UI feedback uses Sonner toast notifications.

### Sign Up

- Validates name, email, phone, password, confirm password.
- Submits POST /users/register using fetch.
- On success, navigates to /dashboard.

## 7) API Client and Token Refresh

A shared Axios client lives in src/lib/api.tsx with:

- baseURL from NEXT_PUBLIC_API_URL
- withCredentials enabled to send cookies

A response interceptor handles refresh:

- If any request fails with 401 (not already retried), it calls POST /auth/refresh.
- If refresh succeeds, the original request is retried.
- If refresh fails, it redirects to /login on the client.

## 8) State Management (Redux)

The Redux store is configured with redux-persist:

- user slice: persists user profile data
- websocket slice: stores socket connection state and in-memory message list

Persistence configuration:

- Storage: localStorage
- Whitelist: user only

This ensures user identity is retained across refreshes, while chat messages are transient.

## 9) Real-time Chat System

### WebSocket Connection Manager

The app shell layout (src/app/(pages)/layout.tsx) creates and manages a WebSocket connection:

- URL uses NEXT_PUBLIC_WS_URL
- On open: sets connected true
- On message: parses JSON and dispatches addMessage
- On close: retries with exponential backoff (max 5 attempts)
- On unmount: closes socket and clears timers

The socket instance is stored in Redux for access across the app.

### Chat Context

Chat page uses a custom context (RecipientContext) to track:

- selected recipient user
- active chatroom metadata
- server-side messages fetched on chat start

This avoids unnecessary Redux coupling for local chat state.

### Chat Start Flow

When a user searches and selects a recipient:

1. Fetch chatroom between users: GET /chatrooms/find-by-users/user1/:id/user2/:id
2. Fetch messages for chatroom: GET /messages/chatroom/:chatroomId
3. Store recipient, chatroom, and messages in RecipientContext
4. Navigate to /chat/[recipient]

### Chat Rendering and Messaging

- Incoming messages are merged by chatroom ID with locally fetched history.
- Message bubbles render sender/receiver alignment and timestamps.
- Sending a message writes to the socket and also adds it locally for optimistic UI.

Message payload shape (from redux slice):

- user_id
- receiver_id
- content
- chatroom_id
- source
- created_at
- id

### Refresh Fallback

If the chat page is refreshed and the recipient is missing from context:

- The page re-derives the recipient ID from the URL.
- It re-fetches chatroom and messages to rehydrate the UI.

## 10) User Profile and Avatar Storage

The /profile page provides:

- Display of user details (id, email, phone)
- Avatar preview and upload via a modal dialog

Avatar storage pipeline:

1. Upload image to Supabase storage bucket talky-chat.
2. Generate a signed URL for display (1 week expiration).
3. Update backend user profile with avatar file path (PUT /users/update).
4. Update Redux user slice with avatar_file_path and avatar_url.

Supabase client uses:

- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY

## 11) Sidebar and Navigation Shell

The app shell provides:

- Sidebar navigation with Dashboard, Chat, Calendar, Search
- User dropdown for account and sign out
- Breadcrumbs based on current path

Sign out calls POST /auth/logout and redirects to /login.

## 12) Styling and Theming

- Tailwind CSS v4 is configured via @import directives in globals.css.
- Colors and radii are defined as CSS variables with light and dark modes.
- next-themes handles class switching for dark mode.

## 13) Environment Variables (Required)

The project expects these environment variables:

- NEXT_PUBLIC_API_URL: base URL for REST API
- NEXT_PUBLIC_WS_URL: WebSocket endpoint
- NEXT_PUBLIC_SUPABASE_URL: Supabase project URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY: Supabase public key

## 14) Build and Run

Common scripts from package.json:

- npm run dev: local development
- npm run build: production build
- npm run start: production server
- npm run lint: linting

## 15) Key Design Choices and Assumptions

- Auth is cookie-based and relies on the API server for refresh tokens.
- Chat is real-time over WebSockets with optimistic UI updates.
- Redux persists user identity but not chat history.
- Supabase is used only for file storage, not for primary auth or DB.

## 16) Known Areas for Future Work

These are implied by the current implementation:

- Protect /chat with middleware or server-side checks (currently commented).
- Add better error surfaces for API failures in chat and profile.
- Implement calendar and search sections in the sidebar.
- Improve global type definitions for User and Chatroom interfaces.

---

End of technical overview.
