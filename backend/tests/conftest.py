import itertools
from collections.abc import Callable, Iterable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Laptop

_model_name_counter = itertools.count()


def make_laptop(**overrides) -> Laptop:
    defaults = dict(
        brand="TestBrand",
        model_name=f"Test Model {next(_model_name_counter)}",
        processor="Intel Core i5",
        processor_brand="Intel",
        cpu_ghz=3.0,
        ram_gb=16,
        ram_expandable=True,
        storage_gb=512,
        screen_size_inches=15.6,
        gpu_name="Integrated",
        gpu_vram_gb=None,
        has_dedicated_gpu=False,
        os="Windows",
        battery_life_hours=8.0,
        baseline_price=None,
    )
    defaults.update(overrides)
    return Laptop(**defaults)


def make_session_factory(laptops: Iterable[Laptop]) -> Callable[[], Session]:
    """In-memory SQLite DB (shared across the engine's sessions via StaticPool)
    seeded with the given Laptop rows -- for tests that need a real
    SQLAlchemy session without touching the dev laptops.db."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Laptop.__table__])
    session_local = sessionmaker(bind=engine)

    seed_session = session_local()
    seed_session.add_all(list(laptops))
    seed_session.commit()
    seed_session.close()

    return session_local
