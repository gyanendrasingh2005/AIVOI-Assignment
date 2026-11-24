from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, users, investigations, documents, ai, rca, evidence_gaps

api_router = APIRouter()

# Mount endpoints under /api/v1
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(investigations.router)
api_router.include_router(documents.router)
api_router.include_router(ai.router)
api_router.include_router(rca.router)
api_router.include_router(evidence_gaps.router)
