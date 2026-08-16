from pydantic import BaseModel, Field, field_validator


class LaptopIngestRecord(BaseModel):
    """Validated shape of one cleaned row before it's written to the `laptops` table."""

    brand: str
    model_name: str
    processor: str
    processor_brand: str
    cpu_ghz: float | None = Field(default=None, ge=0.3, le=6.0)
    ram_gb: int = Field(ge=1, le=256)
    ram_expandable: bool
    storage_gb: int = Field(ge=0, le=16384)
    screen_size_inches: float | None = Field(default=None, ge=8.0, le=20.0)
    gpu_name: str | None = None
    gpu_vram_gb: float | None = Field(default=None, ge=0.0, le=64.0)
    has_dedicated_gpu: bool
    os: str
    battery_life_hours: float | None = Field(default=None, ge=0.0, le=48.0)
    baseline_price: float | None = None

    @field_validator("brand", "model_name", "processor", "os")
    @classmethod
    def must_be_nonempty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()
