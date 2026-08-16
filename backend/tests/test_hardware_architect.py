from app.agents.hardware_architect import derive_hardware_requirements
from app.state import LaptopSessionState


def test_ai_workload_requires_dedicated_gpu_and_high_ram():
    state = LaptopSessionState(ai_workload=True)
    req = derive_hardware_requirements(state)
    assert req["require_dedicated_gpu"] is True
    assert req["min_ram_gb"] == 16


def test_aaa_gaming_requires_dedicated_gpu_and_high_ram():
    state = LaptopSessionState(gaming_preference="AAA")
    req = derive_hardware_requirements(state)
    assert req["require_dedicated_gpu"] is True
    assert req["min_ram_gb"] == 16


def test_casual_gaming_does_not_require_dedicated_gpu():
    state = LaptopSessionState(gaming_preference="casual")
    req = derive_hardware_requirements(state)
    assert req["require_dedicated_gpu"] is False
    assert req["min_ram_gb"] == 8


def test_no_gaming_or_ai_uses_default_baseline():
    state = LaptopSessionState(gaming_preference="none", ai_workload=False)
    req = derive_hardware_requirements(state)
    assert req["require_dedicated_gpu"] is False
    assert req["min_ram_gb"] == 8


def test_os_preference_passed_through():
    state = LaptopSessionState(os_preference="Windows")
    req = derive_hardware_requirements(state)
    assert req["os"] == "Windows"


def test_no_os_preference_means_no_filter():
    state = LaptopSessionState(os_preference="no preference")
    req = derive_hardware_requirements(state)
    assert req["os"] is None


def test_unset_os_preference_means_no_filter():
    state = LaptopSessionState(os_preference=None)
    req = derive_hardware_requirements(state)
    assert req["os"] is None


def test_budget_max_never_appears_in_requirements():
    state = LaptopSessionState(budget_max=999999)
    req = derive_hardware_requirements(state)
    assert "budget_max" not in req
    assert "baseline_price" not in req


def test_brand_preference_passed_through():
    state = LaptopSessionState(brand_preference="ASUS")
    req = derive_hardware_requirements(state)
    assert req["brand"] == "ASUS"


def test_brand_preference_strips_whitespace():
    state = LaptopSessionState(brand_preference="  Dell  ")
    req = derive_hardware_requirements(state)
    assert req["brand"] == "Dell"


def test_no_brand_preference_means_no_filter():
    state = LaptopSessionState(brand_preference="no preference")
    req = derive_hardware_requirements(state)
    assert req["brand"] is None


def test_unset_brand_preference_means_no_filter():
    state = LaptopSessionState(brand_preference=None)
    req = derive_hardware_requirements(state)
    assert req["brand"] is None
