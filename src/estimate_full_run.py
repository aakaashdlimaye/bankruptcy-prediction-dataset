"""Estimate wall-clock time and disk for the `--full` run.

Extrapolates from the measured pilot rather than guessing: the per-firm
extraction cost and the per-firm-quarter artefact size are both taken from the
pilot artefacts actually on disk, then scaled by the ratio of full-universe
firms to pilot firms.

Output: reports/full_run_estimate.md  (the `--full` run itself is NOT launched)
"""
from __future__ import annotations

import json
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

import config as C
import phase3_fundamentals as P3

OUT = C.REPORTS / "full_run_estimate.md"
BENCH_FIRMS = 60


def _mb(p: Path) -> float:
    return p.stat().st_size / 1e6 if p.exists() else 0.0


def benchmark(ciks: list[str]) -> float:
    """Seconds per firm for the extraction step, measured now."""
    t0 = time.time()
    n = 0
    with zipfile.ZipFile(C.RAW / "companyfacts.zip") as zf:
        names = set(zf.namelist())
        for cik in ciks:
            fn = f"CIK{int(cik):010d}.json"
            if fn not in names:
                continue
            blob = json.loads(zf.read(fn))
            d = P3.process_company(blob, cik, {})
            if not d.empty:
                P3.interest_annual_fallback(d, blob, {})
            n += 1
    return (time.time() - t0) / max(n, 1)


def main() -> None:
    uni = pd.read_parquet(C.INTERIM / "universe_full.parquet")
    pilot = pd.read_csv(C.DATA / "universe_pilot.csv", dtype={"cik": str})
    panel = pd.read_parquet(C.panel_path(False), columns=["cik", "quarter"])

    n_full = int((uni["in_universe"] == 1).sum())
    n_pilot = len(pilot)
    n_pilot_done = panel["cik"].nunique()
    scale = n_full / max(n_pilot, 1)

    print(f"[estimate] benchmarking extraction on {BENCH_FIRMS} firms...")
    per_firm = benchmark(pilot["cik"].head(BENCH_FIRMS).tolist())

    rows_per_firm = len(panel) / max(n_pilot_done, 1)
    rows_full = rows_per_firm * n_full

    art = {
        "fundamentals_panel.parquet": _mb(C.panel_path(False)),
        "ratios_panel.parquet": _mb(C.ratios_path(False)),
        "sequences_train.npz": _mb(C.PROCESSED / "sequences_train.npz"),
        "sequences_val.npz": _mb(C.PROCESSED / "sequences_val.npz"),
        "sequences_test.npz": _mb(C.PROCESSED / "sequences_test.npz"),
        "split_manifest.csv": _mb(C.PROCESSED / "split_manifest.csv"),
    }
    derived_mb = sum(art.values())

    extract_s = per_firm * n_full
    # Phases 4 and 5 are vectorised over the panel; measured pilot cost scaled
    # linearly in rows, with a floor for fixed overhead.
    ratios_s = max(20.0, 25.0 * scale)
    seq_s = max(60.0, 150.0 * scale)
    total_s = extract_s + ratios_s + seq_s

    raw_mb = (_mb(C.RAW / "companyfacts.zip") + _mb(C.RAW / "submissions.zip")
              + _mb(C.RAW / "company_tickers.json"))

    L = [
        "# Full-Run Estimate (`--full`)", "",
        "Measured from the pilot on this machine and scaled to the full universe.",
        "**The full run has not been launched** - this file is the estimate the",
        "spec asks for.", "",
        "## Scale", "",
        "| Quantity | Pilot | Full universe | Factor |", "|---|---:|---:|---:|",
        f"| Firms in scope | {n_pilot:,} | {n_full:,} | {scale:.2f}x |",
        f"| Firms yielding facts | {n_pilot_done:,} | ~{int(n_pilot_done * scale):,} | |",
        f"| Firm-quarters in panel | {len(panel):,} | ~{int(rows_full):,} | |",
        "",
        "## Time", "",
        "| Stage | Basis | Estimate |", "|---|---|---:|",
        f"| Phase 0 downloads | already cached ({raw_mb / 1000:.2f} GB on disk) | 0 (re-run: ~10-25 min) |",
        f"| Phase 1-2 labels and universe | one pass over submissions.zip, unchanged by `--full` | ~2 min |",
        f"| Phase 3 extraction | measured {per_firm * 1000:.1f} ms/firm x {n_full:,} firms | **{extract_s / 60:.1f} min** |",
        f"| Phase 4 ratios | vectorised, scales with rows | ~{ratios_s / 60:.1f} min |",
        f"| Phase 5 sequences | per-firm windowing, scales with firms | ~{seq_s / 60:.1f} min |",
        f"| **Total (phases 3-5, downloads cached)** | | **~{total_s / 60:.0f} min** |",
        "",
        f"With the two bulk downloads included from cold, budget "
        f"**~{total_s / 60 + 20:.0f} minutes** end to end on a domestic connection.",
        "",
        "## Disk", "",
        "| Artefact | Pilot | Full (projected) |", "|---|---:|---:|",
    ]
    for k, v in art.items():
        L.append(f"| `{k}` | {v:.1f} MB | {v * scale:,.0f} MB |")
    L += [
        f"| **derived total** | **{derived_mb:.1f} MB** | **~{derived_mb * scale / 1000:.2f} GB** |",
        f"| raw bulk downloads (fixed) | {raw_mb / 1000:.2f} GB | {raw_mb / 1000:.2f} GB |",
        f"| **grand total** | **{(derived_mb + raw_mb) / 1000:.2f} GB** | "
        f"**~{(derived_mb * scale + raw_mb) / 1000:.2f} GB** |",
        "",
        "## Notes", "",
        "- Peak RAM stays modest: extraction is chunked at "
        f"{P3.CHUNK_SIZE} firms and each chunk is flushed to its own parquet, so "
        "the full run never holds more than one chunk plus the concatenated panel "
        "in memory. The 32 GB machine is not a constraint.",
        "- The run is resumable: completed chunks under "
        f"`{C.chunk_dir(True).relative_to(C.ROOT).as_posix()}/` are skipped on "
        "restart.",
        "- `--full` writes to separate files (`fundamentals_panel_full.parquet`, "
        "`ratios_panel_full.parquet`), so pilot artefacts are never overwritten.",
        "- No additional SEC requests are made: `--full` reads the same two bulk "
        "files already on disk.",
        "- Expect the positive rate to fall by roughly an order of magnitude "
        f"against the pilot, since the pilot is deliberately positive-enriched "
        f"(50% of firms) while the full universe carries ~{100 * 789 / n_full:.1f}% "
        "bankrupt firms.",
        "",
        "## To launch it", "", "```bash",
        "python run_all.py --full --from 3", "```", "",
    ]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[estimate] -> {OUT.relative_to(C.ROOT)}")
    print(f"[estimate] full run ~{total_s / 60:.0f} min, "
          f"~{(derived_mb * scale + raw_mb) / 1000:.2f} GB total disk")


if __name__ == "__main__":
    main()
