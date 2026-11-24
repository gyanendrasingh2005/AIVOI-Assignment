# PharmaRCA: Enterprise AI-Powered RCA & CAPA Platform

> Enterprise-grade Root Cause Analysis (RCA) and Corrective and Preventive Action (CAPA) platform tailored for Active Pharmaceutical Ingredient (API) manufacturing quality management.

---

## 1. System Overview

PharmaRCA establishes a compliant, intelligent investigation workflow adhering to **ICH Q7**, **ICH Q9 (R1)**, **ICH Q10**, and **FDA 21 CFR Part 11 / Part 211** standards:

```
Incident Intake ➔ Document Extraction ➔ Quality Risk Assessment ➔ Evidence Collection ➔ Root Cause Analysis (5-Whys / Fishbone) ➔ Evidence Gap Detection ➔ CAPA Recommendations ➔ Human Review ➔ E-Signature Approval ➔ Effectiveness Verification ➔ Closure
```

---

## 2. Technology Stack

### Frontend
- **React 18** + **Vite** + **TypeScript**
- **Redux Toolkit** (centralized application state)
- **React Router v6** (role-based protected navigation)
- **Tailwind CSS** (clean enterprise pharma design system)
- **Axios** (centralized API client with interceptors)
- **Lucide React** (clinical iconography)

### Backend
- **Python 3.11+** + **FastAPI**
- **SQLAlchemy 2.0** (asynchronous ORM)
- **Pydantic v2 & Pydantic-Settings** (robust validation & typed configurations)
- **Alembic** (database schema migrations)
- **PyMuPDF (fitz)** (high-fidelity BPR, CoA & equipment log text/table extraction)
- **Pytest & Pytest-Asyncio** (automated unit and integration testing)

### AI Orchestration
- **LangGraph** (stateful multi-node agent workflow)
- **Groq API** (`llama-3.3-70b-versatile` or configurable model)
- Zero-hallucination evidence citation enforcement

### Database & Storage
- **PostgreSQL 16**
- Dedicated encrypted document store with **SHA-256 integrity hashing**
- Immutable, tamper-evident audit logging engine

---

## 3. Directory Layout

```
.
├── .gitignore
├── README.md
├── backend/
│   ├── alembic/                      # Database migrations
│   ├── app/
│   │   ├── ai/                       # LangGraph stateful agents & nodes
│   │   │   ├── graphs/
│   │   │   ├── nodes/
│   │   │   ├── prompts/
│   │   │   └── schemas/
│   │   ├── api/                      # Versioned REST API routes
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       └── api_router.py
│   │   ├── core/                     # Configuration, security, logging
│   │   ├── database/                 # SQLAlchemy 2.0 async engine & session
│   │   ├── middleware/               # Error handling, request auditing
│   │   ├── models/                   # SQLAlchemy declarative entities
│   │   ├── repositories/             # Data access layer
│   │   ├── schemas/                  # Pydantic v2 schemas
│   │   ├── services/                 # Domain business logic
│   │   └── utils/                    # Helper functions & hashing
│   ├── tests/                        # Backend test suites
│   ├── requirements.txt
│   ├── alembic.ini
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/                      # Main application entry & providers
    │   ├── components/               # Common, layout, and UI components
    │   ├── features/                 # Modular domain features
    │   │   ├── approvals/
    │   │   ├── auth/
    │   │   ├── capa/
    │   │   ├── dashboard/
    │   │   ├── documents/
    │   │   ├── evidence/
    │   │   ├── investigations/
    │   │   └── rca/
    │   ├── hooks/                    # Custom React hooks
    │   ├── lib/                      # External library wrappers
    │   ├── services/                 # API service abstractions
    │   ├── store/                    # Redux Toolkit store & slices
    │   ├── types/                    # TypeScript interfaces
    │   └── utils/                    # Formatting & GMP constants
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── tailwind.config.js
```

---

## 4. Getting Started

### Prerequisites
- Node.js 18+ & npm 9+
- Python 3.11+
- PostgreSQL 15+

### Backend Setup (PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your PostgreSQL credentials and Groq API key
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup (PowerShell)
```powershell
cd frontend
npm install
npm run dev
```

The application will be accessible at `http://localhost:5173`.
API documentation is hosted at `http://localhost:8000/docs`.
