from collections.abc import Iterator
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import build_engine, get_session
from app.main import create_app


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    # 只在本机开发实例上新建随机测试库；从不清空或 drop 用户指定的现有库。
    settings = Settings()
    url = make_url(settings.database_url.get_secret_value())
    if settings.app_env not in {"development", "test"} or url.host not in {"127.0.0.1", "localhost"}:
        pytest.fail("Integration tests require a local development PostgreSQL instance")
    admin_url = url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    name = "meeting_assistant_test_" + uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    test_url = url.set(database=name).render_as_string(hide_password=False)
    try:
        cfg = Config("alembic.ini")
        cfg.attributes["database_url"] = test_url
        command.upgrade(cfg, "head")
        yield test_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    app = create_app(Settings(_env_file=None, database_url=database_url, app_env="test", jwt_secret="test-only-" * 8))
    engine = app.state.engine
    with engine.connect() as connection:
        transaction = connection.begin()
        # 路由中的 commit 释放 savepoint，外层事务在每个测试后回滚。
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            def override_session():
                yield session
            app.dependency_overrides[get_session] = override_session
            try:
                with TestClient(app) as test_client:
                    from tests.helpers import authenticate
                    authenticate(test_client)
                    yield test_client
            finally:
                transaction.rollback()
