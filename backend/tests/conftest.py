import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.dependencies import get_db
from app.main import app
from db.base import Base

SQLITE_URL = "sqlite://"


@pytest.fixture(autouse=True)
def disable_embeddings_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """API tests use SQLite without Ollama — skip embedding side effects."""
    monkeypatch.setattr(settings, "embedding_provider", "voyage")
    monkeypatch.setattr(settings, "voyage_api_key", "")
    monkeypatch.setattr(settings, "require_auth", False)
    monkeypatch.setattr(settings, "supabase_url", "")


@pytest.fixture(scope="function")
def engine():
    # StaticPool ensures every connection sees the same in-memory DB
    eng = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
