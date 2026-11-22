"""Paths and fixed choices for the M2 data preparation run."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
SEED = 42
VALIDATION_FOLDS = 7
NEAR_DUPLICATE_THRESHOLD = 0.85
SOURCE_REVISION = "57ec275d8078af65b7731c2a98be812d844a6d6b"
SOURCE_BASE = f"https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/{SOURCE_REVISION}"
SOURCE_FILES = {
    "banking77_train.csv": ("banking_data/train.csv", "b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b"),
    "banking77_test.csv": ("banking_data/test.csv", "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d"),
    "categories.json": ("banking_data/categories.json", "53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63"),
    "LICENSE.txt": ("LICENSE", "7e7170e3cebf88a9f60c7b8421418323c09304da1af4d5e90f4da1dc1c8a2661"),
}
