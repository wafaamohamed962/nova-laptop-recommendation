from app.retrieval import fetch_candidates
from tests.conftest import make_laptop, make_session_factory


def test_strict_requirements_match_when_available():
    laptops = [
        make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True),
        make_laptop(os="Windows", ram_gb=8, has_dedicated_gpu=False),
        make_laptop(os="macOS", ram_gb=16, has_dedicated_gpu=True),
        make_laptop(os="Windows", ram_gb=32, has_dedicated_gpu=True),
        make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True),
        make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True),
    ]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "Windows", "min_ram_gb": 16, "require_dedicated_gpu": True}
        results, notes = fetch_candidates(session, requirements, min_results=3)
    finally:
        session.close()

    assert len(results) == 4  # Windows + ram>=16 + dedicated GPU
    assert all(r.os == "Windows" and r.ram_gb >= 16 and r.has_dedicated_gpu for r in results)
    assert notes == []


def test_relaxes_gpu_requirement_when_too_few_results():
    laptops = [
        make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=False) for _ in range(5)
    ] + [make_laptop(os="Windows", ram_gb=16, has_dedicated_gpu=True)]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "Windows", "min_ram_gb": 16, "require_dedicated_gpu": True}
        results, notes = fetch_candidates(session, requirements, min_results=5)
    finally:
        session.close()

    # only 1 laptop satisfies the strict GPU requirement -> should relax to find 6
    assert len(results) == 6
    assert len(notes) == 1
    assert "gpu" in notes[0]


def test_relaxes_all_the_way_to_ram_only_when_os_is_scarce():
    laptops = [make_laptop(os="Linux", ram_gb=16, has_dedicated_gpu=False) for _ in range(5)]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "macOS", "min_ram_gb": 16, "require_dedicated_gpu": True}
        results, notes = fetch_candidates(session, requirements, min_results=5)
    finally:
        session.close()

    assert len(results) == 5
    assert any("os" in note for note in notes)


def test_brand_filter_applied_when_available():
    laptops = [
        make_laptop(brand="ASUS", os="Windows", ram_gb=16, has_dedicated_gpu=False) for _ in range(3)
    ] + [make_laptop(brand="Dell", os="Windows", ram_gb=16, has_dedicated_gpu=False) for _ in range(3)]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "Windows", "brand": "ASUS", "min_ram_gb": 16, "require_dedicated_gpu": False}
        results, notes = fetch_candidates(session, requirements, min_results=3)
    finally:
        session.close()

    assert len(results) == 3
    assert all(r.brand == "ASUS" for r in results)
    assert notes == []


def test_brand_filter_is_case_insensitive():
    laptops = [make_laptop(brand="ASUS", os="Windows", ram_gb=16) for _ in range(3)]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "Windows", "brand": "asus", "min_ram_gb": 16, "require_dedicated_gpu": False}
        results, notes = fetch_candidates(session, requirements, min_results=3)
    finally:
        session.close()

    assert len(results) == 3


def test_brand_is_relaxed_first_before_os_or_gpu():
    """Brand is a stated preference, not a functional requirement -- it
    should be the first thing dropped when results are scarce, before
    touching OS or GPU."""
    laptops = [
        make_laptop(brand="Dell", os="Windows", ram_gb=16, has_dedicated_gpu=True) for _ in range(5)
    ]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "Windows", "brand": "ASUS", "min_ram_gb": 16, "require_dedicated_gpu": True}
        results, notes = fetch_candidates(session, requirements, min_results=5)
    finally:
        session.close()

    # no ASUS laptops exist at all -- brand gets dropped, OS/GPU stay intact
    assert len(results) == 5
    assert all(r.os == "Windows" and r.has_dedicated_gpu for r in results)
    assert len(notes) == 1
    assert "brand" in notes[0]
    assert "os" not in notes[0].split("[")[1].split("]")[0]  # os wasn't among the dropped constraints


def test_never_returns_zero_even_when_pool_is_tiny():
    laptops = [make_laptop(os="Windows", ram_gb=4, has_dedicated_gpu=False)]
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        requirements = {"os": "macOS", "min_ram_gb": 32, "require_dedicated_gpu": True}
        results, notes = fetch_candidates(session, requirements, min_results=5)
    finally:
        session.close()

    assert len(results) == 1  # fully relaxed (no filters) still returns the one laptop that exists
