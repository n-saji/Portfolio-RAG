# Talky Space 
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


# Talky Space 

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

### Refresh Fallback

If the chat page is refreshed and the recipient is missing from context:

- The page re-derives the recipient ID from the URL.
- It re-fetches chatroom and messages to rehydrate the UI.


## 15) Key Design Choices and Assumptions

- Auth is cookie-based and relies on the API server for refresh tokens.
- Chat is real-time over WebSockets with optimistic UI updates.
- Redux persists user identity but not chat history.
- Supabase is used only for file storage, not for primary auth or DB.


