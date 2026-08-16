"""
Hardware Architect: translates a ready LaptopSessionState into concrete
hardware requirements for the DB Retriever.

Deliberately excludes budget_max. There's no price data in the static
dataset (see ingest.py), so nothing here can be filtered by price yet --
that only becomes possible once Phase 5 fetches live prices for the
already-selected top candidates. Budget is enforced as a hard filter in
app/response_mapping.py once those live prices are known.
"""

from typing import Optional, TypedDict

from app.state import LaptopSessionState

_GAMING_OR_AI_MIN_RAM_GB = 16
_CASUAL_MIN_RAM_GB = 8
_DEFAULT_MIN_RAM_GB = 8
_NO_PREFERENCE_VALUES = ("no preference", "any", "none")


class HardwareRequirements(TypedDict):
    os: Optional[str]  # None means no OS filter
    brand: Optional[str]  # None means no brand filter
    min_ram_gb: int
    require_dedicated_gpu: bool


def derive_hardware_requirements(state: LaptopSessionState) -> HardwareRequirements:
    needs_dedicated_gpu = bool(state.ai_workload) or state.gaming_preference == "AAA"

    if state.ai_workload or state.gaming_preference == "AAA":
        min_ram_gb = _GAMING_OR_AI_MIN_RAM_GB
    elif state.gaming_preference == "casual":
        min_ram_gb = _CASUAL_MIN_RAM_GB
    else:
        min_ram_gb = _DEFAULT_MIN_RAM_GB

    os_filter = state.os_preference if state.os_preference not in (None, "no preference") else None

    brand_filter = None
    if state.brand_preference and state.brand_preference.strip().lower() not in _NO_PREFERENCE_VALUES:
        brand_filter = state.brand_preference.strip()

    return HardwareRequirements(
        os=os_filter,
        brand=brand_filter,
        min_ram_gb=min_ram_gb,
        require_dedicated_gpu=needs_dedicated_gpu,
    )
