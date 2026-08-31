"""Reproduce the whole dataset from an empty data/ (except the LoPucki table).

    python run_all.py                # pilot universe, end to end
    python run_all.py --full         # same pipeline over the full universe
    python run_all.py --from 3       # resume at a phase
    python run_all.py --only 4 5     # run selected phases

Every phase is idempotent: cached downloads and completed chunks are reused,
so an interrupted run continues rather than restarting.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import config as C  # noqa: E402


def _banner(msg: str) -> None:
    print("\n" + "#" * 72)
    print(f"# {msg}")
    print("#" * 72, flush=True)


def phase_0() -> None:
    _banner("PHASE 0 - scaffold and bulk downloads")
    import download_bulk
    download_bulk.main("all")


def phase_1(force: bool = False) -> None:
    _banner("PHASE 1 - bankruptcy labels")
    import scan_submissions
    import phase1_labels
    scan_submissions.main(force=force)
    phase1_labels.main(force=force)


def phase_2(force: bool = False) -> None:
    _banner("PHASE 2 - firm universe and pilot sample")
    import phase2_universe
    phase2_universe.main(force=force)


def phase_3(full: bool = False, force: bool = False) -> None:
    _banner(f"PHASE 3 - fundamentals extraction ({'full' if full else 'pilot'})")
    import phase3_fundamentals
    phase3_fundamentals.main(full=full, force=force)   # raises if the gate fails


def phase_4(full: bool = False) -> None:
    _banner("PHASE 4 - ratio computation")
    import phase4_ratios
    import verify_ratios
    phase4_ratios.main(full=full)
    if not full and not verify_ratios.main():
        raise SystemExit("Phase 4 hand-recomputation gate failed")


def phase_5(full: bool = False, embargo: bool = False) -> None:
    _banner("PHASE 5 - labelling, sequences and split")
    import phase5_sequences
    res = phase5_sequences.main(full=full, embargo=embargo)
    if not res["audit_pass"]:
        raise SystemExit("Phase 5 leakage audit failed")


def phase_6() -> None:
    _banner("PHASE 6 - supplementary external datasets")
    import phase6_external
    phase6_external.main()


def phase_7(full: bool = False) -> None:
    _banner("PHASE 7 - final deliverables")
    import phase7_report
    import estimate_full_run
    phase7_report.main(full=full)
    estimate_full_run.main()


PHASES = {0: phase_0, 1: phase_1, 2: phase_2, 3: phase_3,
          4: phase_4, 5: phase_5, 6: phase_6, 7: phase_7}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="run over the full non-financial universe, not the pilot")
    ap.add_argument("--force", action="store_true",
                    help="ignore caches and rebuild")
    ap.add_argument("--embargo", action="store_true",
                    help="drop windows straddling a split boundary (stricter split)")
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--only", type=int, nargs="*", default=None)
    a = ap.parse_args()

    todo = sorted(a.only) if a.only else [p for p in PHASES if p >= a.start]
    t0 = time.time()
    for ph in todo:
        t = time.time()
        fn = PHASES[ph]
        kw = {}
        if ph in (1, 2):
            kw["force"] = a.force
        if ph == 3:
            kw.update(full=a.full, force=a.force)
        if ph in (4, 7):
            kw["full"] = a.full
        if ph == 5:
            kw.update(full=a.full, embargo=a.embargo)
        fn(**kw)
        print(f"\n[timing] phase {ph} took {time.time() - t:.1f}s")
    print(f"\n[timing] total {time.time() - t0:.1f}s")
    print("\nAll requested phases completed.")


if __name__ == "__main__":
    main()
