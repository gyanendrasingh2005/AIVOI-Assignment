from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthStatusResponse, DatabaseHealthResponse
from app.database.session import check_database_connection

router = APIRouter(tags=["System Health & Telemetry"])


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Probe",
    description="Returns the runtime operational status and version of the PharmaRCA API.",
)
async def get_health() -> HealthStatusResponse:
    return HealthStatusResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Database Connectivity Probe",
    description="Probes the PostgreSQL cluster with a live query and reports connectivity and latency.",
)
async def get_database_health() -> DatabaseHealthResponse:
    db_result = await check_database_connection()
    return DatabaseHealthResponse(
        status="connected" if db_result["connected"] else "disconnected",
        database=db_result["database"],
        latency_ms=db_result["latency_ms"],
        error=db_result["error"],
    )
