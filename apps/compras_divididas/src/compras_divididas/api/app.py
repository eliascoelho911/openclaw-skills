"""FastAPI app bootstrap for compras_divididas."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from compras_divididas.api.error_handlers import register_error_handlers
from compras_divididas.api.routes import v1_router
from compras_divididas.db.session import get_db_session


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""

    app = FastAPI(
        title="Compras Divididas API",
        version="0.1.0",
    )

    @app.get("/health/live", include_in_schema=False)
    def health_live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", include_in_schema=False)
    def health_ready(
        db_session: Annotated[Session, Depends(get_db_session)],
    ) -> dict[str, str]:
        try:
            db_session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is unavailable",
            ) from exc
        return {"status": "ready"}

    register_error_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()
