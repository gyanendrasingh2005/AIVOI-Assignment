# PharmaRCA: Local Development Setup & Execution Guide (Windows PowerShell)

This guide documents how to run the complete **PharmaRCA** application locally on **Windows PowerShell** using **PostgreSQL 16** without Docker.

---

## 1. Prerequisites

- **Windows 10 / 11** (64-bit)
- **PowerShell 5.1+** or **PowerShell 7+**
- **Python 3.11+**
- **Node.js 18+ & npm 9+**
- **PostgreSQL 15 or 16** (either installed via winget/installer or using the local portable distribution)

---

## 2. PostgreSQL Setup & Database Initialization

### Option A: Using the Local Standalone PostgreSQL (Included in Workspace)

If you use the portable PostgreSQL 16 located in `E:\New_project\pgsql`:

1. **Start PostgreSQL in Terminal 1**:
   ```powershell
   & "E:\New_project\pgsql\pgsql\bin\postgres.exe" -D "E:\New_project\pgsql\data"
   ```
   *Leave Terminal 1 running.*

2. **Verify connection & create database (Terminal 2 - One time only)**:
   ```powershell
   & "E:\New_project\pgsql\pgsql\bin\psql.exe" -h 127.0.0.1 -U postgres -c "SELECT version();"
   & "E:\New_project\pgsql\pgsql\bin\createdb.exe" -h 127.0.0.1 -U postgres pharmarca_qms
   & "E:\New_project\pgsql\pgsql\bin\psql.exe" -h 127.0.0.1 -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
   ```

### Option B: Installing PostgreSQL via Windows Package Manager (`winget`)

If you want a permanent system-wide Windows service:

1. Open PowerShell as **Administrator**:
   ```powershell
   winget install PostgreSQL.PostgreSQL.16 --silent --override '--unattendedmodeui none --superpassword postgres'
   ```
2. Start the Windows Service:
   ```powershell
   Start-Service postgresql-x64-16
   ```
3. Create the database:
   ```powershell
   & "C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres -h 127.0.0.1 pharmarca_qms
   ```

---

## 3. Backend Setup & Alembic Migrations

1. **Navigate to the Backend Directory**:
   ```powershell
   cd backend
   ```

2. **Activate the Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(If script execution is disabled in PowerShell, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

3. **Install Dependencies (if not already installed)**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Environment Configuration (`backend/.env`)**:
   Verify that `backend/.env` points to your PostgreSQL database:
   ```ini
   PROJECT_NAME="PharmaRCA Enterprise Platform"
   VERSION="1.0.0"
   API_V1_STR="/api/v1"
   ENVIRONMENT="development"
   DEBUG=true

   SECRET_KEY="dev_secret_key_pharmarca_21cfr11_at_least_32_characters"
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=120
   REFRESH_TOKEN_EXPIRE_DAYS=7

   BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

   POSTGRES_SERVER="127.0.0.1"
   POSTGRES_PORT=5432
   POSTGRES_USER="postgres"
   POSTGRES_PASSWORD="postgres"
   POSTGRES_DB="pharmarca_qms"
   DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/pharmarca_qms"
   SYNC_DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/pharmarca_qms"

   STORAGE_DIR="storage/evidence"
   MAX_UPLOAD_SIZE_BYTES=52428800

   GROQ_API_KEY="gsk_your_groq_api_key_here"
   GROQ_MODEL="llama-3.3-70b-versatile"
   GROQ_MAX_RETRIES=2
   GROQ_TEMPERATURE=0.1
   ```

5. **Run Alembic Migrations**:
   ```powershell
   python -m alembic upgrade head
   ```

6. **Seed Initial Roles & Administrator Account**:
   ```powershell
   $env:PYTHONPATH='backend'
   python -m app.cli seed-roles
   python -m app.cli bootstrap-admin --email admin@pharmarca.com --password AdminPassword123! --full-name "Quality System Admin"
   ```

7. **Start the FastAPI Backend (Terminal 2)**:
   ```powershell
   cd backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

---

## 4. Frontend Setup & Execution

1. **Open Terminal 3 and navigate to the frontend directory**:
   ```powershell
   cd frontend
   ```

2. **Install Dependencies (if not already installed)**:
   ```powershell
   npm install
   ```

3. **Verify `frontend/.env`**:
   ```ini
   VITE_API_BASE_URL=/api/v1
   ```

4. **Start the Frontend Dev Server (Terminal 3)**:
   ```powershell
   npm run dev
   ```

---

## 5. Application URLs & Default Credentials

| Service | Address |
| :--- | :--- |
| **Frontend Web UI** | [http://localhost:5173/](http://localhost:5173/) |
| **Backend REST API** | [http://127.0.0.1:8000/api/v1](http://127.0.0.1:8000/api/v1) |
| **Interactive OpenAPI Docs** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| **Health Check Endpoint** | [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) |
| **Database Status Check** | [http://127.0.0.1:8000/api/v1/health/db](http://127.0.0.1:8000/api/v1/health/db) |

### Default Seeded User
- **Email**: `admin@pharmarca.com`
- **Password**: `AdminPassword123!`
- **Role**: `Admin`

---

## 6. Architecture & Infrastructure Notes

### Is Docker Required?
- **No.** The entire application (PostgreSQL 16, FastAPI Backend, React Frontend) runs natively on Windows PowerShell without Docker containers or WSL virtualization.
- Docker configuration (`Dockerfile` and `docker-compose.yml`) is provided strictly as an optional deployment path for cloud/containerized environments.

### Are Redis or Celery Required?
- **No.** PharmaRCA does not use Redis or Celery. All stateful AI workflows execute in-process via LangGraph, and background tasks are orchestrated via FastAPI’s asynchronous event loop (`asyncio`) and database persistence (`ai_executions` table).

---

## 7. Common Errors & Troubleshooting

1. **`asyncpg.exceptions.StringDataRightTruncationError: value too long for type character varying(32)`**:
   - *Cause*: Alembic default `alembic_version` table defines `version_num VARCHAR(32)`, which truncates descriptive migration IDs.
   - *Fix*: `backend/alembic/env.py` has been updated with `version_num_length=128` and auto-alters `alembic_version` on startup.

2. **`ModuleNotFoundError: No module named 'app'`**:
   - *Cause*: Running python scripts from project root without `backend` in `PYTHONPATH`.
   - *Fix*: Set `$env:PYTHONPATH='backend'` before running CLI commands, or run uvicorn with `--app-dir backend`.

3. **CORS / Network connection refused**:
   - *Cause*: Accessing the backend directly while frontend runs on a different port.
   - *Fix*: Vite is configured to reverse-proxy `/api` to `http://localhost:8000`, eliminating CORS and port mismatches.

4. **Groq API Key**:
   - Ordinary backend startup and non-AI features (Authentication, Investigations, CAPA, Document Management) do NOT require a Groq API key.
   - To enable live AI incident extraction, risk assessment, 5 Whys, and CAPA recommendations, update `GROQ_API_KEY` in `backend/.env` with your key from [console.groq.com](https://console.groq.com).
