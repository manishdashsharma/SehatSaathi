# SehatSaathi — CLAUDE.md

## Project Identity

**Name:** SehatSaathi  
**Mission:** AI-powered rural health guidance platform — a personal health companion for villagers that explains medical documents in simple language using voice, multi-agent AI, and guardrailed responses.  
**Stack:** FastAPI · MongoDB · Groq · OpenAI · LiveKit · Guardrails AI · React Native (App)

---

## Monorepo Structure

```
sehat-saathi/
├── CLAUDE.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini                        # Not used (MongoDB), reserved for future SQL needs
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── sessions.py
│   │   │   │   ├── agents.py
│   │   │   │   └── webhooks.py
│   │   │
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   ├── dependencies.py
│   │   │   ├── exceptions.py
│   │   │   ├── middleware.py
│   │   │   └── logging.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── session.py
│   │   │   ├── agent_verdict.py
│   │   │   └── emergency_contact.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── session.py
│   │   │   └── agent.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── document_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── agent_orchestrator.py
│   │   │   ├── livekit_service.py
│   │   │   ├── email_service.py
│   │   │   ├── guardrail_service.py
│   │   │   └── location_service.py
│   │   │
│   │   ├── agents/
│   │   │   ├── base_agent.py
│   │   │   ├── diagnosis_agent.py
│   │   │   ├── medication_agent.py
│   │   │   ├── lifestyle_agent.py
│   │   │   ├── risk_agent.py
│   │   │   └── voice_agent.py
│   │   │
│   │   ├── guardrails/
│   │   │   ├── medical_rail.py
│   │   │   ├── language_rail.py
│   │   │   └── emergency_detector.py
│   │   │
│   │   └── utils/
│   │       ├── file_utils.py
│   │       ├── language_utils.py
│   │       └── response_utils.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_documents.py
│       ├── test_agents.py
│       └── test_guardrails.py
│
│
├── app/                                   # React Native — Expo
│   ├── package.json
│   ├── app.json
│   ├── tsconfig.json
│   ├── babel.config.js
│   │
│   └── src/
│       ├── navigation/
│       │   ├── RootNavigator.tsx
│       │   ├── AuthNavigator.tsx
│       │   └── MainNavigator.tsx
│       │
│       ├── screens/
│       │   ├── auth/
│       │   │   ├── SplashScreen.tsx
│       │   │   ├── ConsentScreen.tsx
│       │   │   ├── RegisterScreen.tsx
│       │   │   └── OtpScreen.tsx
│       │   │
│       │   ├── main/
│       │   │   ├── HomeScreen.tsx
│       │   │   ├── UploadScreen.tsx
│       │   │   ├── AgentResultScreen.tsx
│       │   │   ├── VoiceSessionScreen.tsx
│       │   │   └── ProfileScreen.tsx
│       │   │
│       │   └── emergency/
│       │       └── EmergencyContactScreen.tsx
│       │
│       ├── components/
│       │   ├── DocumentPicker.tsx
│       │   ├── AgentVerdictCard.tsx
│       │   ├── VoiceWaveform.tsx
│       │   ├── LanguagePicker.tsx
│       │   └── GuardrailBanner.tsx
│       │
│       ├── services/
│       │   ├── api.service.ts
│       │   ├── livekit.service.ts
│       │   ├── location.service.ts
│       │   └── storage.service.ts
│       │
│       ├── store/
│       │   ├── index.ts
│       │   ├── authSlice.ts
│       │   └── sessionSlice.ts
│       │
│       ├── hooks/
│       │   ├── useLocation.ts
│       │   ├── useLiveKit.ts
│       │   └── useLanguage.ts
│       │
│       ├── i18n/
│       │   ├── index.ts
│       │   ├── hi.json
│       │   ├── en.json
│       │   ├── mr.json
│       │   ├── bn.json
│       │   └── ta.json
│       │
│       └── types/
│           ├── navigation.types.ts
│           └── api.types.ts
│
└── session/
    ├── README.md
    └── 2026-06-27.md                      # Auto-generated per session
```

---

## Architecture Principles

### Backend
- Package management via `uv` — never use pip or poetry
- FastAPI with async throughout — no sync DB calls, no sync I/O
- MongoDB via `motor` (async driver) — no ODM overhead, raw collections with Pydantic validation at schema layer
- Repository pattern: services never touch DB directly — all DB ops go through model layer
- All endpoints versioned under `/api/v1/`
- JWT auth with refresh token rotation
- Background tasks via FastAPI `BackgroundTasks` for email, post-session writes
- Structured logging with `structlog` — JSON in production, human-readable in dev
- All secrets from environment — zero hardcoded values anywhere

### Multi-Agent Orchestration
- `agent_orchestrator.py` fans out to 4 agents in parallel using `asyncio.gather`
- Each agent is stateless and receives the same document context + user profile
- Agents: `DiagnosisAgent`, `MedicationAgent`, `LifestyleAgent`, `RiskAgent`
- All agents return a typed `AgentVerdict` schema
- Verdicts are aggregated, stored in MongoDB, then passed to `VoiceAgent`

### Guardrails
- `guardrail_service.py` wraps every LLM call — input and output
- `medical_rail.py`: blocks medicine names, dosage suggestions, diagnosis confirmation
- `language_rail.py`: enforces simple vocabulary scoring, rejects jargon
- `emergency_detector.py`: keyword + semantic scoring — triggers email to doctor if threshold breached
- Guardrails run server-side only — never bypass from client

### LiveKit Voice Agent
- `livekit_service.py` creates a room per session
- `voice_agent.py` joins as a participant with system prompt loaded from aggregated verdicts
- Voice agent persona: friendly village health guide, never a doctor
- Session transcript stored post-call, flagged for emergency review if needed

### MongoDB Collections
```
users
documents
agent_verdicts
sessions
emergency_contacts
audit_logs
consent_records
```

### React Native App
- Expo managed workflow with EAS Build for production
- i18n via `i18next` + `react-i18next` — 5 languages at launch
- LiveKit SDK integrated in `VoiceSessionScreen`
- Location via `expo-location` — permission gated, stored encrypted
- Document upload via `expo-document-picker` + `expo-image-picker`
- Zustand for state — no Redux overhead in mobile

---

## Environment Variables

```env
MONGO_URI=
MONGO_DB_NAME=sehat_saathi

JWT_SECRET=
JWT_REFRESH_SECRET=
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

OPENAI_API_KEY=
GROQ_API_KEY=

LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

GUARDRAILS_API_KEY=

MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=sehat-saathi
MINIO_SECURE=false

ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```

---

## Session File Convention

Every Claude session must append a file at `session/YYYY-MM-DD.md` with:

```md
# Session — YYYY-MM-DD

## Work Done
- <bullet per task completed>

## Decisions Made
- <architectural or product decisions>

## Files Created / Modified
- <path> — <one line reason>

## Pending / Next
- <what remains>
```

If a file for today already exists, append a new `## Session N` block — do not overwrite.

---

## Code Rules (Non-Negotiable)

- Zero comments in code — self-documenting names only
- No `print()` — use structured logger
- No `any` type in TypeScript — strict mode always on
- No inline styles in React / React Native — styled components or NativeWind only
- All API responses follow: `{ success: bool, data: T | null, error: str | null }`
- All errors are caught at service layer — routes never throw raw exceptions
- Every new route gets a corresponding test
- Migration scripts go in `backend/scripts/migrations/`
- Secrets never logged, never returned in API responses

---

## Git Conventions

```
feat:     new feature
fix:      bug fix
refactor: code restructure, no behavior change
chore:    deps, config, tooling
docs:     documentation only
test:     test additions or fixes
```

Branch naming: `feat/voice-agent-integration`, `fix/guardrail-medication-block`

---

## Scaling Considerations

- Agent orchestration is async — horizontally scalable via multiple FastAPI workers
- MongoDB indexes defined at startup in `database.py` — compound indexes on `user_id + created_at` for all collections
- LiveKit rooms isolated per session — no shared state between users
- MinIO for all file storage — never store binary in MongoDB; S3-compatible API so migration to real S3 is a config swap
- Redis to be introduced for session caching and rate limiting when user base > 10k

---

## Languages Supported at Launch

| Code | Language   |
|------|------------|
| hi   | Hindi      |
| en   | English    |
| mr   | Marathi    |
| bn   | Bengali    |
| ta   | Tamil      |

Voice agent language is auto-detected from user profile preference. Falls back to Hindi.

---

## Guardrail Hard Rules

1. Never suggest a medicine by name
2. Never confirm or deny a diagnosis
3. Never give dosage instructions
4. Always recommend consulting a real doctor for serious concerns
5. If emergency keywords detected → trigger doctor email silently, continue session normally
6. Simple language score must be above threshold before response is sent to user
