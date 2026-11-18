import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.api.auth import router as auth_router
from app.api.meetings import router
from app.core.config import Settings
from app.db.session import build_engine

logger = logging.getLogger("meeting_assistant")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level)
    # 即使 LOG_LEVEL=DEBUG，也不启用 SQL 参数日志。
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    engine = build_engine(settings.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Meeting Action Assistant", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # 异常字符串可能含连接串或正文；仅记错误类型和路由模板。
        route = request.scope.get("route")
        logger.error("database_failure method=%s route=%s error_type=%s", request.method,
                     getattr(route, "path", "unknown"), type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        # 这是进程存活检查，不伪装成数据库 readiness。
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(router)
    return app
