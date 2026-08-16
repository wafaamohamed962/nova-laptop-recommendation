"""
Pure text-cleaning functions for the raw `cleaned_laptops_rag_dataset.csv` columns.

Kept free of pandas/DB dependencies so each rule can be unit tested in isolation
against the specific messy string formats observed in the source data.
"""

import math
import re

_GHZ_RE = re.compile(r"([\d.]+)\s*Ghz", re.IGNORECASE)
_BATTERY_HOURS_RE = re.compile(r"Upto\s*([\d.]+)\s*Hrs", re.IGNORECASE)
_NUMERIC_RE = re.compile(r"^\d+(\.\d+)?$")

_BRAND_KEYWORDS = [
    ("Apple", ("apple", " m1", " m2", " m3", " m4")),
    ("Intel", ("intel", "core i", "core ultra", "core 5", "core 7", "pentium", "celeron")),
    ("AMD", ("amd", "ryzen", "athlon")),
    ("Qualcomm", ("qualcomm", "snapdragon")),
    ("MediaTek", ("mediatek",)),
    ("Microsoft", ("microsoft", "sq1", "sq2")),
]


def is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def clean_model_name(raw_name: str) -> str:
    """Strip the '::<id>::computer::laptops' scrape-artifact suffix."""
    return raw_name.split("::")[0].strip()


def extract_ghz(ghz_raw: object) -> float | None:
    """Parse e.g. ' 2.0 Ghz Processor' -> 2.0. Returns None for missing/'0' placeholders."""
    if is_missing(ghz_raw):
        return None
    match = _GHZ_RE.search(str(ghz_raw))
    if match:
        return float(match.group(1))
    return None


def resolve_processor_brand_and_ghz(
    processor_brand_raw: object, ghz_raw: object, processor_name: str
) -> tuple[str, float | None]:
    """
    Handles the ~21-row data corruption where the real GHz value leaked into
    `processor_brand` (e.g. "2.3") while `ghz` itself just reads "0".

    In that case, recover cpu_ghz from processor_brand's numeric value, and
    re-derive the actual brand string from processor_name text instead.
    """
    raw_str = "" if is_missing(processor_brand_raw) else str(processor_brand_raw).strip()

    if _NUMERIC_RE.match(raw_str):
        recovered_ghz = float(raw_str)
        brand = _infer_brand_from_processor_name(processor_name)
        return brand, recovered_ghz

    ghz = extract_ghz(ghz_raw)
    brand = raw_str if raw_str else _infer_brand_from_processor_name(processor_name)
    return brand, ghz


def _infer_brand_from_processor_name(processor_name: str) -> str:
    name_lower = processor_name.lower()
    for brand, keywords in _BRAND_KEYWORDS:
        if any(keyword in name_lower for keyword in keywords):
            return brand
    return "Unknown"


def parse_ram_expandable(raw: object) -> bool:
    if is_missing(raw):
        return False
    return str(raw).strip().lower() != "not expandable"


def parse_battery_hours(raw: object) -> float | None:
    """
    Only trusts strings matching 'Upto N Hrs Battery Life'. Rejects the ~2000
    rows where adapter-wattage text (e.g. '45W Adapter') leaked into this
    column instead, since that's not a battery-life figure at all.
    """
    if is_missing(raw):
        return None
    match = _BATTERY_HOURS_RE.search(str(raw))
    if match:
        return float(match.group(1))
    return None


def parse_gpu_name(raw: object) -> str | None:
    """'GeForce RTX 3050 GPU, 4 GB' -> 'GeForce RTX 3050'; 'Iris Xe' -> 'Iris Xe'."""
    if is_missing(raw):
        return None
    text = str(raw).split(",")[0].strip()
    text = re.sub(r"\s*GPU$", "", text, flags=re.IGNORECASE).strip()
    return text or None
