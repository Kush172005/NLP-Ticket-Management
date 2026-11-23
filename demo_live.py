"""Show the main M5 API behavior with a safe public-style example."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8000"


def get_json(path):
    with urlopen(BASE_URL + path, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post_json(path, value):
    body = json.dumps(value).encode("utf-8")
    request = Request(BASE_URL + path, data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def main():
    print("1. Service readiness")
    print(get_json("/ready"))

    print("\n2. Intent suggestion for a sample message")
    print(post_json("/predict", {"text": "my card payment is pending"}))

    print("\n3. Safe response to blank input")
    print(post_json("/predict", {"text": "   "}))

    print("\n4. Aggregate service metrics")
    print(get_json("/metrics"))


if __name__ == "__main__":
    try:
        main()
    except URLError as error:
        raise SystemExit(f"Could not reach {BASE_URL}. Start the service with: python api.py ({error})")
