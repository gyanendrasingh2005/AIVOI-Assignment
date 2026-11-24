from pydantic import BaseModel, Field
from datetime import datetime


class HealthStatusResponse(BaseModel):
    status: str = Field(default="healthy", description="Application status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="UTC timestamp of the status check")
    environment: str = Field(..., description="Runtime environment")


class DatabaseHealthResponse(BaseModel):
    status: str = Field(..., description="Database connection status: 'connected' or 'disconnected'")
    database: str = Field(..., description="Target database name")
    latency_ms: float = Field(..., description="Roundtrip query latency in milliseconds")
    error: str | None = Field(default=None, description="Detailed error message if connection failed")
