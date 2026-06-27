from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import request_id_middleware
from app.database import connect_minio, connect_mongo, disconnect_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await connect_mongo()
    connect_minio()
    yield
    await disconnect_mongo()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SehatSaathi API",
        version="1.0.0",
        docs_url="/docs" if settings.is_dev else None,
        redoc_url="/redoc" if settings.is_dev else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_id_middleware)
    app.include_router(api_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": "Internal server error"},
        )

    return app


app = create_app()
