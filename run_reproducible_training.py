import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from importlib import metadata

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

BACKUP = REPORTS / "reproducibility_backups" / RUN_ID
LOG_PATH = REPORTS / f"reproducibility_run_{RUN_ID}.log"
MANIFEST_PATH = REPORTS / f"reproducibility_manifest_{RUN_ID}.json"

DATA_FILES = [
    ROOT / "data/raw/banking77_train.csv",
    ROOT / "data/raw/banking77_test.csv",
]

CODE_FILES = [
    ROOT / "config.py",
    ROOT / "data_loader.py",
    ROOT / "m2_preprocess.py",
    ROOT / "m3_train.py",
    ROOT / "predict_ticket.py",
    ROOT / "requirements.txt",
]

IMPORTANT_ARTIFACTS = [
    ROOT / "models/intent_model.joblib",
    ROOT / "models/tfidf_word.joblib",
    ROOT / "reports/m2_stats.json",
    ROOT / "reports/m3_test_results.json",
    ROOT / "reports/m3_model_comparison.csv",
    ROOT / "reports/m3_per_class_report.csv",
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def fingerprint(paths):
    result = {}
    for path in paths:
        if path.is_file():
            result[str(path.relative_to(ROOT))] = {
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        else:
            result[str(path.relative_to(ROOT))] = {
                "missing": True
            }
    return result

def read_csv_summary(path):
    import pandas as pd
    df = pd.read_csv(path)
    if not {"text", "label"}.issubset(df.columns):
        raise ValueError(f"Unexpected columns in {path}")
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "unique_labels": int(df["label"].nunique()),
        "missing_text_or_label": int(
            df[["text", "label"]].isnull().any(axis=1).sum()
        ),
    }

def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None

# Ensure the expected official CSV files exist.
for path in DATA_FILES:
    if not path.is_file():
        raise FileNotFoundError(f"Required dataset file missing: {path}")

dataset_summary = {
    str(path.relative_to(ROOT)): read_csv_summary(path)
    for path in DATA_FILES
}

# Check expected Banking77 file sizes in terms of row counts and labels.
expected = [
    ("data/raw/banking77_train.csv", 10003),
    ("data/raw/banking77_test.csv", 3080),
]
for name, expected_rows in expected:
    actual = dataset_summary[name]["rows"]
    if actual != expected_rows:
        raise ValueError(
            f"{name}: expected {expected_rows} rows, found {actual}"
        )
    if dataset_summary[name]["unique_labels"] != 77:
        raise ValueError(f"{name} does not contain all 77 labels")
    if dataset_summary[name]["missing_text_or_label"] != 0:
        raise ValueError(f"{name} has missing text/label values")

# Preserve existing model and report files before the fresh run.
BACKUP.mkdir(parents=True, exist_ok=True)
backed_up = []
for path in IMPORTANT_ARTIFACTS:
    if path.is_file():
        destination = BACKUP / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        backed_up.append(str(destination.relative_to(ROOT)))

dataset_before = fingerprint(DATA_FILES)
code_before = fingerprint(CODE_FILES)
log_lines = []
run_status = "started"
error = None

def run_stage(command, title):
    log_lines.append(f"\n===== {title} =====\n")
    log_lines.append("$ " + " ".join(command) + "\n")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_lines.append(result.stdout)
    print(result.stdout, end="")
    if result.returncode != 0:
        raise RuntimeError(
            f"{title} failed with exit code {result.returncode}"
        )

try:
    run_stage([sys.executable, "m2_preprocess.py"], "M2 PREPROCESSING")
    run_stage([sys.executable, "m3_train.py"], "M3 TRAINING AND EVALUATION")
    run_status = "success"
except Exception as exc:
    run_status = "failed"
    error = str(exc)
finally:
    LOG_PATH.write_text("".join(log_lines))

dataset_after = fingerprint(DATA_FILES)
code_after = fingerprint(CODE_FILES)

artifacts = []
for folder_name in ("models", "reports", "data/processed"):
    folder = ROOT / folder_name
    if folder.exists():
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            if "reproducibility_backups" in path.parts:
                continue
            if path in (LOG_PATH, MANIFEST_PATH):
                continue
            artifacts.append({
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            })

metrics = {}
metrics_path = ROOT / "reports/m3_test_results.json"
if metrics_path.exists():
    try:
        metrics = json.loads(metrics_path.read_text())
    except Exception as exc:
        metrics = {"read_error": str(exc)}

git_commit = None
git_status = None
try:
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    git_status = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
except Exception:
    pass

manifest = {
    "run_id": RUN_ID,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": run_status,
    "error": error,
    "project_directory": str(ROOT),
    "python_version": sys.version,
    "packages": {
        name: package_version(name)
        for name in [
            "pandas", "scikit-learn", "numpy",
            "scipy", "joblib", "matplotlib"
        ]
    },
    "dataset_description": (
        "Local CSVs named as official Banking77 train/test files. "
        "Hashes identify the files but do not independently authenticate "
        "their origin."
    ),
    "dataset_summary": dataset_summary,
    "dataset_hashes_before": dataset_before,
    "dataset_hashes_after": dataset_after,
    "dataset_unchanged_during_run": dataset_before == dataset_after,
    "code_hashes_before": code_before,
    "code_hashes_after": code_after,
    "code_unchanged_during_run": code_before == code_after,
    "backup_directory": str(BACKUP.relative_to(ROOT)),
    "backed_up_files": backed_up,
    "artifacts_after_run": artifacts,
    "evaluation_metrics": metrics,
    "training_log": str(LOG_PATH.relative_to(ROOT)),
    "git_commit": git_commit,
    "git_status_short": git_status,
}

MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")

print("\n===== REPRODUCIBILITY SUMMARY =====")
print("Status:", run_status)
print("Dataset unchanged:", manifest["dataset_unchanged_during_run"])
print("Code unchanged:", manifest["code_unchanged_during_run"])
print("Backup:", BACKUP.relative_to(ROOT))
print("Training log:", LOG_PATH.relative_to(ROOT))
print("Manifest:", MANIFEST_PATH.relative_to(ROOT))
print("Metrics:", json.dumps(metrics, indent=2))

if run_status != "success":
    raise SystemExit(error or "Training failed")
