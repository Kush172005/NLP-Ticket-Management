"""Measure response time of the already-running local API."""
import argparse
import json
import platform
import statistics
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from config import REPORTS


def read_json(url, data=None):
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(url, data=data, headers=headers)
    with urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def percentile(values, fraction):
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def main():
    parser = argparse.ArgumentParser(description="Measure local ticket intent API response time.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--text", default="my card payment is pending")
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be at least 1")

    base = args.url.rstrip("/")
    _, health = read_json(base + "/ready")
    if health.get("status") != "ready":
        raise SystemExit("API is not ready. Start it with: python api.py")

    body = json.dumps({"text": args.text}).encode("utf-8")
    times = []
    successes = 0
    for _ in range(args.requests):
        started = time.perf_counter()
        status, result = read_json(base + "/predict", body)
        times.append((time.perf_counter() - started) * 1000)
        successes += int(status == 200 and "suggestion" in result)

    total_seconds = sum(times) / 1000
    result = {
        "url": base,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "requests": args.requests,
        "successful_predictions": successes,
        "success_rate": round(successes / args.requests, 4),
        "latency_ms": {
            "mean": round(statistics.mean(times), 2),
            "median": round(statistics.median(times), 2),
            "p95": round(percentile(times, 0.95), 2),
            "p99": round(percentile(times, 0.99), 2),
        },
        "throughput_requests_per_second": round(args.requests / total_seconds, 2),
        "sample_suggestion": result.get("suggestion"),
        "measurement_note": "Sequential localhost requests; includes HTTP connection overhead; not a production load test.",
    }
    _, result["service_metrics_after_run"] = read_json(base + "/metrics")
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "m5_benchmark.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except URLError as error:
        raise SystemExit(f"Could not reach the API: {error}. Start it with: python api.py")
