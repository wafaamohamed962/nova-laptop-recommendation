from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db


def test_get_db_yields_a_working_session_and_closes_it(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'db_test.db'}", connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(bind=engine)

    monkeypatch.setattr("app.db.SessionLocal", TestSessionLocal)

    gen = get_db()
    db = next(gen)
    try:
        assert isinstance(db, Session)
        assert db.execute(text("SELECT 1")).scalar() == 1
    finally:
        gen.close()  # triggers the generator's finally: db.close()
