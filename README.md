# Ticket Management System

**Banking support ticket classification · Industry Track · M1 and M2**

This version defines the business case and prepares Banking77 data for later modelling.
It contains no trained model, fitted vectorizer, prediction script or model-performance results.

## Start here

1. Read `docs/M1_PROBLEM_BRIEF.md` for the problem, users, business objective, success
   measures and feasibility analysis.
2. Open `reports/m2_report.html` in a browser for the M1–M2 evidence and charts.
3. Read `docs/DATA_CARD.md` for the dataset, preparation decisions, split policy and privacy limits.
4. Follow `docs/EVALUATION_GUIDE.md` for the demonstration and viva preparation.

The original project is preserved in Downloads. This folder is the M1–M2 evaluation version.
See `docs/PROJECT_AUDIT.md` for the changes and excluded M3 components.

## Setup

Python 3.11 or newer is required. This version was checked using Python 3.14.
From this folder, create an environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The official raw files and generated reports are supplied, so the evaluation needs no network
once dependencies are installed. If raw files are missing, restore them with:

```bash
python data_loader.py --download
```

The downloader checks fixed SHA-256 hashes and does not overwrite a modified source file.

## Reproduce M2

```bash
python m2_preprocess.py
python verify.py
python -m unittest discover -s tests -v
python demo.py
```

To show the cleaning of an actual public dataset example:

```bash
python demo.py --text "Is there a way to know when my card will arrive?"
```

The demo prints masked and cleaned text. It does not predict an intent or store entered text.

## Preparation pipeline

1. Verify the publisher's train/test CSVs, category list and license against pinned hashes.
2. Audit rows, labels, missing values and source duplicates.
3. Normalize text and mask supported contact/numeric patterns.
4. Exclude empty, conflicting and repeated normalized training examples.
5. Group exact text and lexical near-duplicates using a fixed word-trigram Jaccard rule.
6. Exclude training groups overlapping the official test text.
7. Split the retained training source into train/validation with grouped stratification, seed 42.
8. Save cleaned splits, quality checks, statistics, charts and source/code/output hashes.

All 3,080 official test examples keep their membership and labels. All exported splits
contain 77 intents. The pipeline checks zero cross-split exact text and defined duplicate-group
overlap. Semantic paraphrases and customer-level leakage cannot be ruled out from these fields.

The split uses one of seven grouped stratified folds for validation, approximately one seventh
of the retained training source. Grouping can change the exact fraction and label proportions.

## Files

| File / folder | Purpose |
|---|---|
| `config.py` | Paths, source revision, hashes and fixed preparation choices |
| `data_loader.py` | Verify and load separate official train/test files |
| `preprocessing.py` | Masking, normalization and duplicate grouping |
| `m2_preprocess.py` | Data audit, exclusions, split construction and exports |
| `reporting.py` | Static charts, HTML report and generated data card |
| `verify.py` | Independently check saved artifacts against source files |
| `demo.py` | Terminal walkthrough and text-cleaning demo |
| `data/raw/` | Publisher's original files, unmodified |
| `data/processed/` | Prepared train, validation and test CSVs |
| `reports/` | Evidence from the actual preprocessing run |
| `docs/` | M1 brief, data card, audit and evaluation guide |
| `presentation/` | Local evaluation slides |
| `tests/` | Regression checks for cleaning, grouping and source verification |

## Data source and limitations

Banking77 contains 13,083 English banking queries across 77 intents. It supports intent
classification, not a validated complete ticket lifecycle system. It has no sentiment,
priority, routing, summary or reply labels. No real-agent time saving has been measured.

Publisher: [PolyAI](https://github.com/PolyAI-LDN/task-specific-datasets).  
Paper: Casanueva et al. (2020), [Efficient Intent Detection with Dual Sentence Encoders](https://aclanthology.org/2020.nlp4convai-1.5/).  
Dataset license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), with the publisher's
license included in `data/raw/LICENSE.txt`. The source CSVs are unchanged. Processed files
change text and exclude training examples as documented in the data card.

Regex masking is incomplete. Names, addresses and unusual identifiers may remain. Keep raw
data separate, review redaction before sharing, and use public examples in the demonstration.
