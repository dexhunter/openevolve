"""Allocations inside one full-population MAP-Elites snapshot.

ProgramDatabase._population_snapshot is the copy a population strategy sees on
admission, cell replacement, eviction, and migration. The shipped default
population is 1,000 programs across 5 islands. Each program carries the circle
packing evaluator's metric keys and a small metadata dict, and its code is the
shipped best_program.py text plus a unique tail so the strings are distinct.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import emit, load_alloccount  # noqa: E402
from openevolve.config import DatabaseConfig  # noqa: E402
from openevolve.database import Program, ProgramDatabase  # noqa: E402

POPULATION = 1000
ISLANDS = 5
RUNS = 5
METRIC_KEYS = (
    "combined_score",
    "sum_radii",
    "target_ratio",
    "validity",
    "eval_time",
    "radius_variance",
    "spatial_spread",
)


def build_database():
    code = (ROOT / "examples" / "circle_packing" / "best_program.py").read_text(encoding="utf-8")
    config = DatabaseConfig(
        population_size=POPULATION,
        num_islands=ISLANDS,
        archive_size=100,
        random_seed=1,
        in_memory=True,
        db_path=None,
    )
    database = ProgramDatabase(config)
    for index in range(POPULATION):
        island = index % ISLANDS
        program = Program(
            id=f"prog-{index:04d}",
            code=f"{code}\n# variant {index}\n",
            metrics={key: ((index + len(key)) % 17) / 10.0 for key in METRIC_KEYS},
            metadata={
                "island": island,
                "parent_metrics": {"combined_score": 0.25, "validity": 1.0},
                "changes": "tighten bounds",
            },
        )
        database.programs[program.id] = program
        database.islands[island].add(program.id)
        if index % 2 == 0:
            database.island_feature_maps[island][f"{index % 10}-{index % 10}"] = program.id
    database.archive = {f"prog-{index:04d}" for index in range(100)}
    database.best_program_id = "prog-0000"
    database.island_best_programs = [f"prog-{island:04d}" for island in range(ISLANDS)]
    return database


def main():
    counter = load_alloccount()
    database = build_database()
    snapshot = database._population_snapshot()
    if len(snapshot.programs) != POPULATION:
        raise SystemExit(f"expected {POPULATION} programs, got {len(snapshot.programs)}")
    if len(snapshot.islands) != ISLANDS:
        raise SystemExit(f"expected {ISLANDS} islands, got {len(snapshot.islands)}")

    # Install the counter and drop the first hooked call. The steady-state
    # count is what repeated admissions pay.
    counter.start()
    try:
        database._population_snapshot()
    finally:
        counter.stop()

    samples = []
    for _ in range(RUNS):
        counter.start()
        try:
            snapshot = database._population_snapshot()
        finally:
            samples.append(counter.stop())
        if len(snapshot.programs) != POPULATION:
            raise SystemExit("snapshot lost programs")
    emit("allocations", samples)


if __name__ == "__main__":
    main()
