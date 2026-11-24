from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import PharmaRCAException
from app.middleware.error_handler import (
    pharmarca_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    generic_exception_handler,
)
from app.api.v1.api_router import api_router
from app.database.session import check_database_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    db_check = await check_database_connection()
    if db_check["connected"]:
        logger.info(f"Connected to PostgreSQL cluster ({db_check['database']}, Latency: {db_check['latency_ms']}ms)")
    else:
        logger.warning(f"PostgreSQL connection check failed during startup: {db_check['error']}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise AI-Powered Root Cause Analysis & CAPA Platform for API Manufacturing.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(PharmaRCAException, pharmarca_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Mount API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also mount health endpoint at root /health for convenience
from app.api.v1.endpoints.health import router as health_root_router
app.include_router(health_root_router)
