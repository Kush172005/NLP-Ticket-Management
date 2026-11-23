# Ticket Management System

**Banking support ticket classification · Industry Track · M1–M5**

This project defines the business case, prepares Banking77 data, develops and evaluates intent
models, and provides a local API prototype.

## Start here

1. Read `docs/M1_PROBLEM_BRIEF.md` for the problem, users, business objective, success
   measures and feasibility analysis.
2. Open `reports/m2_report.html` in a browser for the M1–M2 evidence and charts.
3. Read `docs/DATA_CARD.md` for the dataset, preparation decisions, split policy and privacy limits.
4. Open `presentation/M1_M2_Evaluation.pptx` for the milestone presentation.
5. Read `docs/M3_MODEL_DEVELOPMENT.md` for the model comparison and results.
6. Read `docs/M4_EVALUATION.md` and `docs/M5_DEPLOYMENT.md` for evaluation and the local API prototype.

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

Train and compare the Milestone 3 models, or predict one query:

```bash
python train_models.py
python m4_evaluation.py
python predict_ticket.py "my card payment is pending"
```

Run the M5 local API and measure it from another terminal:

```bash
python api.py
python benchmark_api.py --requests 100
```

The API listens on `127.0.0.1` by default. It provides `/health`, `/ready`, `/metrics`, and
`POST /predict`. With the API running, open `http://127.0.0.1:8000` for the local ticket intelligence
dashboard, or run `python demo_live.py` in a second terminal for the guided terminal demonstration.
Open `http://127.0.0.1:8000/admin/review` for the bank-style review workflow. Successful
predictions are saved in an ignored local SQLite database; use sample text only. See
`docs/M5_DEPLOYMENT.md` for the review endpoints, request format, failure behavior and monitoring.
The workflow maps every dataset label to a department, then supports demo-agent assignment,
work-in-progress notes and resolution summaries. Department rules and demo agent names are local
prototype data, not verified bank policy or real employee accounts.

Training compares a majority guess, a word TF-IDF logistic regression baseline and a word+character
TF-IDF linear SVM. It chooses by validation macro F1, then evaluates the selected model once on test.
Milestone 4 checks a small SVM setting search, analyzes test errors, and runs controlled robustness
checks on validation messages. See `docs/M4_EVALUATION.md` for the results and limits. Inference
shows three suggested categories; its raw ranking scores are not probabilities.

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
| `api.py` | Local HTTP prediction service with health and metrics endpoints |
| `ticket_store.py` | Local SQLite ticket state, human review, agent work, resolution and audit events |
| `ticket_routing.py` | Centrally validated mapping for all 77 intents plus demo-agent choices |
| `docs/INTENT_DEPARTMENT_MAP.md` | Human-readable routing table for all 77 actual labels |
| `web/admin_review.html` | Bank operations queue, ticket detail drawer and lifecycle controls |
| `web/admin_review.js` | Review, routing, agent assignment, work notes, resolution and audit interactions |
| `web/index.html` | Responsive browser dashboard served by the local API |
| `web/project_journey.html` | M1–M5 project evidence, model comparison and measured results |
| `benchmark_api.py` | Sequential local API latency measurement |
| `demo_live.py` | Demonstrates API readiness, prediction, input failure handling, and metrics |
| `data/raw/` | Publisher's original files, unmodified |
| `data/processed/` | Prepared train, validation and test CSVs |
| `reports/` | Evidence from the actual preprocessing run |
| `docs/` | M1 brief, data card, audit, evaluation and deployment guides |
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
