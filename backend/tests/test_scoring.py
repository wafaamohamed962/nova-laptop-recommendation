from app.scoring import score_candidates, select_top_picks, select_weight_profile
from app.state import LaptopSessionState
from tests.conftest import make_laptop, make_session_factory


def _committed(*laptops):
    """Seed laptops into a real (in-memory) DB and return them with .id populated,
    matching how select_top_picks is actually fed in production (via fetch_candidates)."""
    session_factory = make_session_factory(laptops)
    session = session_factory()
    try:
        return session.query(type(laptops[0])).order_by(type(laptops[0]).id).all()
    finally:
        session.close()


def test_weight_profile_gaming_aaa_favors_performance_and_vram():
    weights = select_weight_profile(LaptopSessionState(gaming_preference="AAA"))
    assert weights["performance"] == weights["vram"] == 0.35
    assert sum(weights.values()) == 1.0


def test_weight_profile_ai_workload_favors_performance_and_vram():
    weights = select_weight_profile(LaptopSessionState(ai_workload=True))
    assert weights["vram"] == 0.35


def test_weight_profile_cs_major_favors_performance():
    weights = select_weight_profile(LaptopSessionState(major="Computer Science"))
    assert weights["performance"] == 0.35
    assert sum(weights.values()) == 1.0


def test_weight_profile_medical_major_favors_portability():
    weights = select_weight_profile(LaptopSessionState(major="Medicine"))
    assert weights["portability"] == 0.45
    assert sum(weights.values()) == 1.0


def test_weight_profile_default_when_no_signal():
    weights = select_weight_profile(LaptopSessionState())
    assert sum(weights.values()) == 1.0


def test_score_candidates_empty_list_returns_empty():
    assert score_candidates([], LaptopSessionState()) == []


def test_score_candidates_ranks_higher_specs_higher():
    weak = make_laptop(cpu_ghz=1.5, ram_gb=8, has_dedicated_gpu=False, gpu_vram_gb=None)
    strong = make_laptop(cpu_ghz=4.5, ram_gb=32, has_dedicated_gpu=True, gpu_vram_gb=8.0)

    scored = score_candidates([weak, strong], LaptopSessionState(major="Computer Science"))
    scored_by_id = {s.laptop.model_name: s for s in scored}

    assert scored_by_id[strong.model_name].performance_score > scored_by_id[weak.model_name].performance_score
    assert scored_by_id[strong.model_name].vram_score > scored_by_id[weak.model_name].vram_score
    assert scored_by_id[strong.model_name].total_score > scored_by_id[weak.model_name].total_score


def test_score_candidates_smaller_screen_scores_more_portable():
    small = make_laptop(screen_size_inches=13.0)
    large = make_laptop(screen_size_inches=17.0)

    scored = score_candidates([small, large], LaptopSessionState(major="Medicine"))
    scored_by_id = {s.laptop.model_name: s for s in scored}

    assert scored_by_id[small.model_name].portability_score > scored_by_id[large.model_name].portability_score


def test_score_candidates_handles_all_missing_battery_life_neutrally():
    a = make_laptop(battery_life_hours=None)
    b = make_laptop(battery_life_hours=None)

    scored = score_candidates([a, b], LaptopSessionState())

    assert all(0.0 <= s.portability_score <= 1.0 for s in scored)


def test_score_candidates_value_score_is_neutral_placeholder():
    scored = score_candidates([make_laptop(), make_laptop()], LaptopSessionState())
    assert all(s.value_score == 0.5 for s in scored)


def test_select_top_picks_empty_returns_empty():
    assert select_top_picks([]) == []


def test_select_top_picks_returns_three_distinct_with_labels():
    # Weak-everything laptop (lowest performance+vram -> should be the Budget pick),
    # a balanced/portable middle laptop (best under default weights, which favor
    # portability -> should be Best Overall), and a heavy max-spec laptop with poor
    # portability (highest raw performance+vram, but not the top *weighted* score
    # -> should be the separate Power pick). Deliberately decoupled from Best
    # Overall so the two labels can't collide onto the same laptop.
    laptops = _committed(
        make_laptop(
            cpu_ghz=1.5, ram_gb=8, has_dedicated_gpu=False,
            screen_size_inches=15.0, battery_life_hours=8.0,
        ),
        make_laptop(
            cpu_ghz=2.5, ram_gb=16, has_dedicated_gpu=False,
            screen_size_inches=13.0, battery_life_hours=14.0,
        ),
        make_laptop(
            cpu_ghz=4.5, ram_gb=32, has_dedicated_gpu=True, gpu_vram_gb=8.0,
            screen_size_inches=17.0, battery_life_hours=4.0,
        ),
        make_laptop(
            cpu_ghz=3.0, ram_gb=16, has_dedicated_gpu=True, gpu_vram_gb=4.0,
            screen_size_inches=15.0, battery_life_hours=8.0,
        ),
    )
    # Medicine weights portability heavily enough (0.45) that it beats a laptop
    # maxing performance+vram alone (combined weight only 0.30 here), so Best
    # Overall and the raw max-spec Power pick land on different laptops.
    scored = score_candidates(laptops, LaptopSessionState(major="Medicine"))

    picks = select_top_picks(scored)

    assert len(picks) == 3
    ids = [p["id"] for p in picks]
    assert len(set(ids)) == len(ids)  # no duplicates
    reasons = {p["selection_reason"] for p in picks}
    assert any("Best Overall" in r for r in reasons)
    assert any("Budget Saver" in r for r in reasons)
    assert any("Power" in r for r in reasons)

    budget_pick = next(p for p in picks if "Budget Saver" in p["selection_reason"])
    assert budget_pick["cpu_ghz"] == 1.5

    power_pick = next(p for p in picks if "Power" in p["selection_reason"])
    assert power_pick["cpu_ghz"] == 4.5

    best_overall = next(p for p in picks if "Best Overall" in p["selection_reason"])
    assert best_overall["cpu_ghz"] == 2.5  # the balanced/portable pick, not the raw max-spec one


def test_select_top_picks_dedupes_when_pool_smaller_than_three():
    laptops = _committed(make_laptop(cpu_ghz=2.0), make_laptop(cpu_ghz=3.0))
    scored = score_candidates(laptops, LaptopSessionState())

    picks = select_top_picks(scored)

    ids = [p["id"] for p in picks]
    assert len(picks) <= 2
    assert len(set(ids)) == len(ids)


def test_select_top_picks_single_candidate():
    scored = score_candidates([make_laptop()], LaptopSessionState())
    picks = select_top_picks(scored)
    assert len(picks) == 1
