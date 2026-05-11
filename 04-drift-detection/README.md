# 04 — Drift Detection (Evidently)

Compare a **baseline** distribution against a **current production** distribution. Compute PSI, KL, KS, MMD. Generate Evidently HTML report. Push the headline metric to Prometheus as a gauge.

## What students do

```bash
cd 04-drift-detection
python scripts/drift_detect.py
# Generates:
#   reports/drift-report.html
#   reports/drift-summary.json
#   pushes drift_psi_score gauge to Prometheus pushgateway (or skips if unavailable)
```

Then open the HTML report and inspect:

- Per-feature PSI score
- Distribution comparison plots
- Detected drift cause (data drift vs prediction drift)

## Cross-platform note

This track is **runnable on Colab** if you don't want Docker (the only one in the lab without a Compose dependency). See `colab/04_evidently_drift_colab.ipynb`.

## Submission checkpoint (15 pts)

- 5 pts: `reports/drift-report.html` exists and renders
- 5 pts: `drift-summary.json` shows PSI > 0.2 for at least one shifted feature
- 5 pts: REFLECTION.md explains which test fits each feature type (PSI vs KL vs KS vs MMD)
