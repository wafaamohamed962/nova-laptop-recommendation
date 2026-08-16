from sqlalchemy import Boolean, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Laptop(Base):
    """
    Static knowledge-base row for one laptop model.

    Deviation from the original spec schema: `baseline_price` is nullable here.
    The source dataset (cleaned_laptops_rag_dataset.csv) has no price column at all,
    so this stays NULL for every row until/unless a fallback price source is added.
    Live pricing is fetched on demand in Phase 5 via SerpApi instead.
    """

    __tablename__ = "laptops"
    __table_args__ = (UniqueConstraint("model_name", name="uq_laptops_model_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    processor: Mapped[str] = mapped_column(String(100), nullable=False)
    processor_brand: Mapped[str] = mapped_column(String(30), nullable=False)
    cpu_ghz: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_gb: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ram_expandable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    storage_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    screen_size_inches: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpu_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    has_dedicated_gpu: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    os: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    battery_life_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<Laptop id={self.id} brand={self.brand!r} model_name={self.model_name!r}>"
