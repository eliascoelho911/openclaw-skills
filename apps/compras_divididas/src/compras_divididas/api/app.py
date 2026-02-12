"""FastAPI app bootstrap for compras_divididas."""

from fastapi import FastAPI

from compras_divididas.api.error_handlers import register_error_handlers
from compras_divididas.api.routes import v1_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""

    app = FastAPI(
        title="Compras Divididas API",
        version="0.1.0",
    )
    register_error_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()
