# Phase 5 Gate - Leakage Audit

Each check prints the evidence it is asserting on.

## (a) No firm-quarter index appears in two splits

```
window index = (cik, end_quarter); total windows = 18,000
distinct window indices                = 18,000
indices mapped to more than one split  = 0
split sizes: {'test': 3009, 'train': 12634, 'val': 2357}
```

**PASS** - every window index belongs to exactly one split, because the split is a function of the end quarter alone.

> **Disclosed property of stride-1 windowing.** The spec assigns a straddling window to the split of its end quarter rather than dropping it, so *input quarters* near a boundary can appear in windows on both sides. Windows affected: val 2,071 of 2,357, test 1,980 of 3,009. No label is shared. Run with `--embargo` to drop these windows entirely.

## (b) Winsorisation and scaler parameters derive only from train data

```
winsorisation fitted_on : period_end <= 2019-12-31
  rows used             : 29,717 of 40,691
  example bound         : r13_interest_coverage p01=-2044.264 p99=618.820
scaler fitted_on        : train split only (window end quarter <= 2019Q4)
  windows used          : 12,634
  max train end quarter : 2019Q4 (limit 2019Q4)
```

**PASS** - both parameter sets are fitted on period ends up to 2019-12-31 and applied unchanged to val and test.

## (c) No window contains quarters at or after its firm's event date

```
positive-firm windows checked            = 7,923
windows whose end quarter is past the    = 0
  firm's bankruptcy quarter
post-petition firm-quarters left in panel= 0
min quarters_to_event over positives     = 1.0
```

**PASS** - firm-quarters with a period end on or after the event date are removed before windowing, so no window can contain post-petition data.

## (d) Max quarter in train < min label-horizon quarter in val

```
max window end quarter in train      = 2019Q4
min window end quarter in val        = 2020Q1
min label-horizon quarter in val (h=1) = 2020Q2
comparison: 2019Q4 < 2020Q2 -> True
```

**PASS**

> **Disclosed property.** A train window ending 2019Q4 carries a y_4 label that resolves in 2020Q4, inside the validation period. This is inherent to multi-horizon labelling with an adjacent split and is reported rather than hidden; `--embargo` removes the affected boundary windows if a stricter protocol is wanted.

## Verdict

| Check | Result |
|---|---|
| (a) no firm-quarter index in two splits | PASS |
| (b) winsoriser and scaler from train only | PASS |
| (c) no window contains post-event quarters | PASS |
| (d) train max quarter < val min label horizon | PASS |

**Leakage audit: PASS**
