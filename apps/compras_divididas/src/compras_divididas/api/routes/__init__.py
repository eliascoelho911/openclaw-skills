"""API v1 router registration."""

from fastapi import APIRouter

from compras_divididas.api.routes import (
    monthly_reports,
    movements,
    participants,
    recurrences,
)

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(participants.router)
v1_router.include_router(movements.router)
v1_router.include_router(monthly_reports.router)
v1_router.include_router(recurrences.router)
v1_router.include_router(recurrences.monthly_generation_router)
