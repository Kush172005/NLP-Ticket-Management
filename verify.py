"""Check saved M2 outputs against the original source and recorded evidence."""
import json
from itertools import combinations

import pandas as pd

from config import ROOT, PROCESSED, REPORTS
from data_loader import load_raw, sha256
from preprocessing import clean_text, mask_text, duplicate_groups


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify():
    raw_train, raw_test, _ = load_raw()
    raw = pd.concat([raw_train, raw_test]).set_index("row_id")
    stats = json.loads((REPORTS / "m2_stats.json").read_text())
    manifest = json.loads((REPORTS / "manifest.json").read_text())
    for section in ("code", "artifacts"):
        for relative, expected in manifest[section].items():
            require(sha256(ROOT / relative) == expected, f"Changed {section} file: {relative}. Rerun M2.")
    splits = {name: pd.read_csv(PROCESSED / f"{name}.csv", keep_default_na=False)
              for name in ("train", "val", "test")}
    for name, frame in splits.items():
        require(frame.row_id.is_unique, f"Repeated row IDs in {name}")
        require(set(frame.label) == set(raw_train.label), f"Label coverage failed: {name}")
        require("text" not in frame.columns, f"Unmasked original text exported in {name}")
        require(frame.clean_text.str.strip().ne("").all(), f"Empty cleaned text in {name}")
        require(len(frame) == stats["splits"][name]["rows"], f"Count mismatch in {name}")
        source = raw.loc[frame.row_id]
        require(frame.label.tolist() == source.label.tolist(), f"Changed labels in {name}")
        require(frame.clean_text.tolist() == source.text.map(clean_text).tolist(), f"Cleaning mismatch in {name}")
        require(frame.masked_text.tolist() == source.text.map(mask_text).tolist(), f"Masking mismatch in {name}")
        require(frame.source_split.tolist() == source.source_split.tolist(), f"Source membership mismatch in {name}")
    require(splits["test"].row_id.tolist() == raw_test.row_id.tolist(), "Official test membership/order changed")
    require(set(splits["train"].source_split) == {"train"}, "Test row leaked into training")
    require(set(splits["val"].source_split) == {"train"}, "Test row leaked into validation")
    for a, b in combinations(splits, 2):
        for column in ("row_id", "clean_text", "group_id"):
            require(not set(splits[a][column]) & set(splits[b][column]), f"{a}/{b} share {column}")
    removed = pd.read_csv(REPORTS / "removed_rows.csv")
    retained = set(splits["train"].row_id) | set(splits["val"].row_id)
    require(removed.row_id.is_unique, "A removed row has multiple reasons")
    require(not retained & set(removed.row_id), "Excluded row still appears in training/validation")
    require(retained | set(removed.row_id) == set(raw_train.row_id), "Training source is not fully accounted for")
    # Recompute lexical groups from saved text rather than trusting stored group IDs.
    all_saved = pd.concat([frame.assign(output_split=name) for name, frame in splits.items()], ignore_index=True)
    _, pairs = duplicate_groups(all_saved.clean_text.tolist())
    require(all(all_saved.iloc[a].output_split == all_saved.iloc[b].output_split for a, b, _, _ in pairs),
            "Cross-split lexical duplicate found in saved outputs")
    require(not (ROOT / "models").exists(), "Model folder found in this M1–M2 version")
    for name in ("m3_train.py", "predict_ticket.py", "analyze.py", "modules.py", "eval_rules.py", "run_reproducible_training.py"):
        require(not (ROOT / name).exists(), f"Out-of-scope script found: {name}")


if __name__ == "__main__":
    verify()
