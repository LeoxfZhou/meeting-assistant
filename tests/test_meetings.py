from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.session import build_engine, get_session
from app.main import create_app
from app.schemas.meeting import MAX_FILE_BYTES

PAYLOAD = {"title": "演示例会", "content": "这是合成会议文本，仅用于后端测试。"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_crud(client):
    response = client.post("/meetings", json=PAYLOAD)
    assert response.status_code == 201
    meeting = response.json()
    assert meeting["source_type"] == "pasted_text"
    assert meeting["status"] == "ready"
    assert meeting["created_at"] and meeting["updated_at"]
    url = "/meetings/" + meeting["id"]
    assert client.get(url).json() == meeting
    assert client.get("/meetings").json() == [meeting]
    updated = client.patch(url, json={"title": "修订标题"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "修订标题"
    assert updated.json()["content"] == PAYLOAD["content"]
    updated = client.patch(url, json={"content": "修订正文"})
    assert updated.json()["content"] == "修订正文"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.get("/meetings").json() == []


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing(client, method):
    kwargs = {"json": {"title": "新标题"}} if method == "patch" else {}
    assert getattr(client, method)(f"/meetings/{uuid4()}", **kwargs).status_code == 404


@pytest.mark.parametrize("payload", [
    {}, {"title": "", "content": "abc"}, {"title": "a", "content": " \n"},
    {"title": 123, "content": "abc"}, {"title": "a", "content": None},
    {**PAYLOAD, "status": "done"}, {**PAYLOAD, "title": "x" * 201},
    {**PAYLOAD, "content": "bad\x00text"},
])
def test_invalid_create(client, payload):
    assert client.post("/meetings", json=payload).status_code == 422
    assert client.get("/meetings").json() == []


@pytest.mark.parametrize("payload", [{}, {"title": None}, {"content": ""}, {"status": "ready"}])
def test_invalid_patch(client, payload):
    meeting = client.post("/meetings", json=PAYLOAD).json()
    assert client.patch("/meetings/" + meeting["id"], json=payload).status_code == 422
    assert client.get("/meetings/" + meeting["id"]).json()["content"] == PAYLOAD["content"]


@pytest.mark.parametrize("name,mime,kind", [
    ("demo.txt", "text/plain", "txt"), ("demo.md", "text/markdown", "markdown"),
    ("../../demo.TXT", "text/plain", "txt"),
])
def test_upload(client, name, mime, kind):
    response = client.post("/meetings/upload", files={"file": (name, "合成正文".encode(), mime)})
    assert response.status_code == 201
    meeting = response.json()
    assert meeting["title"] == "demo"
    assert meeting["content"] == "合成正文"
    assert meeting["source_type"] == kind
    assert client.get("/meetings/" + meeting["id"]).json() == meeting


def test_upload_bom_and_title(client):
    response = client.post("/meetings/upload", data={"title": "指定标题"},
                           files={"file": ("demo.md", b"\xef\xbb\xbfhello", "text/plain")})
    assert response.status_code == 201
    assert response.json()["content"] == "hello"
    assert response.json()["title"] == "指定标题"


@pytest.mark.parametrize("name,data,mime,status", [
    ("demo.pdf", b"hello", "application/pdf", 415),
    ("demo.txt", b"hello", "image/png", 415),
    ("demo.txt", b"", "text/plain", 422),
    ("demo.md", b" \n\t", "text/markdown", 422),
    ("demo.txt", b"\xff\xfe", "text/plain", 422),
    ("demo.txt", b"x" * (MAX_FILE_BYTES + 1), "text/plain", 413),
])
def test_bad_upload(client, name, data, mime, status):
    assert client.post("/meetings/upload", files={"file": (name, data, mime)}).status_code == status
    assert client.get("/meetings").json() == []


def test_invalid_uuid_and_pagination(client):
    assert client.get("/meetings/not-a-uuid").status_code == 422
    assert client.get("/meetings?limit=101").status_code == 422
    assert client.get("/meetings?offset=-1").status_code == 422
    for i in range(3):
        client.post("/meetings", json={**PAYLOAD, "title": str(i)})
    assert len(client.get("/meetings?limit=2").json()) == 2
    assert len(client.get("/meetings?limit=2&offset=2").json()) == 1


def test_database_failure(client, caplog):
    def broken_session():
        raise OperationalError("private SQL", {"secret": "must-not-leak"}, RuntimeError("private connection"))
    client.app.dependency_overrides[get_session] = broken_session
    response = client.get("/meetings")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "OperationalError" in caplog.text
    assert "must-not-leak" not in caplog.text
    assert "private connection" not in caplog.text


def test_postgres_schema_and_migration(database_url):
    engine = build_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {"meetings", "alembic_version"}
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT version()" )).startswith("PostgreSQL")
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0001_create_meetings"
        cfg = Config("alembic.ini")
        cfg.attributes["database_url"] = database_url
        command.check(cfg)
    finally:
        engine.dispose()


def test_real_commit_persists_between_sessions(database_url):
    # 不使用测试 savepoint，验证跨连接持久化；只写临时测试数据库。
    settings = Settings(_env_file=None, app_env="test", database_url=database_url)
    with TestClient(create_app(settings)) as first:
        response = first.post("/meetings", json=PAYLOAD)
        assert response.status_code == 201
        mid = response.json()["id"]
    with TestClient(create_app(settings)) as second:
        assert second.get(f"/meetings/{mid}").json()["content"] == PAYLOAD["content"]
        assert second.delete(f"/meetings/{mid}").status_code == 204
