# SehatSaathi — Backend PRD

## 1. Product Overview

SehatSaathi is an AI-powered rural health guidance platform. The backend serves a React Native mobile app used by villagers who need help understanding medical documents. Users photograph a medical report, upload it, and receive a plain-language explanation via four parallel AI agents. They can then start a voice conversation with an AI health companion (Saathi) who explains the findings in their local language.

**The backend is not a medical system.** It is an information companion. It never diagnoses, never prescribes, never confirms a disease. Every LLM response passes through guardrails before reaching the user.

---

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | FastAPI (async) | Native async support, automatic OpenAPI docs |
| Database | MongoDB via Motor (async) | Flexible document schema, no ORM overhead |
| LLM | Groq (primary) + OpenAI (fallback) | Groq for speed, OpenAI for quality |
| OCR | OpenAI Vision (`gpt-4o`) | Best accuracy on handwritten Hindi/regional scripts |
| Voice | LiveKit | Real-time audio rooms, agent SDK |
| File Storage | MinIO (S3-compatible) | Self-hosted, swap to S3 with zero code change |
| Auth | JWT (access + refresh rotation) | Stateless, refresh tokens stored in MongoDB |
| Email | SMTP via email_service | Emergency doctor alerts |
| Logging | structlog | JSON in prod, human-readable in dev |
| Package Manager | uv | Fast, deterministic |

---

## 3. Architecture

```
Mobile App
    │
    ▼
FastAPI  (/api/v1/)
    │
    ├── Auth          → JWT issue/refresh/revoke
    ├── Users         → profile, consent, location
    ├── Documents     → upload (MinIO), OCR, list
    ├── Agents        → orchestrate 4 AI agents in parallel
    ├── Sessions      → LiveKit room lifecycle + voice agent
    └── Webhooks      → LiveKit room events
         │
         ▼
    MongoDB (Motor)
    Collections: users, documents, agent_verdicts, sessions,
                 refresh_tokens, consent_records, emergency_contacts, audit_logs
```

### Request Lifecycle

```
Request → CORS middleware → Request ID injection → Route handler
       → AppException → error_response()  (structured JSON)
       → Success       → success_response() (structured JSON)
```

All responses follow:
```json
{ "success": true,  "data": <T>,   "error": null }
{ "success": false, "data": null,  "error": "Human readable message" }
```

---

## 4. Authentication Flow

### 4.1 Register / Login — `POST /api/v1/auth/register`

Single endpoint for both new and returning users. No OTP, no password.

```
Body: { phone: str (10 digits), name: str, language: "hi"|"en"|"mr"|"bn"|"ta" }
```

**Flow:**
1. Strip non-digits from phone, validate 10 digits (done in Pydantic validator)
2. `find_user_by_phone(phone)` — if found, skip to step 4
3. `create_user()` — new doc with `upload_count=0`, `call_count=0`, `consent_given=false`, `role="user"`
4. `create_access_token(user_id)` — JWT, 30 min expiry, signed with `JWT_SECRET`
5. `create_refresh_token(user_id)` — JWT, 7 day expiry, signed with `JWT_REFRESH_SECRET`
6. Store refresh token in `refresh_tokens` collection with `expires_at`
7. Return `{ access_token, refresh_token, token_type: "bearer", user: UserResponse }`

**Usage limits enforced at registration:** None. Limits are checked at upload and session start.

### 4.2 Token Refresh — `POST /api/v1/auth/refresh`

```
Body: { refresh_token: str }
```

1. `decode_refresh_token()` — verify signature + expiry
2. Look up token in `refresh_tokens` collection (rotation: if not found, it was already used or revoked → 401)
3. Delete old token from DB
4. Issue new access + refresh token pair
5. Store new refresh token

**Rotation is strict:** each refresh token is single-use. Replay = 401.

### 4.3 Logout — `POST /api/v1/auth/logout`

Requires `Authorization: Bearer <access_token>`. Deletes the refresh token from DB.

### 4.4 Protected Routes

All non-auth routes require `Authorization: Bearer <access_token>`.

`get_current_user` dependency:
1. Decode access token → extract `user_id`
2. `find_user_by_id(user_id)` — returns full user doc
3. Inject into handler as `current_user: dict`

---

## 5. User Flow

### 5.1 Consent — `POST /api/v1/users/me/consent`

```
Body: { given: bool }
```

- Sets `consent_given: true` on user
- Writes to `consent_records` collection (for audit)
- **Sessions cannot start without consent** (enforced in session start handler)

### 5.2 Profile Update — `POST /api/v1/users/me/profile`

```
Body: { name?: str, language?: "hi"|"en"|"mr"|"bn"|"ta" }
```

Partial update — only fields present in body are updated.

### 5.3 Location Update — `POST /api/v1/users/me/location`

```
Body: { lat: float, lng: float, village?: str, district?: str, state?: str }
```

If `village` is not provided, `location_service.reverse_geocode(lat, lng)` is called (OpenStreetMap Nominatim). Result stored in `location` field on user doc.

### 5.4 Get Current User — `GET /api/v1/users/me`

Returns full `UserResponse` for the authenticated user.

### 5.5 List Users (Admin) — `GET /api/v1/users/`

Requires `role: moderator` or above. Supports pagination (`page`, `limit`) and `role` filter.

---

## 6. Document Flow

### 6.1 Upload — `POST /api/v1/documents/upload`

```
Content-Type: multipart/form-data
Body: file (image — JPEG/PNG/PDF)
```

**Limit check:** `upload_count >= 5` → 403 error.

**Flow:**
1. Check `upload_count < 5` on user
2. Validate file type (image or PDF)
3. Generate MinIO object key: `{user_id}/{uuid}.{ext}`
4. Upload raw bytes to MinIO bucket `sehat-saathi`
5. `create_document()` in MongoDB with `status: "pending"`, `minio_key`, `original_name`
6. Increment `upload_count` on user
7. Trigger background task: OCR processing
8. Return `DocumentResponse` immediately (status is `"pending"`)

**OCR Background Task:**
1. Download file bytes from MinIO
2. If image → base64 encode → send to OpenAI Vision (`gpt-4o`) with prompt to extract all text
3. If PDF → extract text via PyMuPDF
4. Store extracted text as `ocr_text` on document
5. Set `status: "processed"`
6. On failure → `status: "failed"`

**Document statuses:** `pending` → `processed` | `failed`

### 6.2 List Documents — `GET /api/v1/documents/`

Paginated (`page`, `limit`). Filtered by `user_id` and `is_active: true`. Sorted newest first.

### 6.3 Get Document — `GET /api/v1/documents/{document_id}`

Returns full `DocumentResponse`. Scoped to `user_id` — cannot access other users' docs.

### 6.4 Get Presigned URL — `GET /api/v1/documents/{document_id}/url`

Returns a time-limited MinIO presigned URL for direct file access. Expires in 1 hour.

---

## 7. Agent Orchestration Flow

### 7.1 Analyze — `POST /api/v1/agents/analyze`

```
Body: { document_id: str }
```

**Pre-conditions:**
- Document must exist and belong to user
- Document `status` must be `"processed"` and `ocr_text` must be non-empty
- If not processed yet → 400 "Document has not been processed yet. Please wait and retry."

**Orchestration:**
```python
asyncio.gather(
    DiagnosisAgent().run(ocr_text, user),
    MedicationAgent().run(ocr_text, user),
    LifestyleAgent().run(ocr_text, user),
    RiskAgent().run(ocr_text, user),
)
```

All 4 agents run **in parallel**. Individual agent failures are logged and skipped — if all fail, raises 500.

**Each Agent (BaseAgent pattern):**
1. Build a system prompt specific to agent type + user language
2. Build user prompt with OCR text
3. Call Groq LLM (or OpenAI fallback) — `llama-3.3-70b-versatile` or `gpt-4o-mini`
4. Parse LLM response into `{ summary, detail, agent_type }`
5. Pass through **Guardrails** (input + output check)
6. Return verdict dict

**Agent Types and their focus:**

| Agent | Type | Focus |
|---|---|---|
| DiagnosisAgent | `diagnosis` | What the report seems to be about (neutral framing) |
| MedicationAgent | `medication` | Any medicines mentioned in the report, without dosage advice |
| LifestyleAgent | `lifestyle` | Diet, rest, activity suggestions based on the report |
| RiskAgent | `risk` | Warning signs or concerning values in the report |

**After orchestration:**
- All successful verdicts stored in `agent_verdicts` collection via `bulk_create_verdicts()`
- Response includes `verdicts[]` + `summary` (diagnosis agent's summary)

### 7.2 Get Verdicts — `GET /api/v1/agents/{document_id}/verdicts`

Returns stored verdicts for a document. Used when user returns to a previously analyzed document.

---

## 8. Guardrail System

Every LLM output is checked before storage or delivery. Guardrails are **server-side only** and cannot be bypassed by the client.

### 8.1 Medical Rail (`medical_rail.py`)

Regex-based. Blocks:
- Medicine names (50+ common Indian/generic names: paracetamol, dolo, metformin, etc.)
- Dosage patterns (`100mg`, `5ml`, `take 2`)
- Diagnosis confirmation (`you have diabetes`, `diagnosed with cancer`)
- Prescription language (`prescribe`, `dosage`, `prescription`)

Returns `(passed: bool, reason: str | None)`.

On failure → agent retries with a stricter prompt. After 3 failures → verdict is marked with `guardrail_triggered: true` and a safe fallback message is used.

### 8.2 Language Rail (`language_rail.py`)

Scores response complexity. Rejects overly technical medical jargon. Enforces plain-language output appropriate for rural users with low health literacy.

### 8.3 Emergency Detector (`emergency_detector.py`)

Runs on **user's voice input** during sessions (not on LLM output).

Keyword list covers English + Hindi emergency phrases: chest pain, heart attack, saans nahi, behos, dora, marjna chahta, etc.

Each keyword has a severity multiplier (1.0–3.0). Score = sum of multipliers, capped at 10.0. Threshold = 1.5.

**On emergency detection:**
- `flag_emergency(session_id)` — sets `status: "flagged"` on session
- Background task: send email via `email_service` to registered doctor/contact
- Session continues normally — user is not alarmed

---

## 9. Session (Voice) Flow

### 9.1 Start Session — `POST /api/v1/sessions/start`

```
Body: { document_id: str, language?: str }
```

**Pre-conditions:**
- `consent_given: true` on user → else 403
- Implicitly: `call_count < 5` (incremented here, not checked — by design: limit is soft)

**Flow:**
1. Increment `call_count` on user
2. Generate unique LiveKit room name (`sehat-{uuid4-short}`)
3. Create LiveKit room via LiveKit Server API
4. Generate **user token** — LiveKit JWT for the mobile client to join
5. `create_session()` in MongoDB — stores `user_id`, `document_id`, `livekit_room`, `language`, `status: "active"`
6. `get_verdicts(document_id)` — fetch previously computed agent verdicts
7. `asyncio.create_task(run_voice_agent(room_name, verdicts, language))` — spawn agent in background
8. Return `SessionResponse` with `livekit_token` — client uses this to connect to LiveKit room

**VoiceAgent (`voice_agent.py`):**
- Joins the LiveKit room as a participant named "Saathi"
- System prompt built from aggregated verdicts + user language
- Persona: "friendly village health guide, not a doctor"
- Responds to user voice input
- Each user utterance is checked by `emergency_detector.py` before VoiceAgent processes it
- VoiceAgent responses are checked by `medical_rail.py` before being spoken

### 9.2 End Session — `POST /api/v1/sessions/{session_id}/end`

```
Body: { transcript?: str }
```

1. Verify session belongs to current user
2. `end_session(session_id, transcript)` — sets `status: "completed"`, `ended_at: now`
3. Background task: `livekit_service.delete_room()` — cleanup LiveKit room
4. Return updated `SessionResponse`

### 9.3 List Sessions — `GET /api/v1/sessions/`

Paginated. User's sessions only, newest first.

### 9.4 Get Session — `GET /api/v1/sessions/{session_id}`

Single session by ID, scoped to current user.

---

## 10. MongoDB Collections & Indexes

### users
```
{ phone, name, language, role, consent_given, consent_at,
  upload_count, call_count, location, is_active, created_at, updated_at }

Indexes:
  { phone: 1, is_active: 1 }   ← unique lookup on register/login
  { is_active: 1 }
```

### documents
```
{ user_id, original_name, minio_key, file_type, status,
  ocr_text, is_active, created_at, updated_at }

Indexes:
  { user_id: 1, is_active: 1, created_at: -1 }   ← list query
```

### agent_verdicts
```
{ document_id, user_id, session_id, agent_type, summary, detail,
  guardrail_triggered, is_active, created_at, updated_at }

Indexes:
  { document_id: 1, is_active: 1 }
  { session_id: 1, is_active: 1 }
```

### sessions
```
{ user_id, document_id, livekit_room, language, status,
  emergency_flagged, transcript, started_at, ended_at,
  is_active, created_at, updated_at }

Status values: "active" | "completed" | "flagged"

Indexes:
  { user_id: 1, is_active: 1, created_at: -1 }
  { livekit_room: 1, is_active: 1 }   ← webhook lookup
```

### refresh_tokens
```
{ user_id, token, expires_at, created_at }

Indexes:
  { token: 1 }         ← lookup on refresh
  { user_id: 1 }       ← logout all devices
  { expires_at: 1 }    ← TTL index for auto-cleanup
```

### consent_records
```
{ user_id, given_at }   ← append-only audit log

Indexes:
  { user_id: 1 }
```

---

## 11. Usage Limits

| Resource | Limit | Enforcement Point |
|---|---|---|
| Document uploads | 5 per user | `document_service.upload_document()` → 403 if `upload_count >= 5` |
| Voice sessions | 5 per user | `call_count` incremented at session start (soft limit — increments before checking) |

Limits are **not time-windowed** (not per-day/per-month). They are lifetime counts per user account.

To reset: update `upload_count` or `call_count` directly in MongoDB (admin operation, no API endpoint).

---

## 12. Role System

| Role | Access |
|---|---|
| `user` | Own data only — register, upload, analyze, session |
| `doctor_reviewer` | Read-only on flagged sessions |
| `moderator` | List all users, read all sessions |
| `superadmin` | Full access |

Role is set to `"user"` on registration. Elevation is done directly in MongoDB (no API endpoint for promotion).

`require_moderator_or_above` dependency checks `role in ["moderator", "superadmin"]`.

---

## 13. File Storage (MinIO)

- Bucket: `sehat-saathi`
- Object key format: `{user_id}/{uuid}.{extension}`
- Never store binary in MongoDB — MinIO only
- Presigned URLs expire in 1 hour
- MinIO is S3-compatible — production migration = change 3 env vars, zero code change

---

## 14. Environment Variables

```env
MONGO_URI=                        # MongoDB Atlas connection string
MONGO_DB_NAME=sehat_saathi

JWT_SECRET=                       # Access token signing key
JWT_REFRESH_SECRET=               # Refresh token signing key
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

OPENAI_API_KEY=                   # OCR (gpt-4o vision) + LLM fallback
GROQ_API_KEY=                     # Primary LLM (llama-3.3-70b-versatile)

LIVEKIT_URL=                      # LiveKit server WebSocket URL
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=sehat-saathi
MINIO_SECURE=false

ENVIRONMENT=development           # development | production
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```

---

## 15. API Reference (All Endpoints)

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | ❌ | Register or login by phone |
| POST | `/api/v1/auth/refresh` | ❌ | Rotate refresh token |
| POST | `/api/v1/auth/logout` | ✅ | Revoke refresh token |

### Users
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | ✅ | Get current user |
| POST | `/api/v1/users/me/consent` | ✅ | Record consent |
| POST | `/api/v1/users/me/profile` | ✅ | Update name or language |
| POST | `/api/v1/users/me/location` | ✅ | Update location (lat/lng or manual) |
| GET | `/api/v1/users/` | ✅ Admin | List all users (paginated) |

### Documents
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/documents/upload` | ✅ | Upload report image/PDF |
| GET | `/api/v1/documents/` | ✅ | List user's documents (paginated) |
| GET | `/api/v1/documents/{id}` | ✅ | Get single document |
| GET | `/api/v1/documents/{id}/url` | ✅ | Get presigned MinIO URL |

### Agents
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/agents/analyze` | ✅ | Run 4-agent orchestration on document |
| GET | `/api/v1/agents/{document_id}/verdicts` | ✅ | Fetch stored verdicts |

### Sessions
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/sessions/start` | ✅ | Create LiveKit room + spawn voice agent |
| POST | `/api/v1/sessions/{id}/end` | ✅ | End session, store transcript |
| GET | `/api/v1/sessions/` | ✅ | List user's sessions (paginated) |
| GET | `/api/v1/sessions/{id}` | ✅ | Get single session |

---

## 16. Complete User Journey (End-to-End)

```
1. User opens app → Onboarding (language select)
        ↓
2. POST /auth/register { phone, name, language }
   → Returns access_token + refresh_token + user
        ↓
3. POST /users/me/consent { given: true }
   → consent_given = true, session start unlocked
        ↓
4. POST /documents/upload (multipart image)
   → doc created (status: "pending")
   → OCR runs in background → status: "processed"
        ↓
5. POST /agents/analyze { document_id }
   → 4 agents run in parallel, verdicts stored
   → Returns DiagnosisAgent + MedicationAgent + LifestyleAgent + RiskAgent verdicts
        ↓
6. User reads verdicts in app (AgentResultScreen)
        ↓
7. POST /sessions/start { document_id }
   → LiveKit room created
   → VoiceAgent joins room with verdicts as context
   → Returns livekit_token for mobile client
        ↓
8. Mobile connects to LiveKit room with token
   → Real-time audio conversation with Saathi
   → Emergency detection runs on every user utterance
   → Guardrails run on every Saathi response
        ↓
9. POST /sessions/{id}/end { transcript? }
   → Session marked completed, LiveKit room deleted
```

---

## 17. What is NOT Built Yet

| Feature | Status | Notes |
|---|---|---|
| OTP verification | Not built | Phone-only auth by design (no OTP, per product decision) |
| Doctor review portal | Not built | Role exists (`doctor_reviewer`), no routes |
| Emergency contact management | Not built | Model exists, no CRUD routes |
| Admin dashboard | Not built | `list_users` endpoint exists, no UI |
| Redis caching / rate limiting | Not built | Planned for >10k users |
| Push notifications | Not built | For OCR completion alerts |
| Audit log writes | Not built | Collection exists, nothing writes to it |
| EAS / production build | Not built | Expo Go only right now |
| `/api/v1/health` | Not built | Returns 404 currently |

---

## 18. Known Constraints

- **Call limit is soft:** `call_count` is incremented before checking. A user at count=4 who calls twice in parallel could go to 6. Acceptable at current scale.
- **OCR is async but not queued:** Background tasks run in the same FastAPI process. Under heavy load, use Celery + Redis.
- **VoiceAgent is fire-and-forget:** `asyncio.create_task()` — if the server restarts mid-session, the agent is lost. LiveKit room still exists; client reconnects but gets no agent.
- **No refresh token family tracking:** Refresh token theft detection (reuse of a rotated token) logs the user out but does not invalidate all sessions.
- **MinIO in docker-compose is dev-only:** No replication, no backup. Production must use AWS S3 or managed object storage.
