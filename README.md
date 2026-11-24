# PharmaRCA: Enterprise AI-Powered RCA & CAPA Quality Management Platform

> An enterprise pharmaceutical Root Cause Analysis (RCA) and Corrective & Preventive Action (CAPA) platform engineered for Active Pharmaceutical Ingredient (API) and drug product manufacturing under **FDA 21 CFR Part 11**, **21 CFR §211.192**, **ICH Q7**, **ICH Q9 (R1)**, and **ICH Q10**.

---

## 1. System Architecture & Lifecycle

PharmaRCA orchestrates an evidence-grounded, human-in-the-loop investigation workflow. AI models (via Groq and LangGraph) are strictly advisory; all root causes, gaps, tasks, effectiveness decisions, and closure actions require human investigator verification and authorized QA sign-off.

```
       [ Deviation / OOS Detected ]
                    │
                    ▼
       [ 1. Draft Investigation Intake ]
                    │
                    ▼
       [ 2. BPR / CoA / Equipment PDF Upload ] ──► [ SHA-256 Checksum & Encryption ]
                    │
                    ▼
       [ 3. Text & Table Extraction (PyMuPDF) ]
                    │
                    ▼
       [ 4. AI Structured Extraction (LangGraph) ]
                    │
                    ▼
       [ 5. Human Investigator Review & Confirmation ]
                    │
                    ▼
       [ 6. Quality Risk Assessment (ICH Q9 Matrix) ] ──► [ Severity × Probability × Detectability ]
                    │
                    ▼
       [ 7. Root Cause Analysis (5 Whys + Fishbone) ] ──► [ Evidence-Grounding Validation ]
                    │
                    ▼
       [ 8. Evidence Gap Detection & Completeness ]
                    │
                    ▼
       [ 9. Human Gap Remediation & Evidence Attachment ]
                    │
                    ▼
       [ 10. QA Root Cause Verification ]
                    │
                    ▼
       [ 11. AI CAPA Recommendations (ICH Q10) ]
                    │
                    ▼
       [ 12. CAPA Formulation & Action Task Planning ]
                    │
                    ▼
       [ 13. QA CAPA Plan Approval (21 CFR Part 11) ]
                    │
                    ▼
       [ 14. Action Task Execution & Evidence Upload ]
                    │
                    ▼
       [ 15. QA Task Verification & Closure ]
                    │
                    ▼
       [ 16. Effectiveness Check Planning ]
                    │
                    ▼
       [ 17. Monitoring Data Collection & AI Assessment ]
                    │
            ┌───────┴────────────────────────┐
            ▼                                ▼
   [ No Recurrence ]             [ Recurrence Observed ]
            │                                │
            ▼                                ▼
   [ 18. Decision: EFFECTIVE ]    [ 21 CFR §211.192 Violation ]
            │                     [ Decision CANNOT be Effective ]
            ▼                                │
   [ 19. CAPA Closure Validation ]           ▼
            │                     [ 18b. Decision: INEFFECTIVE ]
            ▼                                │
   [ 20. QA Authorized Closure ]             ▼
            │                     [ 19b. Reopen CAPA / Spawn Follow-Up ]
            ▼
   [ 21. Centralized Investigation Closure ]
```

---

## 2. Technology Stack

### Backend
- **Framework**: Python 3.11+, FastAPI (Async/Await)
- **Database ORM**: SQLAlchemy 2.0 (AsyncIO), Alembic migrations
- **Databases**: PostgreSQL 16 (production), SQLite / aiosqlite (zero-dependency development)
- **AI Orchestration**: LangGraph, Groq API (`llama-3.3-70b-versatile`)
- **Document Processing**: PyMuPDF (`pymupdf`), PDF text & table parsing
- **Security & RBAC**: JWT, Passlib (bcrypt), 21 CFR Part 11 audit trails
- **Test Suite**: Pytest, Pytest-Asyncio, HTTPX (136/136 tests passing)

### Frontend
- **Framework**: React 18, Vite, TypeScript 5.4+
- **State Management**: Redux Toolkit & React Hooks
- **Styling**: Tailwind CSS (GxP clinical colorway), Lucide React
- **API Client**: Axios with request/response interceptors & token auto-attachment

---

## 3. Quick Start & Execution

### Option A: Direct Local Execution (Instant Zero-Dependency)

The backend automatically initializes local SQLite schemas and bootstraps standard roles and the Admin account on first run.

#### 1. Start Backend (Terminal 1)
```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
- **Backend API & Swagger Docs**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

#### 2. Start Frontend (Terminal 2)
```powershell
npm run dev --prefix frontend
```
- **Web Application**: [http://localhost:5173/](http://localhost:5173/)

---

### Option B: Production Docker Deployment

Deploy the full containerized stack (PostgreSQL 16 + FastAPI Backend + Alpine Nginx Frontend):

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Launch all services
docker compose up --build -d

# 3. View status and health
docker compose ps
```
- Web Application: `http://localhost/` or `http://localhost:3000/`
- API Backend: `http://localhost:8000/api/v1/docs`

---

## 4. Default Seeded Credentials & Roles

| Role | Email | Password | Permissions & Oversight |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@pharmarca.com` | `AdminPassword123!` | System configuration, user management, audit logs |
| **QA Approver** | `qa.approver@pharma.com` | `SecurePassword123!` | 21 CFR Part 11 sign-offs, CAPA plan approvals, closures |
| **Lead Investigator** | `investigator@pharma.com` | `SecurePassword123!` | Incident analysis, 5 Whys, Fishbone, task execution |
| **Operator** | `operator@pharma.com` | `SecurePassword123!` | Incident intake, initial evidence upload |

---

## 5. Automated Verification & Testing

PharmaRCA features 100% test pass rate across 10 modular test suites:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Test Suite Breakdown:
1. `test_auth.py` (21 CFR Part 11 authentication, token expiry, RBAC)
2. `test_investigations.py` (Investigation numbering, state machine, assignment)
3. `test_documents.py` (PyMuPDF extraction, SHA-256 checksums, evidence scoping)
4. `test_ai_foundation.py` (Groq provider abstraction, LangGraph workflows, error recovery)
5. `test_ai_incident_extraction.py` (Analyzable context, hallucination checks, human review)
6. `test_ai_risk_assessment.py` (ICH Q9 risk matrix, severity/probability/detectability scoring)
7. `test_ai_rca.py` (5 Whys causal paths, Ishikawa 6M categorization, verified root causes)
8. `test_ai_evidence_gap.py` (Completeness scoring, gap remediation, human acceptance)
9. `test_ai_capa.py` (Action recommendations, task planning, verification workflow)
10. `test_ai_capa_effectiveness.py` (Monitoring, AI effectiveness assessment, 21 CFR §211.192 recurrence blocker)
11. `test_master_e2e_integration.py` (Complete 27-step lifecycle & GAMP 5 data integrity invariants)

---

## 6. GxP Compliance & Regulatory Safeguards

- **21 CFR Part 11**: Cryptographic password hashing (bcrypt), JWT access controls, session expiry, and immutable audit logs capturing user ID, timestamp, entity type, and detailed delta payloads.
- **21 CFR §211.192**: If deviation recurrence is observed during the observation period, an `EFFECTIVE` quality decision is strictly prohibited by backend state machine enforcement. The system mandates recording the recurrence, marking the check ineffective, and reopening the CAPA or spawning a linked follow-up investigation.
- **ICH Q9 (R1) Quality Risk Management**: Standardized 5×5 Risk Priority Matrix calculating RPN, severity, probability, and detectability with mandatory QA review.
- **ICH Q10 Pharmaceutical Quality System**: Closed-loop CAPA methodology enforcing root cause linkage, remediation verification, and independent effectiveness evaluation.
