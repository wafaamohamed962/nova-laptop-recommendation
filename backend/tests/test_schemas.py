import pytest
from pydantic import ValidationError

from app.schemas import LaptopIngestRecord

VALID_KWARGS = dict(
    brand="Dell",
    model_name="Dell G15",
    processor="Intel Core i5 (12th Gen)",
    processor_brand="Intel",
    cpu_ghz=3.3,
    ram_gb=16,
    ram_expandable=True,
    storage_gb=512,
    screen_size_inches=15.6,
    gpu_name="GeForce RTX 3050",
    has_dedicated_gpu=True,
    os="Windows",
    battery_life_hours=10.0,
)


def test_valid_record_passes():
    record = LaptopIngestRecord(**VALID_KWARGS)
    assert record.brand == "Dell"
    assert record.baseline_price is None


def test_empty_brand_rejected():
    with pytest.raises(ValidationError):
        LaptopIngestRecord(**{**VALID_KWARGS, "brand": "   "})


def test_ram_gb_zero_rejected():
    with pytest.raises(ValidationError):
        LaptopIngestRecord(**{**VALID_KWARGS, "ram_gb": 0})


def test_cpu_ghz_out_of_range_rejected():
    with pytest.raises(ValidationError):
        LaptopIngestRecord(**{**VALID_KWARGS, "cpu_ghz": 50.0})


def test_screen_size_out_of_range_rejected():
    with pytest.raises(ValidationError):
        LaptopIngestRecord(**{**VALID_KWARGS, "screen_size_inches": 3.0})


def test_battery_life_out_of_range_rejected():
    with pytest.raises(ValidationError):
        LaptopIngestRecord(**{**VALID_KWARGS, "battery_life_hours": 100.0})


def test_nullable_fields_accept_none():
    record = LaptopIngestRecord(
        **{
            **VALID_KWARGS,
            "cpu_ghz": None,
            "screen_size_inches": None,
            "gpu_name": None,
            "battery_life_hours": None,
        }
    )
    assert record.cpu_ghz is None
    assert record.gpu_name is None
