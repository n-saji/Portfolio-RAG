# University Portal 

## 1. Purpose and Scope

The project is a Golang backend for a University / College Administration Portal. It provides CRUD and workflow APIs for:
- Courses
- Students (details, marks, ranking)
- Instructor profiles and login credentials
- Account management and verification (OTP-based)
- Authentication and token management
- Messaging and notifications (database backed with WebSocket delivery)

It is primarily a REST API built with Gin, with a small gRPC schema definition. The service uses PostgreSQL for persistence and Goose migrations for schema management.

## 2. High-Level Architecture

### 2.1 Runtime Flow (main.go)
Startup sequence:
1. Load configuration and environment variables.
2. Open database connection (GORM).
3. Run Goose migrations from embedded SQL files.
4. Build HTTP handlers and router.
5. Start background goroutines:
   - WebSocket broadcast loop.
   - Cron scheduler for periodic jobs.
6. Start the HTTP server.

Key runtime components:
- Gin HTTP server for REST endpoints.
- GORM for ORM and database access.
- Goose for DB migrations.
- Cron (robfig/cron) for background tasks.
- Gorilla WebSocket for realtime notifications.

### 2.2 Layering
The code follows a layered structure:
- Handlers (HTTP layer) validate tokens, parse input, format responses.
- Service (business layer) applies validation and business rules.
- Daos (data access layer) encapsulate GORM queries.
- Models define data schemas and JSONB structures.
- Utils provide email, WebSocket, token, OTP and request helpers.

### 2.3 Background Jobs and Cron
Two cron jobs are scheduled:
- RunDailyMigrations: cleans expired tokens in two steps.
- SendMessages: periodically pushes pending messages to connected clients.

### 2.4 WebSockets
WebSocket support is built using Gorilla WebSocket. The service keeps:
- A map of live connections.
- A map from account ID to connection.
Messages can be sent as:
- Broadcasts to all connected clients.
- Targeted messages to a specific account ID.

## 4. Dependency Stack

Core libraries:
- gin-gonic/gin: HTTP server framework.
- gorm.io/gorm and gorm.io/driver/postgres: ORM and PostgreSQL driver.
- pressly/goose: migrations.
- gorilla/websocket: WebSocket handling.
- mailgun-go: outbound email.
- google/uuid: UUID generation.
- robfig/cron: scheduled tasks.
- grpc and protobuf libraries (proto definitions are included).

## 5. Data Model and Database Schema

### 5.1 Core Tables
The schema is defined via Goose migrations:

1) course_infos
- id (uuid, PK)
- course_name (text)
- Seed data includes "No Course" and a default catalog of courses.

2) student_marks
- id (uuid, PK)
- student_id (uuid)
- course_id (uuid)
- course_name (text)
- marks (numeric)
- grade (text)

3) student_infos
- id (uuid, PK)
- name (text)
- roll_number (text)
- age (numeric)
- course_id (uuid, FK -> course_infos.id)
- marks_id (uuid, FK -> student_marks.id)

4) instructor_details
- id (uuid, PK)
- instructor_code (text)
- instructor_name (text)
- department (text)
- course_id (uuid, FK -> course_infos.id)
- info (jsonb) [added later] for embedded student list.

5) instructor_logins
- id (uuid, PK)
- email_id (text)
- password (text)

6) token_generators
- token (uuid, PK)
- valid_from (numeric)
- valid_till (numeric)
- is_valid (boolean)
- account_id (uuid, FK -> accounts.id)

7) accounts
- id (uuid, PK)
- name (varchar)
- info (jsonb) contains credentials and related account info
- type (varchar) [instructor or student]
- verified (boolean)

8) messages
- id (uuid, PK)
- account_id (uuid)
- messages (varchar)
- is_read (boolean)
- title (varchar)
- author (varchar)
- created_at (numeric)

9) otps
- id (uuid, PK)
- account_id (uuid)
- email_id (varchar)
- otp_code (varchar)
- created_at (numeric)
- expires_at (numeric)
- is_used (boolean)

### 5.2 JSONB Structures
The service stores nested structures as JSONB:
- InstructorDetails.Info -> Instructor_Info with StudentsList
- Accounts.Info -> Account_Info with Credentials

### 5.3 Triggers and Data Hygiene
Migrations add database triggers:
- Default grade setup after insert into student_infos.
- Cleanup of student_marks after student deletion.
- Cleanup of instructor_logins after instructor deletion.
- Cleanup of accounts when related student or instructor is deleted.

### 5.4 Migration Timeline Summary
Key migrations in chronological order:
- Create course_infos and seed courses.
- Create student_marks, student_infos, instructor_details, instructor_logins.
- Create token_generators for auth.
- Add triggers for default grade and cleanup on delete.
- Add info jsonb field to instructor_details.
- Create accounts table and deletion triggers.
- Add type and verified fields to accounts.
- Create messages table and expand with title/author/created_at.
- Link token_generators to accounts with foreign key.
- Add otps table for account verification.

## 6. HTTP API Surface

Routes are defined in the router initialization. The API assumes a token (header Token or cookie token) for most endpoints, enforced by the service layer.

### 6.1 Course APIs
- POST /insert-course
  - Create new course with validation (unique course name).
- GET /retrieve-all-courses
  - List all courses.
- PATCH /update-course/:name
  - Rename course; cascades updates to instructor records and student marks.
- DELETE /delete-course/:courseName
  - Delete course if no instructor uses it; falls back to remote fetch on error.

### 6.2 Student APIs
- POST /insert-student-details
  - Create student details and create student_marks row.
- GET /retrieve-college-administration
  - List students; supports ordering by query param.
- DELETE /delete-student-info/:id
  - Remove student by UUID.
- PATCH /update-student-name-and-age/:name
  - Update name and age for all matching students.
- GET /find-all-course-for-student/:name
  - Return all courses and marks for a student.
- DELETE /delete-student-course/:name/:course
  - Remove a student from a specific course.
- GET /get-ranking/:coursename
  - Rank students by marks for a course.
- GET /get-student-name-course
  - Return selective fields (name, roll, course) only.
- DELETE /delete-student
  - Delete students by flexible criteria (JSON body).
- PATCH /v2/update-student-details
  - Update student detail by ID (v2 variant).

### 6.3 Instructor APIs
- POST /insert-instructor-details
  - Create instructor details and account, attach student list for course.
- GET /retrieve-instructors
  - List instructors.
- GET /retrieve-instructors/:order_by
  - List instructors ordered by fields or students count.
- GET /instructor-login-with-id/:instructorId/:emailId/:password
  - Create instructor login and issue auth token.
- PATCH /update-instructor
  - Update instructor attributes based on query parameters.
- DELETE /admins/:aid/delete-instructor
  - Admin delete by condition, cleans messages, logins, tokens.
- GET /get-instructor-name-by-id/:id
  - Fetch instructor details by ID.
- GET /view-profile-instructor/:id
  - Assemble profile with login credentials.

### 6.4 Authentication and Account APIs
- POST /v1/login
  - Validate login and issue token.
- GET /logout
  - Disable token.
- GET /check-token-status
  - Validate token.
- POST /create-account
  - Create account and base instructor detail + login, send OTP.
- GET /send-otp-email
  - Generate OTP and send to email.
- GET /verify-otp
  - Verify OTP and mark account as verified.
- POST /send-reset-password-mail
  - Generate reset token and email reset link.
- POST /reset-password
  - Reset password using token and invalidate existing tokens.

### 6.5 Messaging and WebSocket APIs
- GET /ws/:id
  - WebSocket connection for account ID.
- GET /read-message/:id
  - Mark messages as read for account ID.
- GET /send-test-message
  - Broadcast test messages.

### 6.6 Health and Test
- GET /ping
- GET /health

## 7. Business Rules and Data Integrity

Major rules enforced in service layer:
- Course names must be unique and non-empty.
- Student names must not be numeric; age must be positive.
- Student marks must be <= 100, and grade is derived.
- A student cannot duplicate a course entry.
- Instructor department and name must be non-numeric and avoid '-'.
- Login email must be valid format and password must be >= 8 characters.
- Tokens are time-bound and invalidated on expiry or logout.

## 8. Authentication and Token Management

Token flow:
- After login, a token is created in token_generators with validity window.
- Token is returned in response headers and cookies.
- Each authenticated API checks token validity and expiry.
- Cron job runs every 10 minutes to mark expired tokens invalid and then delete them.

Account verification:
- Account creation triggers OTP email.
- OTP is stored in otps table with expiration.
- Verify OTP sets account verified flag.

Reset password flow:
- Reset password token stored in token_generators with 15-minute validity.
- Successful reset invalidates all tokens for that account.

## 9. Messaging and Notifications

Messages are stored in the messages table. Delivery behavior:
- StoreMessages inserts a message per recipient (accounts by type).
- A periodic job pulls unread messages and pushes them to WebSocket clients.
- After sending, message status is marked as read.

Messages can be system-originated (author "System") or instructor-originated.

## 10. Email Workflows

Emails are sent via Mailgun:
- OTP email for account verification uses a template.
- Reset password email sends a link to FRONTEND_URL.

## 11. gRPC Contract

The proto defines a minimal gRPC service:
- Administration.CreateCourse(CourseInfo) returns Res.
- Additional messages define CourseInfo, StudentInfo, StudentMarks, InstructorDetails.

The gRPC implementation is not shown in the code listing but the contract exists.

## 12. Deployment and Runtime

### 12.1 Docker
- Dockerfile builds the Go binary and exposes port 5050.
- docker-compose.yml builds and runs the service with env vars.

### 12.2 HTTP Ports
- The Gin server runs on PORT (env). Docker maps 5050 and 8080.

## 13. Notable Implementation Details

- WebSocket connections are stored in maps guarded by a mutex.
- Default grade is set via a trigger, not in application logic.
- JSONB fields are used for nested structures (students list and credentials).
- Auto-migrate is disabled in favor of Goose migrations.

## 14. Summary of Project Capabilities

The project delivers a full-featured backend for course, student, and instructor administration, including authentication, account verification, messaging, and real-time updates. The architecture is organized around clear layers (handlers, services, daos), and the database is governed by explicit migrations and triggers to keep data consistent.
