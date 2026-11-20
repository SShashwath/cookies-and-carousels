import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Base
from app.db.session import get_db, make_engine
from app.main import create_app


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch):
    monkeypatch.setenv("RESTAURANT_PROVIDER", "mock")
    settings.cache_clear()
    yield
    settings.cache_clear()


@pytest.fixture
def session(tmp_path):
    postgres_url = os.environ.get("FOODMATCH_TEST_DATABASE_URL")
    schema = f"test_{uuid4().hex}"
    if postgres_url:
        admin = create_engine(postgres_url)
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(postgres_url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(engine, expire_on_commit=False)
    finally:
        engine.dispose()
        if postgres_url:
            with admin.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


@pytest.fixture
def client(session):
    app = create_app()

    def database():
        with session() as db:
            yield db

    app.dependency_overrides[get_db] = database
    with TestClient(app) as test_client:
        yield test_client
