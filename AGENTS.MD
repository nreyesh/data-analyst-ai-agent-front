# Frontend Engineering, Security & Agent Architecture Guide

This document defines the architectural guidelines, authentication flows, environment profiling standards, and GitFlow practices for the **Building Analytics Frontend** service (`nreyesh/front`).

Any human engineer or AI coding assistant modifying this repository must adhere to the patterns documented below.

---

## 1. Architectural Philosophy & Decoupling

The frontend is a **pure client presentation tier**. 

### The Fundamental Separation Rule:
* **The frontend knows NOTHING about internal AI logic, LangGraph nodes, SQL queries, or database credentials.**
* The frontend communicates with the backend exclusively over **HTTPS JSON REST APIs** using `front/api_client.py`.
* Never import `agent.*` or backend dependencies into this repository.

```
┌──────────────────────────────────────┐
│ FRONTEND (Chainlit Web UI)           │
│ • Renders chat UI and components     │
│ • Authenticates via Firebase Auth    │
│ • Passes Bearer token to backend     │
└──────────────────┬───────────────────┘
                   │ HTTPS JSON
                   ▼
┌──────────────────────────────────────┐
│ BACKEND (Cloud Run Private Service)  │
│ • Validates Bearer token             │
│ • Runs LangGraph AI Supervisor       │
│ • Connects to Cloud SQL Postgres     │
└──────────────────────────────────────┘
```

---

## 2. Environment Profile Configuration Pattern

Configuration is decoupled from code using YAML profiles located in `front/profile/`:

* `profile/application.yaml`: Common defaults (ports, timeouts, auth endpoints).
* `profile/application-dev.yaml`: Development configuration:
  * Backend URL: `https://building-analytics-backend-dev.a.run.app`
  * Firebase Project: `building-analytics-dev-513719`
  * Dev mock accounts permitted for local testing when offline.
* `profile/application-prod.yaml`: Production configuration:
  * Backend URL: `https://building-analytics-backend-prod.a.run.app`
  * Firebase Project: `building-analytics-prod`
  * Mock accounts **STRICTLY FORBIDDEN**.

### Precedence Hierarchy:
1. **Environment Variables** (e.g. `BACKEND_URL`, `FIREBASE_WEB_API_KEY`) have **highest precedence**.
2. **`application-${ENVIRONMENT}.yaml`** overrides base defaults.
3. **`application.yaml`** defines baseline fallbacks.

> **Zero Secrets in Git:** Never commit API keys, service account credentials, or passwords into YAML files. All secrets must be injected at runtime via Google Cloud Secret Manager or Cloud Run environment variables.

---

## 3. Authentication & Security Architecture

### Google Identity Toolkit (Firebase Auth)
Authentication is handled entirely via Firebase Auth (Google Identity Toolkit):
1. **Client-Side Login:** The user enters their email and password into Chainlit's login dialog.
2. **Credential Verification:** `front/auth.py` calls the Firebase endpoint:
   `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_WEB_API_KEY}`
3. **Token Receipt:** Google returns a signed, short-lived JWT `idToken` (valid for 1 hour).
4. **Session Storage:** The `idToken` is stored in Chainlit's server-side user session (`cl.user_session.set("id_token", ...)`).
5. **Backend Propagation:** Every outgoing API request to the backend includes:
   `Authorization: Bearer <idToken>`

### Multi-Tenancy & Authorization:
* The frontend **never decides permissions**. 
* The backend verifies the cryptographic signature of the token and checks the user's role (`admin` or `resident`).
* The frontend simply renders the UI state returned by the backend.

---

## 4. Contract Validation: Why `models.py` Exists

The frontend uses lightweight **Pydantic schemas** in `front/models.py` (`UserContext`, `FocusContext`, `SupervisorTurnResult`):
* **Fails Fast:** If the backend changes a schema unexpectedly, Pydantic produces a descriptive log instead of crashing on the user's screen with `KeyError`.
* **Zero Heavy Dependencies:** These schemas contain no LangChain, PyTorch, or database drivers, keeping the container image small (~180 MB).

---

## 5. GitFlow & Branching Standards

This repository follows strict **GitFlow** conventions:

```
[ Feature / Bugfix Branch ]
            │
            ▼ (Pull Request)
       [ dev ] ──────────────► Deploys to Google Cloud DEV Project
            │
            ▼ (Tested & Approved Pull Request)
      [ main ] ──────────────► Deploys to Google Cloud PROD Project
```

1. **`dev` Branch:**
   * Active integration branch.
   * Pushes to `dev` trigger CI/CD builds deploying to `building-analytics-front-dev` in project `building-analytics-dev-513719`.
2. **`main` Branch:**
   * Production branch.
   * Direct pushes to `main` are disabled. All changes must arrive via a reviewed Pull Request from `dev`.
   * Pushes to `main` deploy to `building-analytics-front-prod` in project `building-analytics-prod`.
3. **Commit Messages:** Follow **Conventional Commits**:
   * `feat(...)`: New feature or UI component.
   * `fix(...)`: Bug fix.
   * `chore(...)`: Dependency updates or build changes.
   * `refactor(...)`: Code cleanup without behavior change.

---

## 6. Container & Cloud Run Execution Rules

When creating or modifying container configurations:
1. **Cloud Run Port Contract:** Containers **MUST** listen on `0.0.0.0` and port `${PORT}` (default `8080`).
2. **Stateless Instances:** Do not store uploaded user files or session data on the container's local file system. Containers scale to zero and can restart at any moment. All state belongs in Cloud Storage or Cloud SQL via the backend.
