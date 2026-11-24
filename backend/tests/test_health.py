import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Verifies that the /api/v1/health endpoint returns 200 OK and valid schema."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert data["environment"] in ["development", "testing", "production"]


@pytest.mark.asyncio
async def test_root_health_check(client):
    """Verifies that the root /health endpoint returns 200 OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_database_health_endpoint(client):
    """Verifies the /api/v1/health/db connectivity endpoint responds without unhandled exceptions."""
    response = await client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["connected", "disconnected"]
    assert "database" in data
    assert "latency_ms" in data
