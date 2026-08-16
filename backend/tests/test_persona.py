from app.persona import classify_persona
from app.state import LaptopSessionState


def test_ai_workload_takes_priority():
    persona = classify_persona(LaptopSessionState(ai_workload=True, gaming_preference="AAA"))
    assert persona == "ai_workload"


def test_gaming_aaa():
    assert classify_persona(LaptopSessionState(gaming_preference="AAA")) == "gaming_aaa"


def test_gaming_casual():
    assert classify_persona(LaptopSessionState(gaming_preference="casual")) == "gaming_casual"


def test_performance_major():
    assert classify_persona(LaptopSessionState(major="Computer Science")) == "performance"


def test_performance_intent_programmer():
    """Reproduces the reported ask: a self-described programmer (no formal
    major given) should still get the performance persona via intent."""
    assert classify_persona(LaptopSessionState(intent="I'm a programmer")) == "performance"


def test_portability_major():
    assert classify_persona(LaptopSessionState(major="Medicine")) == "portability"


def test_general_when_no_signal():
    assert classify_persona(LaptopSessionState()) == "general"
