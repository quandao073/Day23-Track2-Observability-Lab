# Day 23 Lab Reflection

> Fill in each section. Grader reads the "What I'd change" paragraph closest.

**Student:** Đào Anh Quân - 2A202600028
**Submission date:** 2026-05-11
**Lab repo URL:** [Github](https://github.com/quandao073/Day23-Track2-Observability-Lab.git)

---

## 1. Hardware + setup output

Paste output of `python 00-setup/verify-docker.py`:

```
Docker:        OK  (29.4.0)
Compose v2:    OK  (5.1.2)
RAM available: 31.18 GB (OK)
Ports free:    OK
Report written: submission/setup-report.json
```

Setup report (`submission/setup-report.json`):
```json
{
  "docker": { "ok": true, "version": "29.4.0" },
  "compose_v2": { "ok": true, "version": "5.1.2" },
  "ram_gb_available": 31.18,
  "ram_ok": true,
  "required_ports": [8000, 9090, 9093, 3000, 3100, 16686, 4317, 4318, 8888],
  "bound_ports": [],
  "all_ports_free": true
}
```

---

## 2. Track 02 — Dashboards & Alerts

### 6 essential panels (screenshot)

See `submission/screenshots/06-dashboards-6-panels.png`.

Panels visible: Request Rate (RPS), Latency P50/P95/P99, Error Rate, GPU Utilization, Token Throughput (input/output), In-Flight Requests.

### Burn-rate panel

See `submission/screenshots/08-dashboards-SLO-burn-rate.png`.

SLO: 99.5% success rate. Multi-window burn-rate: Fast burn (5m + 1h > 14.4×), Slow burn (30m + 6h > 6×). With zero errors the burn rate showed 0.0 — confirming the recording rule fix (`or vector(0)`) was necessary for the metric to resolve instead of returning empty.

### Cost & Tokens panel

See `submission/screenshots/07-dashboards-cost-and-tokens.png`.

### Alert fire + resolve

| When | What | Evidence |
|---|---|---|
| T0 | killed `day23-app` via `make alert` | — |
| T0+60s | `ServiceDown` fired in Alertmanager | `submission/screenshots/09-alertmanager-firing.png` |
| T1+90s | app restored by script | — |
| T1+120s | alert resolved in Alertmanager UI | `submission/screenshots/09-alertmanager-firing.png` |

**Note (checkpoint #11 — Slack):** Alertmanager v0.27.0 does not evaluate `{{ env "SLACK_WEBHOOK_URL" }}` in `api_url` config fields — template functions only work in notification bodies, not config values — causing `unsupported scheme "" for URL` on startup. Fixed by using `webhook_configs` with a local dummy receiver so alertmanager starts and routes alerts correctly. Alert routing confirmed via Alertmanager UI. A real Slack webhook would be wired by setting the URL directly in `alertmanager.yml`.

### One thing surprised me about Prometheus / Grafana

The datasource UID mismatch was unexpected — Grafana auto-generates a random UID (e.g. `PBFA97CFB590B2093`) when the provisioning YAML doesn't declare one, but dashboard JSONs hardcode `uid: "prometheus"`. All panels showed "No data" silently without any error message, making it look like a query problem rather than a datasource wiring issue. Adding `uid: prometheus` to the provisioning file fixed it immediately.

---

## 3. Track 03 — Tracing & Logs

### One trace screenshot from Jaeger

See `submission/screenshots/10-jaeger-trace.png` showing `predict → embed-text, vector-search, generate-tokens` spans.
See `submission/screenshots/11-jaeger-span-attrs.png` showing GenAI semantic convention attributes.

### Log line correlated to trace

```json
{
  "model": "llama3-mock",
  "input_tokens": 4,
  "output_tokens": 44,
  "quality": 0.77,
  "duration_seconds": 0.3625,
  "trace_id": "b5f5b8e6736741b40afb384da6df4cf1",
  "event": "prediction served",
  "level": "info",
  "timestamp": "2026-05-11T13:50:20.430328Z"
}
```

The `trace_id` `b5f5b8e6736741b40afb384da6df4cf1` links directly to the Jaeger trace for this request. Clicking the trace in Jaeger shows the full span tree with `embed-text` (5ms), `vector-search` (10ms), and `generate-tokens` (variable) as children of the root `predict` span.

### Tail-sampling math

Policy configuration (from `otel-config.yaml`):
- **keep-errors**: 100% of traces with `status_code == ERROR`
- **keep-slow**: 100% of traces with span duration > 2000ms
- **probabilistic-1pct**: 1% of remaining healthy traces

**Calculation** (at ~17 req/sec observed load):
```
Total traces/sec:    17
Error rate 2%:        0.34 traces/sec → keep 100% = 0.34/sec
Slow (>2s) 1%:        0.17 traces/sec → keep 100% = 0.17/sec
Healthy 97%:         16.49 traces/sec → keep 1%   = 0.16/sec

Total kept:  0.34 + 0.17 + 0.16 ≈ 0.67 traces/sec
Fraction:    0.67 / 17 ≈ 3.9%

→ ~96% of traffic is dropped, but 100% of errors and slow requests are retained.
```

This design is critical: when a model starts failing, you lose zero diagnostic traces. The healthy baseline traffic is sampled at 1% purely to retain representative latency distributions for capacity planning — not for debugging.

---

## 4. Track 04 — Drift Detection

### PSI scores

`04-drift-detection/reports/drift-summary.json`:

```json
{
  "prompt_length": {
    "psi": 3.461,
    "kl": 1.7982,
    "ks_stat": 0.702,
    "ks_pvalue": 0.0,
    "drift": "yes"
  },
  "embedding_norm": {
    "psi": 0.0187,
    "kl": 0.0324,
    "ks_stat": 0.052,
    "ks_pvalue": 0.133853,
    "drift": "no"
  },
  "response_length": {
    "psi": 0.0162,
    "kl": 0.0178,
    "ks_stat": 0.056,
    "ks_pvalue": 0.086899,
    "drift": "no"
  },
  "response_quality": {
    "psi": 8.8486,
    "kl": 13.5011,
    "ks_stat": 0.941,
    "ks_pvalue": 0.0,
    "drift": "yes"
  }
}
```

### Which test fits which feature?

| Feature | Test | Lý do |
|---------|------|-------|
| `prompt_length` | **PSI** | Continuous, bounded integer. PSI bins the distribution and detects any marginal shift — standard choice in production ML monitoring pipelines where you want a single number to threshold on. |
| `embedding_norm` | **KS (Kolmogorov-Smirnov)** | Can be multimodal (different content clusters have different norm ranges). KS makes no assumption about the distribution shape and tests CDF divergence directly. |
| `response_length` | **PSI** | Similar rationale to `prompt_length` — discrete count variable, PSI is interpretable (< 0.1 = no drift, 0.1–0.2 = moderate, > 0.2 = significant). |
| `response_quality` | **KL Divergence** | Quality score is a model output, not an input feature. KL divergence is asymmetric: it measures how much the *current* distribution diverges from the *reference* (ground truth). This asymmetry is exactly what we want — the reference distribution is the correct behavior, and any deviation is a penalty. |

Note: **MMD (Maximum Mean Discrepancy)** would be most appropriate for detecting joint multivariate drift across all features simultaneously, because PSI/KL/KS test each feature independently and can miss correlated shifts (e.g., prompt_length up *and* quality down together = a specific user cohort change, not random noise).

---

## 5. Track 05 — Cross-Day Integration

### Which prior-day metric was hardest to expose? Why?

The hardest metric to expose is **Day 18 (Lakehouse / Spark)**. Unlike Qdrant (which has a built-in Prometheus `/metrics` endpoint) or llama.cpp (which exposes metrics via a simple HTTP server), Spark requires configuring a JMX exporter as a Java agent attached to the Spark executor JVM, then running a separate `jmx_prometheus_javaagent` sidecar to translate JMX MBeans into Prometheus format. The multi-step setup (custom `spark-env.sh`, sidecar port, firewall rules) makes it brittle compared to the pull-based scrape model the rest of the stack uses. In practice, teams often resort to Pushgateway instead — Spark jobs push metrics at task completion rather than exposing a continuously scraped endpoint.

For this lab, **Day 19 (Qdrant vector store)** was connected via the stub script `monitor-day19-vector-store.py`, which exposes `day19_qdrant_collections = 3` and `day19_qdrant_search_total` on port 9101. Prometheus scrapes this target as job `day19-stub`, and the cross-day dashboard panel "Day 19 — Qdrant Collections" renders with live data.

---

## 6. The single change that mattered most

**Fixing the SLO recording rules to handle zero-error states.**

The original recording rule for `inference:fail_ratio:rate5m` was:

```
sum(rate(inference_requests_total{status="error"}[5m]))
/
sum(rate(inference_requests_total[5m]))
```

When there are no errors — which is the normal, healthy state — the numerator returns an empty result set (no time series with `status="error"` exist). In PromQL, dividing an empty vector by a non-empty vector yields empty, not zero. The SLO burn-rate dashboard consequently showed no data at all for burn rate panels, which looks identical to a broken dashboard. A grader or on-call engineer seeing blank panels would have no idea whether the SLO was being met or the instrumentation was broken.

The fix was adding `or vector(0)` to the numerator:

```
(sum(rate(inference_requests_total{status="error"}[5m])) or vector(0))
/
sum(rate(inference_requests_total[5m]))
```

Now the ratio evaluates to `0.0` when there are no errors — burn rate = 0, error budget remaining = 100%. This is the correct semantic: a healthy system *should* show a burn rate near zero, not a missing panel. The distinction matters operationally: "no data" triggers an investigation, "burn rate = 0" triggers confidence. This connects directly to the deck's point that observability is about *reducing time-to-understanding*, and a blank panel increases that time to infinity.

