"""Convert a locally cloned banking77 HF repo into data/raw/banking77_{train,test}.csv
with STRING intent labels (needed: routing/priority rules match on intent names).

Usage:  python import_local.py /path/to/cloned/banking77
Reads csv / parquet / json(l) files whose name contains 'train' or 'test'.
Label names come from the repo README.md YAML (dataset_info -> class_label -> names).
"""
import re
import sys
from pathlib import Path
import pandas as pd
from config import DATA_RAW


def label_names(root: Path):
    readme = root / "README.md"
    if not readme.exists():
        return None
    txt = readme.read_text(encoding="utf-8", errors="ignore")
    pairs = re.findall(r"^\s+'?(\d+)'?:\s*([A-Za-z0-9_\-]+)\s*$", txt, flags=re.M)
    names = {int(k): v for k, v in pairs}
    return names if len(names) == 77 else None


def read_any(p: Path):
    if p.suffix == ".csv":
        return pd.read_csv(p)
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    if p.suffix in (".json", ".jsonl"):
        return pd.read_json(p, lines=p.suffix == ".jsonl")
    return None


def main(root):
    root = Path(root)
    names = label_names(root)
    for split in ("train", "test"):
        files = [f for f in root.rglob("*") if f.is_file() and split in f.name.lower()
                 and f.suffix in (".csv", ".parquet", ".json", ".jsonl") and ".git" not in f.parts]
        if not files:
            sys.exit(f"No {split} file found under {root}. If files are tiny pointer text, "
                     f"run 'git lfs pull' inside the repo.")
        df = pd.concat([read_any(f) for f in files], ignore_index=True)[["text", "label"]]
        if pd.api.types.is_numeric_dtype(df.label):
            if names is None:
                sys.exit("Labels are integers but 77 label names were not found in README.md. "
                         "Use the PolyAI/banking77 repo instead (python data_loader.py --download).")
            df["label"] = df.label.map(names)
            assert df.label.notna().all(), "unmapped label ids"
        df.to_csv(DATA_RAW / f"banking77_{split}.csv", index=False)
        print(split, len(df), "rows,", df.label.nunique(), "intents")


if __name__ == "__main__":
    main(sys.argv[1])
