"""Fetch and verify the publisher's files without changing their contents."""
import argparse
import hashlib
import json
from urllib.request import urlopen

import pandas as pd

from config import RAW, SOURCE_BASE, SOURCE_FILES


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for name, (remote, expected) in SOURCE_FILES.items():
        target = RAW / name
        if target.exists():
            if sha256(target) != expected:
                raise ValueError(f"{name} has changed. Preserve it before downloading a fresh copy.")
            continue
        with urlopen(f"{SOURCE_BASE}/{remote}", timeout=60) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Unexpected source checksum: {name}")
        target.write_bytes(content)
    print("Official source files are present and verified.")


def load_raw():
    hashes = {}
    for name, (_, expected) in SOURCE_FILES.items():
        path = RAW / name
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Run: python data_loader.py --download")
        hashes[name] = sha256(path)
        if hashes[name] != expected:
            raise ValueError(f"Source verification failed for {name}")
    labels = set(json.loads((RAW / "categories.json").read_text()))
    frames = []
    for split, expected_rows in (("train", 10003), ("test", 3080)):
        frame = pd.read_csv(RAW / f"banking77_{split}.csv", keep_default_na=False)
        if list(frame.columns) != ["text", "category"] or len(frame) != expected_rows:
            raise ValueError(f"Unexpected {split} schema or row count")
        if set(frame.category) != labels or len(labels) != 77:
            raise ValueError(f"Unexpected {split} labels")
        frame = frame.rename(columns={"category": "label"})
        frame.insert(0, "row_id", [f"{split}_{i:05d}" for i in range(len(frame))])
        frame["source_split"] = split
        frames.append(frame)
    return *frames, hashes


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
    train, test, _ = load_raw()
    print(f"Verified: {len(train):,} training queries, {len(test):,} test queries, 77 intents.")
