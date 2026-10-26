"""M2 - Data preprocessing for the Ticket Triage Platform.

Steps: load -> audit -> clean -> dedupe -> stratified split -> TF-IDF features -> EDA -> save.
Run: python m2_preprocess.py
"""
import json
import re
import joblib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from config import DATA_PROC, MODELS, REPORTS, SEED
from data_loader import load_raw

CONTRACTIONS = {"can't": "cannot", "won't": "will not", "n't": " not", "'re": " are",
                "'ve": " have", "'ll": " will", "'m": " am", "'d": " would"}
URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")        # card-like numbers -> PII mask
NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")


def clean_text(s: str) -> str:
    """Light cleaning for classical models. Keeps negations/punctuation cues out of the way
    of sentiment (sentiment uses the *raw* text, classifier uses this cleaned text)."""
    s = str(s).lower().strip()
    s = URL_RE.sub(" <url> ", s)
    s = EMAIL_RE.sub(" <email> ", s)
    s = CARD_RE.sub(" <cardnum> ", s)          # mask PII before anything is stored
    for k, v in CONTRACTIONS.items():
        s = s.replace(k, v)
    s = NUM_RE.sub(" <num> ", s)
    s = re.sub(r"[^a-z<>\s]", " ", s)           # drop leftover punctuation / symbols
    s = re.sub(r"\s+", " ", s).strip()
    return s



def main():
    from pathlib import Path

    raw = Path("data/raw")
    train_path = raw / "banking77_train.csv"
    test_path = raw / "banking77_test.csv"

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            "Official Banking77 CSVs missing from data/raw/. "
            "Download the dataset first."
        )

    original_train = pd.read_csv(train_path)
    original_test = pd.read_csv(test_path)

    for name, frame in (("train", original_train), ("test", original_test)):
        if not {"text", "label"}.issubset(frame.columns):
            raise ValueError(f"Unexpected columns in {name}: {list(frame.columns)}")
        if frame["text"].isna().any() or frame["label"].isna().any():
            raise ValueError(f"Missing text/label values in official {name} data.")

    if len(original_train) != 10003 or len(original_test) != 3080:
        raise ValueError(
            f"Unexpected dataset sizes: train={len(original_train)}, "
            f"test={len(original_test)}"
        )

    stats = {
        "source": "Official Banking77 CSVs; official test kept separate",
        "raw_train_rows": int(len(original_train)),
        "raw_test_rows": int(len(original_test)),
        "n_classes": int(original_train.label.nunique()),
    }

    # Clean training data.
    train_df = original_train.copy()
    train_df["raw_len_words"] = train_df.text.str.split().str.len()
    train_df["clean_text"] = train_df.text.map(clean_text)
    train_df = train_df[train_df.clean_text.str.len() > 0].copy()

    before = len(train_df)
    train_df = train_df.drop_duplicates(
        subset=["clean_text", "label"]
    ).reset_index(drop=True)

    conflicts = train_df.groupby("clean_text").label.nunique()
    ambiguous = conflicts[conflicts > 1].index
    train_df = train_df[
        ~train_df.clean_text.isin(ambiguous)
    ].reset_index(drop=True)

    stats["train_duplicates_and_conflicts_removed"] = int(before - len(train_df))
    stats["clean_train_rows"] = int(len(train_df))

    # Split ONLY the official training data into train and validation.
    train, val = train_test_split(
        train_df,
        test_size=0.15,
        stratify=train_df.label,
        random_state=SEED,
    )

    # Keep every official test example; do not split or deduplicate it.
    test = original_test.copy()
    test["raw_len_words"] = test.text.str.split().str.len()
    test["clean_text"] = test.text.map(clean_text)

    if (test.clean_text.str.len() == 0).any():
        raise ValueError("Cleaning produced empty text in the official test set.")

    for name, part in (("train", train), ("val", val), ("test", test)):
        part.to_csv(DATA_PROC / f"{name}.csv", index=False)
        stats[f"{name}_rows"] = int(len(part))
        stats[f"{name}_labels"] = int(part.label.nunique())

    # Fit TF-IDF on training data only.
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    vec.fit(train.clean_text)
    joblib.dump(vec, MODELS / "tfidf_word.joblib")
    stats["tfidf_vocab_size"] = int(len(vec.vocabulary_))

    class_counts = train.label.value_counts()
    stats["class_min"] = int(class_counts.min())
    stats["class_max"] = int(class_counts.max())
    stats["imbalance_ratio"] = round(
        float(class_counts.max() / class_counts.min()), 2
    )
    stats["avg_words"] = round(float(train.raw_len_words.mean()), 1)
    stats["p95_words"] = float(train.raw_len_words.quantile(0.95))

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    class_counts.head(25).sort_values().plot.barh(ax=ax[0], color="#4C78A8")
    ax[0].set_title("Train: tickets per intent (top 25)")
    train.raw_len_words.plot.hist(bins=30, ax=ax[1], color="#F58518")
    ax[1].set_title("Training ticket length (words)")
    plt.tight_layout()
    plt.savefig(REPORTS / "m2_eda.png", dpi=130)
    plt.close(fig)

    with open(REPORTS / "m2_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))
    print("\nSUCCESS: Official Banking77 test set was kept separate.")


if __name__ == "__main__":
    main()
