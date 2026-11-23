# M5: Deployment prototype

## What is running

`api.py` serves the saved intent model as a small, UI-free HTTP API. Interact with it from a terminal
using `curl` or `demo_live.py`; there is no browser dashboard. It listens only on your own computer
(`127.0.0.1:8000`) by default. This is a working local deployment prototype, not a public cloud
service. The model is loaded once when the server starts. Do not bind it to a public network: the
prototype has no login or rate limiting. Change the bind address only in a trusted development
environment.

Start it from the project folder:

```bash
python api.py
```

Send a prediction from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"my card payment is pending"}'
```

The response contains the top suggestion, two alternatives, a request ID, and a reminder for an
agent to review it. Ranking scores are not returned because they are not probabilities.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Shows whether the service process is alive and whether the model loaded. |
| `GET /ready` | Returns success only when the model is ready to answer requests. |
| `GET /metrics` | Shows request totals, failures, average latency, uptime and aggregate predicted-label counts. |
| `POST /predict` | Accepts `{"text":"..."}` and returns an intent suggestion. |

## Failure handling

- Missing or unreadable model: service stays alive for diagnosis, `/ready` reports not ready, and
  prediction requests return `503 model_unavailable`.
- Invalid JSON, missing/blank text, or text cleaned down to nothing: return a clear `400` error.
- Text over 4,000 characters or request body over 20,000 bytes: return `413` without inference.
- Wrong content type: return `415`; unknown route: return `404`.
- Unexpected model error: return a generic `500` with a request ID. Logs contain the error type,
  not the submitted message or stack trace.

No input message is written to the logs or stored by the API. Metrics are aggregated in memory and
reset when the process restarts. This is appropriate for a classroom prototype; a real service would
need durable monitoring, access controls, request-rate limits, HTTPS and an approved privacy design.

## Monitoring plan

Check `/ready` for availability and `/metrics` for successes, rejected requests, server failures,
average latency and prediction counts. Each prediction also emits a structured log with request ID,
HTTP status and latency, without the ticket text.

For a real pilot, add an external monitor for availability and latency; alert on repeated 5xx errors,
readiness failures or rising latency. Review aggregate prediction counts for sudden shifts. With
agent review, compare suggestions against the agent's final category to monitor quality and drift.
Do not retain raw customer text by default. Set thresholds only after measuring the actual approved
deployment environment and its normal traffic.

As an initial pilot plan, check readiness every minute and alert after two consecutive failures.
Review a five-minute window for server errors above 5% (only once there are at least 20 requests)
and p95 latency above 250 ms. These are starting thresholds to validate with pilot traffic, not
service guarantees; the current endpoint exposes counters and average latency, while a monitoring
system would calculate rolling error rates and percentiles from request logs.

## Measured local performance

Run the service in one terminal and `python benchmark_api.py --requests 100` in another. The script
makes sequential localhost calls using the same sample query, checks the readiness endpoint, and
reports success rate, median/p95/p99 response time and requests per second. It includes HTTP
connection overhead. This is a small local measurement, not a concurrency or production load test.
The measured values from this repository run are in `reports/m5_benchmark.json`.
On this Mac with Python 3.14.4, 100 sequential requests all succeeded. Mean latency was **0.96 ms**,
median was **0.88 ms**, p95 was **1.28 ms**, p99 was **2.15 ms**, and observed throughput was about
**1,042 requests per second**. These localhost numbers exclude real network distance and concurrent
traffic, so they should not be treated as cloud or production capacity.

The API was also manually exercised: a valid message returned `pending_card_payment`, and a blank
message returned HTTP 400 with a clear error. The metrics endpoint recorded the successful request
and client error without recording the submitted message.
