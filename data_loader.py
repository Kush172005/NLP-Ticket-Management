"""Load the official Banking77 dataset from local CSV files.

Expected files:
    data/raw/banking77_train.csv
    data/raw/banking77_test.csv

Both files must contain the columns: text,label.
If the files are missing, this loader raises an error rather than
creating replacement data.
"""

import argparse
import pandas as pd
from config import DATA_RAW


def download():
    """Download the official Banking77 dataset from Hugging Face."""
    from datasets import load_dataset

    ds = load_dataset("PolyAI/banking77", revision="refs/convert/parquet")
    label_names = ds["train"].features["label"].names

    DATA_RAW.mkdir(parents=True, exist_ok=True)

    for split in ("train", "test"):
        df = pd.DataFrame({
            "text": ds[split]["text"],
            "label": [label_names[i] for i in ds[split]["label"]],
        })
        df.to_csv(DATA_RAW / f"banking77_{split}.csv", index=False)
        print(f"{split}: {len(df)} rows saved")


def load_raw():
    """Load official local train and test CSVs."""
    train_path = DATA_RAW / "banking77_train.csv"
    test_path = DATA_RAW / "banking77_test.csv"

    missing = [str(p) for p in (train_path, test_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Official Banking77 CSV file(s) missing:\n"
            + "\n".join(missing)
            + "\nDownload them with: python data_loader.py --download"
        )

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    for name, df in (("train", train_df), ("test", test_df)):
        if not {"text", "label"}.issubset(df.columns):
            raise ValueError(
                f"{name} CSV must contain 'text' and 'label' columns."
            )
        if df[["text", "label"]].isnull().any().any():
            raise ValueError(f"{name} CSV contains missing text/label values.")

    combined = pd.concat(
        [train_df[["text", "label"]], test_df[["text", "label"]]],
        ignore_index=True,
    )
    return combined, "banking77 (official local CSVs)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download official Banking77 CSVs from Hugging Face",
    )
    args = parser.parse_args()

    if args.download:
        download()
    else:
        df, source = load_raw()
        print(f"Source: {source}")
        print(f"Rows: {len(df)}")
        print(f"Labels: {df['label'].nunique()}")
