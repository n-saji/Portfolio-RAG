# Gatekeeper Backend Technical Overview

## 1) Purpose and scope

Gatekeeper is a Node.js authentication API. It provides:

- User signup and user profile management
- Login with access and refresh tokens
- Token refresh flow
- Logout and forced logout support
- Role based admin actions
- Session tracking in Redis to allow server side invalidation

## 2) Tech stack and runtime libraries

From package.json:

- Node.js runtime
- Express 5.x for HTTP server
- Mongoose for MongoDB ODM
- Redis client for session store and pub/sub
- jsonwebtoken for JWT creation and verification
- bcrypt for password hashing
- cookie-parser for httpOnly cookie handling
- cors for cross-origin support
- dotenv for environment config
- uuid for JWT jti values

## 3) Project layout

Top level:

- src/index.js: Express app setup and server bootstrap
- src/config/db.js: MongoDB connection via Mongoose
- src/config/redis.js: Redis connection and session helpers
- src/config/serverEvents.js: Redis pub/sub for force logout events
- src/controllers/*.js: Route handlers
- src/middlewares/authentication.js: Auth and admin authorization middleware
- src/models/user.js: User schema and model
- src/routes/*.js: Express routers
- src/utils/token.js: JWT utilities

## 4) Application bootstrap and request flow

The server starts in src/index.js:

1. Environment variables are loaded from .env.
2. MongoDB connection is established (connectDB).
3. Redis connection is established (connectRedis).
4. Redis pub/sub is set up (connectPublisherSubscriber).
5. Express middleware is registered in this order:
   - CORS with credentials enabled and origin set to CLIENT_URL
   - URL-encoded body parser
   - JSON body parser
   - cookie-parser
   - authenticationMiddleware (applies to most requests)
6. Routes are mounted:
   - /api/users
   - /api/auth
   - /api/admin (with adminAuthorizationMiddleware)
7. Health check and root routes exist:
   - GET /health -> 200 OK
   - GET / -> Welcome message
8. Server listens on PORT.

## 5) Environment configuration

Required variables (from README and code):

- PORT: HTTP server port
- CLIENT_URL: allowed CORS origin (credentials enabled)
- MONGO_URI: MongoDB connection string
- JWT_SECRET: secret used to sign JWT tokens
- REDIS_URL: Redis host
- REDIS_PORT: Redis port
- REDIS_USERNAME, REDIS_PASSWORD: optional Redis auth

Cookies only work across origins if the client sends requests with credentials enabled.

## 6) Authentication model

### 6.1 Token strategy

- Two tokens are issued on login:
  - accessToken (15 minutes)
  - refreshToken (1 day, or 7 days when rememberMe=true)
- Both tokens are stored as httpOnly cookies.
- Each token includes a unique jti (UUID) so sessions can be tracked in Redis.

### 6.2 Session tracking in Redis

Redis acts as a session store to support server side logout:

- A session key is written as session:{userId}:{jti}
- The value stores:
  - ip
  - userAgent
  - lastSeen
- TTL is 15 minutes (matches access token lifetime).
- A per user set tracks active jtis at user:{userId}:sessions.

### 6.3 Access control flow

authenticationMiddleware:

- Skips authentication for:
  - /api/auth/*
  - POST /api/users (signup)
- For all other routes:
  - Reads accessToken cookie
  - Verifies JWT and extracts userId and jti
  - Validates the Redis session by userId and jti
  - Sets req.userId when valid

adminAuthorizationMiddleware:

- Reads req.userId and loads user model
- Allows access only when role is admin

## 7) Token utility behavior

Token helpers in src/utils/token.js:

- createJWTToken(userId, rememberMe)
  - Signs access and refresh tokens using JWT_SECRET
  - Adds exp and jti
  - Returns accessToken, refreshToken, jti

- refreshJWTToken(refreshToken)
  - Verifies refresh token signature
  - Checks exp
  - Issues a new access token with same jti

- verifyJWTTokenAndExtractUserId(token)
  - Verifies signature and exp
  - Returns userId and jti

## 8) Controllers and routes

### 8.1 User routes

Mounted at /api/users:

- GET /api/users
  - Returns current user profile (req.userId)
- POST /api/users
  - Creates a new user (signup)
- PATCH /api/users
  - Updates current user with provided fields
- DELETE /api/users
  - Soft deletes user by setting isActive=false
  - Clears cookies
- GET /api/users/all
  - Returns all users (not filtered by role)

Controller logic:

- Creation validates required fields and writes the user.
- Updates allow changing first_name, last_name, email, password.
- Deletion marks the user as inactive and clears cookies.

### 8.2 Auth routes

Mounted at /api/auth:

- POST /api/auth/login
  - Validates email and password
  - Loads active user and compares bcrypt hash
  - Creates access and refresh tokens
  - Sets httpOnly cookies
  - Creates Redis session with jti

- GET /api/auth/refresh-token
  - Validates refresh token
  - Issues a new access token
  - Creates or refreshes Redis session

- POST /api/auth/logout
  - Validates access token
  - Deletes all Redis sessions for userId
  - Clears accessToken and refreshToken cookies

### 8.3 Admin routes

Mounted at /api/admin with adminAuthorizationMiddleware:

- GET /api/admin/active-sessions
  - Returns all active sessions from Redis

- POST /api/admin/force-logout
  - Deletes sessions for a userId
  - Publishes a force-logout event via Redis pub/sub

- POST /api/admin/promote-user
  - Sets target user role to admin
  - Deletes sessions and publishes force-logout

- POST /api/admin/demote-user
  - Requires caller to be isSuperAdmin
  - Sets target user role to user
  - Deletes sessions and publishes force-logout

## 9) Data model

User model fields (src/models/user.js):

- first_name, last_name: required strings
- email: required, unique, lowercased
- password: required, select: false
- role: enum (user, admin), default user
- isActive: boolean, default true
- isSuperAdmin: boolean, default false
- timestamps: createdAt, updatedAt

Password hashing:

- Pre-save hook hashes password with bcrypt when modified.
- Pre findOneAndUpdate hook hashes new password on update.

## 10) Redis pub/sub for force logout

serverEvents.js sets up a publisher and subscriber using duplicated Redis connections.

- Subscriber listens to channel: force-logout
- On event: reads userId and deletes sessions

This is intended to support multi-instance setups so forced logout propagates to all nodes.

## 11) Security and cookies

- JWTs are stored in httpOnly cookies to prevent JS access.
- CORS allows only CLIENT_URL and sets credentials=true.
- Sessions are validated server side via Redis, which allows immediate invalidation.
- Passwords are never returned by default due to select:false.

## 12) Error handling and logging

- Database and Redis connection errors are logged and cause process exit.
- Most controllers return 4xx for invalid input and 5xx for server errors.
- Authentication middleware returns 401 for missing or invalid tokens and 403 for non-admin access.

## 13) Scripts

- npm run dev: starts server with nodemon
- npm start: starts server with node

## 14) Implementation notes (current behavior)

The following details reflect the current code paths and should be considered when reasoning about runtime behavior:

- Sessions are stored in Redis with keys session:{userId}:{jti} and tracked by set user:{userId}:sessions.
- Access token TTL and Redis session TTL both use 15 minutes.
- Refresh token TTL is 1 day by default or 7 days with rememberMe.
- Force logout uses Redis pub/sub to notify other instances.

If you need additional behavior or consistency checks documented, expand this document with those details.