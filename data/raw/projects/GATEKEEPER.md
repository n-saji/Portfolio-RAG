# Gatekeeper Technical Overview

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


## 3) Application bootstrap and request flow

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


## 4) Authentication model

### 4.1 Token strategy

- Two tokens are issued on login:
  - accessToken (15 minutes)
  - refreshToken (1 day, or 7 days when rememberMe=true)
- Both tokens are stored as httpOnly cookies.
- Each token includes a unique jti (UUID) so sessions can be tracked in Redis.

### 4.2 Session tracking in Redis

Redis acts as a session store to support server side logout:

- A session key is written as session:{userId}:{jti}
- The value stores:
  - ip
  - userAgent
  - lastSeen
- TTL is 15 minutes (matches access token lifetime).
- A per user set tracks active jtis at user:{userId}:sessions.

### 4.3 Access control flow

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


## 5) Redis pub/sub for force logout

serverEvents.js sets up a publisher and subscriber using duplicated Redis connections.

- Subscriber listens to channel: force-logout
- On event: reads userId and deletes sessions

This is intended to support multi-instance setups so forced logout propagates to all nodes.

## 6) Security and cookies

- JWTs are stored in httpOnly cookies to prevent JS access.
- CORS allows only CLIENT_URL and sets credentials=true.
- Sessions are validated server side via Redis, which allows immediate invalidation.
- Passwords are never returned by default due to select:false.
