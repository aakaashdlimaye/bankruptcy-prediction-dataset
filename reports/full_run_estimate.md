# Full-Run Estimate (`--full`)

Measured from the pilot on this machine and scaled to the full universe.
**The full run has not been launched** - this file is the estimate the
spec asks for.

## Scale

| Quantity | Pilot | Full universe | Factor |
|---|---:|---:|---:|
| Firms in scope | 1,578 | 10,758 | 6.82x |
| Firms yielding facts | 1,565 | ~10,669 | |
| Firm-quarters in panel | 40,691 | ~279,714 | |

## Time

| Stage | Basis | Estimate |
|---|---|---:|
| Phase 0 downloads | already cached (2.97 GB on disk) | 0 (re-run: ~10-25 min) |
| Phase 1-2 labels and universe | one pass over submissions.zip, unchanged by `--full` | ~2 min |
| Phase 3 extraction | measured 46.5 ms/firm x 10,758 firms | **8.3 min** |
| Phase 4 ratios | vectorised, scales with rows | ~2.8 min |
| Phase 5 sequences | per-firm windowing, scales with firms | ~17.0 min |
| **Total (phases 3-5, downloads cached)** | | **~28 min** |

With the two bulk downloads included from cold, budget **~48 minutes** end to end on a domestic connection.

## Disk

| Artefact | Pilot | Full (projected) |
|---|---:|---:|
| `fundamentals_panel.parquet` | 6.6 MB | 45 MB |
| `ratios_panel.parquet` | 16.5 MB | 112 MB |
| `sequences_train.npz` | 3.6 MB | 25 MB |
| `sequences_val.npz` | 1.0 MB | 7 MB |
| `sequences_test.npz` | 1.1 MB | 8 MB |
| `split_manifest.csv` | 1.7 MB | 12 MB |
| **derived total** | **30.5 MB** | **~0.21 GB** |
| raw bulk downloads (fixed) | 2.97 GB | 2.97 GB |
| **grand total** | **3.00 GB** | **~3.18 GB** |

## Notes

- Peak RAM stays modest: extraction is chunked at 200 firms and each chunk is flushed to its own parquet, so the full run never holds more than one chunk plus the concatenated panel in memory. The 32 GB machine is not a constraint.
- The run is resumable: completed chunks under `data/interim/_fund_chunks_full/` are skipped on restart.
- `--full` writes to separate files (`fundamentals_panel_full.parquet`, `ratios_panel_full.parquet`), so pilot artefacts are never overwritten.
- No additional SEC requests are made: `--full` reads the same two bulk files already on disk.
- Expect the positive rate to fall by roughly an order of magnitude against the pilot, since the pilot is deliberately positive-enriched (50% of firms) while the full universe carries ~7.3% bankrupt firms.

## To launch it

```bash
python run_all.py --full --from 3
```
