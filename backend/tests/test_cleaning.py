import math

import pytest

from app.cleaning import (
    clean_model_name,
    extract_ghz,
    parse_battery_hours,
    parse_gpu_name,
    parse_ram_expandable,
    resolve_processor_brand_and_ghz,
)


def test_clean_model_name_strips_scrape_suffix():
    raw = "HP Chromebook 11A-NA0002MU (2E4N0PA) Laptop (11.6 Inch | ...)::585119::computer::laptops"
    assert clean_model_name(raw) == "HP Chromebook 11A-NA0002MU (2E4N0PA) Laptop (11.6 Inch | ...)"


def test_clean_model_name_no_suffix_is_noop():
    assert clean_model_name("Plain Model Name") == "Plain Model Name"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 2.0 Ghz Processor", 2.0),
        (" 4.2 Ghz Processor", 4.2),
        ("0", None),
        (float("nan"), None),
    ],
)
def test_extract_ghz(raw, expected):
    result = extract_ghz(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


def test_resolve_processor_brand_normal_case():
    brand, ghz = resolve_processor_brand_and_ghz("Intel", " 3.3 Ghz Processor", "Intel Core i5 (12th Gen)")
    assert brand == "Intel"
    assert ghz == pytest.approx(3.3)


def test_resolve_processor_brand_handles_shifted_column_corruption():
    """
    Reproduces the real 21-row data bug: processor_brand holds the GHz value
    ("2.3") and ghz itself is the placeholder "0".
    """
    brand, ghz = resolve_processor_brand_and_ghz("2.3", "0", "2.3 Ghz Processor")
    assert ghz == pytest.approx(2.3)
    # processor_name alone doesn't name a brand here (real row's processor_name
    # for this case is "Apple M1 Pro"-style text elsewhere) -- verify fallback works
    assert brand == "Unknown"


def test_resolve_processor_brand_infers_apple_from_processor_name():
    brand, ghz = resolve_processor_brand_and_ghz("2.3", "0", "Apple M1 Pro")
    assert brand == "Apple"
    assert ghz == pytest.approx(2.3)


def test_resolve_processor_brand_infers_amd_from_processor_name():
    brand, ghz = resolve_processor_brand_and_ghz(float("nan"), " 4.0 Ghz Processor", "AMD Hexa-Core Ryzen 5")
    assert brand == "AMD"
    assert ghz == pytest.approx(4.0)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Not Expandable", False),
        (" 12 GB Expandable", True),
        (" 32 GB Expandable", True),
        (float("nan"), False),
    ],
)
def test_parse_ram_expandable(raw, expected):
    assert parse_ram_expandable(raw) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Upto 12 Hrs Battery Life", 12.0),
        ("Upto 7.30 Hrs Battery Life", 7.30),
        (" Upto 9.45 Hrs Battery Life", 9.45),
        ("45W Adapter", None),  # the shifted-column junk case
        ("150W Adapter", None),
        (float("nan"), None),
    ],
)
def test_parse_battery_hours(raw, expected):
    result = parse_battery_hours(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Integrated Graphics", "Integrated Graphics"),
        ("GeForce RTX 3050 GPU, 4 GB", "GeForce RTX 3050"),
        ("GeForce RTX 3050 Ti GPU, 4 GB", "GeForce RTX 3050 Ti"),
        ("Iris Xe", "Iris Xe"),
        ("UHD GPU, 128 MB", "UHD"),
        (float("nan"), None),
    ],
)
def test_parse_gpu_name(raw, expected):
    assert parse_gpu_name(raw) == expected


def test_extract_ghz_ignores_non_numeric_junk():
    assert extract_ghz("no ghz info here") is None


def test_extract_ghz_case_insensitive():
    assert extract_ghz(" 2.5 GHZ Processor") == pytest.approx(2.5)


def test_parse_gpu_name_whitespace_only_is_none():
    assert parse_gpu_name("   ") is None


def test_parse_gpu_name_strips_surrounding_whitespace():
    assert parse_gpu_name("  Iris Xe  ") == "Iris Xe"
