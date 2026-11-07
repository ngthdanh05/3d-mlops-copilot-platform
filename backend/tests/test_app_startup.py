"""App startup: lifespan creates tables, SQLite pragmas, real get_db dependency."""

import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database as database
import app.main as main


@pytest.fixture
def file_db(tmp_path, monkeypatch):
    """Point the app at a fresh SQLite file with the production engine setup."""
    path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    event.listen(engine.sync_engine, "connect", database._set_sqlite_pragmas)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", async_sessionmaker(engine))
    monkeypatch.setattr(main, "engine", engine)
    return path


def test_lifespan_creates_tables_and_serves_requests(file_db):
    assert not file_db.exists()
    with TestClient(main.app) as client:  # runs the lifespan (init_db)
        resp = client.post("/api/experiments", json={"name": "startup"})
        assert resp.status_code == 201
        assert client.get("/api/experiments").json()[0]["name"] == "startup"

    con = sqlite3.connect(file_db)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"experiments", "runs", "metrics"} <= tables
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    con.close()


async def test_connections_enforce_foreign_keys(file_db):
    async with database.engine.connect() as conn:
        assert (await conn.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    await database.engine.dispose()


async def test_get_db_yields_session(file_db):
    agen = database.get_db()
    session = await agen.__anext__()
    assert (await session.execute(text("SELECT 1"))).scalar() == 1
    await agen.aclose()
    await database.engine.dispose()
