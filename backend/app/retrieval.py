"""
Database Retriever: turns HardwareRequirements into a SQLAlchemy query and
runs it. If the strict requirements are too narrow for this catalog (common
with a specific OS + dedicated-GPU + high-RAM combination), progressively
relaxes constraints -- dropping the GPU requirement, then lowering the RAM
floor, then dropping the OS filter -- until at least `min_results` candidates
come back, or we run out of relaxation steps. This guarantees the downstream
scorer/selector always has something to work with.
"""

from sqlalchemy.orm import Session

from app.agents.hardware_architect import HardwareRequirements
from app.models import Laptop

RelaxationStep = tuple[str, ...]

# Each step names which constraints are still enforced, in decreasing strictness.
_RELAXATION_STEPS: list[RelaxationStep] = [
    ("os", "gpu", "ram"),
    ("os", "ram"),
    ("ram",),
    (),
]


def _apply_requirements(query, requirements: HardwareRequirements, active: RelaxationStep):
    if "os" in active and requirements["os"]:
        query = query.filter(Laptop.os == requirements["os"])
    if "gpu" in active and requirements["require_dedicated_gpu"]:
        query = query.filter(Laptop.has_dedicated_gpu.is_(True))
    if "ram" in active:
        query = query.filter(Laptop.ram_gb >= requirements["min_ram_gb"])
    return query


def fetch_candidates(
    session: Session,
    requirements: HardwareRequirements,
    min_results: int = 5,
) -> tuple[list[Laptop], list[str]]:
    """Returns (candidates, relaxation_notes). relaxation_notes is empty if the
    strict requirements were satisfiable as-is."""
    notes: list[str] = []

    for step_index, active in enumerate(_RELAXATION_STEPS):
        query = _apply_requirements(session.query(Laptop), requirements, active)
        results = query.all()

        is_last_step = step_index == len(_RELAXATION_STEPS) - 1
        if len(results) >= min_results or is_last_step:
            if step_index > 0:
                dropped = [c for c in ("os", "gpu", "ram") if c not in active]
                notes.append(
                    f"Not enough exact matches; relaxed constraint(s) [{', '.join(dropped)}] "
                    f"to find {len(results)} candidates."
                )
            return results, notes

    return [], notes  # unreachable, but keeps type-checkers happy
