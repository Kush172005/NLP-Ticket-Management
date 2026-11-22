"""Prepare the M2 evidence and data splits. Run from any working directory."""
import json
import platform
from importlib.metadata import version

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from config import (ROOT, PROCESSED, REPORTS, SEED, VALIDATION_FOLDS,
                    NEAR_DUPLICATE_THRESHOLD, SOURCE_BASE, SOURCE_FILES, SOURCE_REVISION)
from data_loader import load_raw, sha256
from preprocessing import PATTERNS, clean_text, mask_text, duplicate_groups


EXPORT_COLUMNS = ["row_id", "source_split", "masked_text", "clean_text", "label", "group_id", "raw_words", "clean_words"]


def describe_lengths(frame):
    return {column: {k: round(float(v), 3) for k, v in frame[column].describe(
        percentiles=[.25, .5, .75, .95, .99]).items()} for column in ("raw_words", "clean_words")}


def prepare():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    train, test, hashes = load_raw()
    raw_train = train.copy()
    quality = {}
    privacy = {}
    for name, frame in (("train", train), ("test", test)):
        quality[name] = {
            "rows": len(frame), "labels": frame.label.nunique(),
            "missing_or_blank_text": int(frame.text.str.strip().eq("").sum()),
            "missing_or_blank_label": int(frame.label.str.strip().eq("").sum()),
            "exact_raw_duplicate_rows": int(frame.duplicated(["text", "label"]).sum()),
            "non_ascii_rows": int(frame.text.map(lambda x: not x.isascii()).sum()),
        }
        if quality[name]["missing_or_blank_text"] or quality[name]["missing_or_blank_label"]:
            raise ValueError(f"Missing input in {name}")
        # Counts show pattern matches, not confirmed personal information.
        remaining = frame.text.copy()
        privacy[name] = {}
        for kind, pattern in PATTERNS.items():
            privacy[name][kind] = int(remaining.str.contains(pattern).sum())
            remaining = remaining.map(lambda text: pattern.sub(f" <{kind}> ", text))
        frame["masked_text"] = frame.text.map(mask_text)
        frame["clean_text"] = frame.text.map(clean_text)
        frame["raw_words"] = frame.text.str.split().str.len()
        frame["clean_words"] = frame.clean_text.str.split().str.len()

    removals = []

    def remove_rows(frame, mask, reason):
        removals.extend({"row_id": row.row_id, "reason": reason} for row in frame.loc[mask].itertuples())
        return frame.loc[~mask].copy()

    train = remove_rows(train, train.clean_text.eq(""), "empty_after_cleaning")
    conflicts = train.groupby("clean_text").label.nunique()
    train = remove_rows(train, train.clean_text.isin(conflicts[conflicts > 1].index), "conflicting_training_labels")
    train = remove_rows(train, train.duplicated(["clean_text", "label"]), "duplicate_training_text")
    if test.clean_text.eq("").any():
        raise ValueError("Empty official test example after cleaning")

    combined = pd.concat([train, test], ignore_index=True)
    groups, pairs = duplicate_groups(combined.clean_text.tolist())
    combined["group_id"] = [f"g{x:05d}" for x in groups]
    train = combined[combined.source_split.eq("train")].copy()
    test = combined[combined.source_split.eq("test")].copy()
    train = remove_rows(train, train.group_id.isin(set(test.group_id)), "overlap_with_official_test_group")
    if set(train.label) != set(test.label):
        raise ValueError("Cleaning removed an entire training intent")

    splitter = StratifiedGroupKFold(n_splits=VALIDATION_FOLDS, shuffle=True, random_state=SEED)
    tr_idx, va_idx = next(splitter.split(train.clean_text, train.label, train.group_id))
    splits = {"train": train.iloc[tr_idx].copy(), "val": train.iloc[va_idx].copy(), "test": test}
    checks = {}
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        checks[f"{a}_{b}_clean_text_overlap"] = len(set(splits[a].clean_text) & set(splits[b].clean_text))
        checks[f"{a}_{b}_duplicate_group_overlap"] = len(set(splits[a].group_id) & set(splits[b].group_id))
    if any(checks.values()):
        raise ValueError(f"Split overlap: {checks}")
    for name, frame in splits.items():
        if frame.label.nunique() != 77:
            raise ValueError(f"{name} does not represent all 77 intents")
        frame = frame.sort_values("row_id")
        frame[EXPORT_COLUMNS].to_csv(PROCESSED / f"{name}.csv", index=False)

    removal_frame = pd.DataFrame(removals, columns=["row_id", "reason"])
    removal_frame.to_csv(REPORTS / "removed_rows.csv", index=False)
    pair_frame = pd.DataFrame([
        {"left_id": combined.iloc[a].row_id, "right_id": combined.iloc[b].row_id,
         "similarity": score, "match": kind, "group_id": combined.iloc[a].group_id}
        for a, b, score, kind in pairs
    ], columns=["left_id", "right_id", "similarity", "match", "group_id"])
    pair_frame.to_csv(REPORTS / "duplicate_pairs.csv", index=False)

    counts = pd.DataFrame({"official_train": raw_train.label.value_counts(),
                           **{name: frame.label.value_counts() for name, frame in splits.items()}}).fillna(0).astype(int).sort_index()
    counts.index.name = "label"
    counts.to_csv(REPORTS / "class_distribution.csv")
    raw_lengths = raw_train.text.str.split().str.len()
    stats = {
        "milestones": ["M1", "M2"], "source_revision": SOURCE_REVISION,
        "source_hashes": hashes, "seed": SEED,
        "raw_quality": quality, "privacy_pattern_rows": privacy,
        "removals": {reason: int(n) for reason, n in removal_frame.reason.value_counts().items()},
        "removed_total": len(removals), "retained_official_train": len(train),
        "splits": {name: {"rows": len(frame), "labels": int(frame.label.nunique()),
                           "groups": int(frame.group_id.nunique())} for name, frame in splits.items()},
        "split_policy": "First fold of seeded 7-fold StratifiedGroupKFold on retained official training data",
        "near_duplicate_policy": {"representation": "word trigram sets", "jaccard_threshold": NEAR_DUPLICATE_THRESHOLD,
                                  "minimum_distinct_trigrams": 3, "transitive_groups": True},
        "duplicate_pairs": {kind: int(n) for kind, n in pair_frame.match.value_counts().items()},
        "leakage_checks": checks,
        "official_test_preserved": test.row_id.tolist() == [f"test_{i:05d}" for i in range(3080)],
        "official_test_internal_clean_duplicates": int(test.duplicated("clean_text").sum()),
        "official_test_conflicting_clean_groups": int((test.groupby("clean_text").label.nunique() > 1).sum()),
        "train_class_min": int(counts.train.min()), "train_class_max": int(counts.train.max()),
        "train_imbalance_ratio": round(float(counts.train.max() / counts.train.min()), 3),
        "official_train_class_min": int(counts.official_train.min()),
        "official_train_class_max": int(counts.official_train.max()),
        "length_statistics_official_train": {k: round(float(v), 3) for k, v in raw_lengths.describe(percentiles=[.5, .95, .99]).items()},
        "length_statistics": {name: describe_lengths(frame) for name, frame in splits.items()},
        "validation_fraction_of_retained_train": round(len(splits["val"]) / len(train), 4),
        "limitations": ["Exact and threshold-defined lexical overlap checks do not rule out every semantic paraphrase.",
                        "Regex masking does not detect all names, addresses or financial identifiers.",
                        "No customer, conversation or timestamp identifiers are available for group or temporal evaluation.",
                        "No classifier, vectorizer, prediction or model performance claim belongs to this run."],
    }
    (REPORTS / "m2_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    # Pick real examples that make the main cleaning decisions visible.
    selected = [0]
    for pattern in (r"(?i)\bnot\b", r"(?i)n't|can't|won't", r"\d", r"[^\x00-\x7f]", r"!"):
        candidates = raw_train[raw_train.text.str.contains(pattern, regex=True)]
        if not candidates.empty:
            selected.append(candidates.index[0])
    examples = raw_train.loc[list(dict.fromkeys(selected))].copy()
    pd.DataFrame({"row_id": examples.row_id, "before_masked": examples.text.map(mask_text),
                  "after": examples.text.map(clean_text), "label": examples.label}).to_csv(REPORTS / "cleaning_examples.csv", index=False)
    from reporting import build_reports
    build_reports(stats, counts, splits)
    paths = [p for folder in (PROCESSED, REPORTS) for p in sorted(folder.glob("*"))
             if p.is_file() and p.name != "manifest.json"]
    code_paths = sorted(ROOT.glob("*.py")) + [ROOT / "requirements.txt"]
    manifest = {
        "source_revision": SOURCE_REVISION,
        "sources": {name: {"url": f"{SOURCE_BASE}/{remote}", "sha256": hashes[name]}
                    for name, (remote, _) in SOURCE_FILES.items()},
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ("pandas", "numpy", "scikit-learn", "matplotlib")},
        "code": {p.name: sha256(p) for p in code_paths},
        "artifacts": {str(p.relative_to(ROOT)): sha256(p) for p in paths},
    }
    (REPORTS / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Source verified: 10,003 train + 3,080 test queries, 77 intents.")
    print("Training-source removals:", stats["removals"])
    print("Final splits:", stats["splits"])
    print("Cross-split exact and defined near-duplicate group overlap: 0")
    print("Reports:", REPORTS / "m2_report.html")
    return stats


if __name__ == "__main__":
    prepare()
