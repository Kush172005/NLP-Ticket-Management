# Code walkthrough for the final viva

This guide explains what the **current codebase** does and why its main files exist. It is a walkthrough of the implementation, not an attribution of who personally wrote each line. For the viva, start with the flow below and open individual files only when asked.

## 1. The whole codebase in one picture

```text
M2 preparation
  data/raw → data_loader.py → preprocessing.py → m2_preprocess.py
           → data/processed/{train,val,test}.csv + reports

M3 and M4 modelling
  processed data → train_models.py → compare baseline and candidate
                 → m4_evaluation.py → tune, test errors, robustness
                 → models/banking77_intent_model.joblib + reports

M5 application
  web/index.html → POST /predict → api.py → clean_text + saved model
                                      ↓
                               ticket_store.py → SQLite
                                      ↓
  web/admin_review.html + admin_review.js → review → ticket_routing.py
                     → assign → start → notes → resolve → audit
```

**One-sentence explanation:** “We prepared the data, trained and evaluated a model, saved the complete feature-and-classifier pipeline, and connected it to a local human-reviewed ticket workflow.”

## 2. The five files to know first

| File | What it does | Why it exists |
|---|---|---|
| `preprocessing.py` | Masks patterns and normalizes text; also groups duplicates. | Keep cleaning consistent and reduce defined leakage. |
| `train_models.py` | Fits and compares majority, logistic and SVM approaches. | Establish a baseline and select a stronger candidate on validation. |
| `m4_evaluation.py` | Compares C values, analyzes errors and runs robustness checks. | Document optimization and model limitations. |
| `api.py` | Loads the model, serves the UI, validates requests and provides endpoints. | Make inference usable through a local application. |
| `ticket_store.py` and `ticket_routing.py` | Store human review and lifecycle; map final intents to departments. | Connect NLP suggestions to a simple, auditable workflow. |

## 3. Data and configuration files — M1/M2 foundation

### `config.py`

- Defines project directories (`ROOT`, `RAW`, `PROCESSED`, `REPORTS`), `SEED = 42`, seven validation folds and the lexical near-duplicate threshold.
- Lists the publisher source revision, file names and expected SHA-256 hashes.
- **Why:** one shared source of paths and fixed preparation choices helps reproduce the pipeline. A fixed seed supports repeatability, although exact results may also depend on library versions and platform.

### `data_loader.py`

- `sha256()` calculates a file fingerprint. `load_raw()` checks each source file against its expected hash, verifies the schema, row counts and label set, adds source row IDs and returns train/test frames.
- `download()` can retrieve missing pinned source files and checks their hashes. It refuses to overwrite modified existing files.
- **Why:** catch missing or changed input data rather than silently training on unexpected files.
- **Viva:** “A hash verifies the bytes match what we pinned; it does not prove the data is unbiased or free of sensitive information.”

### `preprocessing.py`

- `mask_text()` applies ordered regular-expression substitutions for supported contact and numeric patterns.
- `clean_text()` normalizes Unicode and text, masks supported patterns, lowercases, expands common contractions and removes punctuation/non-English characters while retaining useful words and negation.
- `duplicate_groups()` groups exact text and defined lexical near-duplicates. For longer text, the grouping uses word-trigram Jaccard similarity at the configured threshold; connections can be transitive.
- **Why:** more consistent text for training and inference; limited privacy protection; reduce specified duplicate overlap between splits.
- **Limit:** regex masking is not complete anonymization. Numbers can also carry useful meaning, so masking is a trade-off.
- **Follow-up:** Training CSVs already contain `clean_text`; inference calls the same `clean_text()` before passing text to the model. The saved scikit-learn pipeline begins with feature extraction, not this separate cleaning function.

### `m2_preprocess.py`

`prepare()` orchestrates the data preparation:

1. Load verified publisher training and test files.
2. Calculate basic quality and privacy-pattern counts; create masked and cleaned text.
3. Remove invalid/conflicting/duplicate training examples and exclude training groups linked to test text under the predefined duplicate rule.
4. Use `StratifiedGroupKFold` with seven folds and seed 42 to take a training/validation split from retained training-source rows.
5. Export the processed CSVs, removals, duplicate records, statistics and report artifacts.
6. Save a manifest of source, code and output fingerprints.

**Why:** separate data preparation from modelling and retain an auditable account of decisions. Test text was inspected for this predefined duplicate audit; test labels and scores were not used for model selection.

### `reporting.py`

- `build_reports()`, `write_data_card()` and `write_html()` produce the M2 report, data card and charts from saved statistics and splits.
- **Why:** make the exploration and preparation understandable to a reviewer without reading every script.
- **Caution:** it generates artifacts, so rerunning preprocessing may rewrite generated files. Do not regenerate reports during a time-limited demo unless needed.

### `verify.py`

- Checks source and manifest hashes, labels and split membership, re-derives masked/clean text, checks row accounting and cross-split exact/group overlap, and recomputes defined duplicate links.
- **Why:** independently validate the saved M2 artifacts against source data and preparation rules.
- An outdated API fingerprint was refreshed after the ticket workflow changed, with a note in the manifest. The M2 data and preprocessing fingerprints were not changed by that correction.
- **Limit:** passing verification checks these specific rules; it does not prove there are no semantic duplicates, all PII is removed, or the model is correct.

### `data/raw/` and `data/processed/`

- Raw: original Banking77 train and test CSVs, category list and license. Source files are pinned by hash.
- Processed: train, validation and test CSVs with row IDs, masked/clean text, labels and group IDs. These feed model scripts.
- **Why separate them:** preserve the publisher inputs and make the prepared model inputs explicit. Processed `masked_text` may still contain information that the regex did not detect.

### `docs/M1_PROBLEM_BRIEF.md` and `docs/DATA_CARD.md`

- Problem, users, targets, dataset provenance, fields, split decisions, privacy and limitations.
- Some wording describes the earlier M1–M2 submission and should be understood as a historical milestone description. The current application later added a prototype ticket lifecycle.

## 4. M3 — How training works in code

### `train_models.py`

**Functions to recognize:**

- `load_split(name)`: reads one processed CSV.
- `build_models()`: creates the three approaches.
- `score(model, texts, labels)`: calculates accuracy, macro F1 and weighted F1.
- `main()`: fits on train, compares on validation, chooses the non-dummy text model with the best validation macro F1, refits on train + validation, evaluates on test, saves the model and reports.

**The approaches:**

1. `DummyClassifier(strategy="most_frequent")`: predicts the most common training label.
2. `TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)` followed by `LogisticRegression(C=4, max_iter=1000, random_state=42)`.
3. `FeatureUnion` joins word TF-IDF `(1,2)` and `char_wb` TF-IDF `(3,5)` with `min_df=2`, `sublinear_tf=True` and up to 300,000 character features; `LinearSVC(C=1.0, random_state=42)` classifies the combined features.

**Why a pipeline and feature union?** A pipeline connects transformations and classifier so the same fitted features are used in prediction. The feature union combines word and character representations. Each candidate is fitted using training data during the validation comparison.

**Why `min_df=2`?** It excludes terms appearing in fewer than two training documents, reducing rare features and vocabulary size. This is a configuration choice; the repository does not contain a separate ablation proving it is optimal.

**Why `sublinear_tf=True`?** It reduces the effect of repeated occurrences through sublinear term-frequency scaling. This is a reasonable setting for TF-IDF, not a separately proven causal improvement in this project.

**Why set `random_state`?** To support reproducibility for components using randomness. Do not promise identical outputs across all software versions or machines solely because of the seed.

**Outputs:** `models/banking77_intent_model.joblib`, `reports/m3_experiment_log.csv`, `reports/m3_summary.json` and `reports/test_classification_report.json`.

**Critical follow-up:** The baseline and candidate differ in both features and classifier, so the recorded comparison measures their combined differences; it does not isolate the contribution of each change.

### `models/banking77_intent_model.joblib`

A serialized fitted scikit-learn pipeline. It contains the fitted feature extraction and classifier, not the original dataset or the separate `clean_text()` code. The server loads it with joblib and checks its classes against the category list.

**Why save it?** The application can make predictions without retraining each time. Use the pinned versions in `requirements.txt` for compatibility. Only load trusted model files: joblib uses Python serialization.

### `predict_ticket.py`

A small command-line inference example. It loads the saved model, cleans the supplied text, prints the top suggestion and two alternatives based on decision-score ranking.

```bash
python predict_ticket.py "my card payment is pending"
```

Scores rank categories but are not calibrated confidence probabilities. The API does not expose those scores as probabilities either.

## 5. M4 — Evaluation code

### `m4_evaluation.py`

- `make_model(c_value)`: builds the word + character TF-IDF and LinearSVC pipeline.
- `measures()`: calculates accuracy, macro F1 and weighted F1.
- `swap_one_pair()`: swaps two characters in a selected usable word for a simple typo stress test. Some messages without a suitable word are unchanged.
- `keep_first_half()`: truncates the input to its first half.
- `perturb()`: generates uppercase/punctuation, character-swap or truncation inputs, then applies the same cleaning function.
- `error_analysis()`: saves incorrect predictions, simple tags, confusion pairs and per-intent metrics.
- `main()`: trains C=0.5, 1.0 and 2.0 on train, compares on validation, applies the 0.001 macro-F1 retention rule, refits the selected setting on train + validation, saves the model and reports test/robustness evidence.

**Why is the robustness model separate?** The stress-check model is fitted on train only, leaving validation examples unseen during fitting. The final saved inference model is refitted on train + validation.

**Why not select on test?** It would make the test score part of development. M3 test results were already viewed, so M4 describes the test results rather than claiming a fresh final audit.

**Can we claim M4 improved the model?** No measurable improvement is claimed. C=2.0 had a tiny validation gain, below the chosen threshold; C=1.0 was retained. The threshold is a heuristic, not a significance test.

### M3/M4 report files

- `reports/m3_experiment_log.csv`, `m3_summary.json`: comparison and selected-model summary.
- `reports/test_classification_report.json`: test per-intent precision, recall and F1 from the M3 run.
- `reports/m4_experiment_log.csv`, `m4_summary.json`: C comparison, selected setting, test summary and stress checks.
- `reports/m4_test_errors.csv`: wrong predictions and simple tags; `m4_common_confusions.csv`: frequent pairs; `m4_test_per_intent.json`: class-level scores.
- **Why save them:** evidence for the viva and a record of decisions. Error tags describe patterns, not proven causes.

## 6. M5 — API, application and ticket workflow

### `api.py`: server and inference

The service uses Python's standard-library `ThreadingHTTPServer`, not Flask or FastAPI.

- `ServiceState.load_model()` loads the saved joblib pipeline at startup and checks that its classes match the dataset categories. Failure leaves the model unavailable.
- `ServiceState.record()` and `metrics()` maintain in-memory request, error, latency and label counters with a lock.
- `ApiHandler.do_GET()` serves the pages and read endpoints, including `/health`, `/ready`, `/metrics`, ticket lists and summaries.
- `ApiHandler.do_POST()` handles `/predict`: validate content type/body/text and limits, clean text, rank the 77 classes using `decision_function`, save the successful prediction as a local ticket, and return suggestion, alternatives, request ID, review flag and ticket ID.
- `handle_ticket_action()` dispatches review, assignment, work, note and resolution actions to the store. It maps validation/state errors to HTTP responses.
- `main()` initializes the local store, loads the model and starts the server on localhost by default.

**Typical questions:**

- *Why clean at inference?* To apply the same text-normalization logic that produced model inputs during preparation.
- *Why decision scores, not probabilities?* LinearSVC's scores are used to rank classes; they are not calibrated probabilities.
- *What if the model is unavailable?* `/ready` returns not ready and `/predict` returns 503.
- *What if saving fails?* The prediction request returns a server error instead of claiming a ticket was saved.
- *What does ThreadingHTTPServer mean?* It handles requests in separate threads; it is used for this simple local prototype, not claimed to be a hardened production server.

### `ticket_store.py`: data persistence and state

- `init_store()` creates SQLite `tickets`, `ticket_audit` and `ticket_notes` tables, indexes, and any missing lifecycle columns.
- `create_ticket()` saves the original message, AI label, alternatives and initial audit events with status `AWAITING_REVIEW`.
- `get_ticket()`, `list_tickets()` and `list_review_queue()` retrieve saved data; `serialize_ticket()` converts the stored record for JSON responses.
- `mark_review_started()` records the first review opening.
- `decide_ticket()` checks that the ticket is awaiting review. Approval keeps the AI intent; correction must be a valid different label. It stores the final intent, human decision, assigned department and audit events in a database transaction.
- `assign_agent()`, `start_ticket()`, `add_agent_note()` and `resolve_ticket()` enforce the required order and store state changes and events. A resolution requires a non-empty summary.
- `review_summary()`, `department_summary()` and `feedback_summary()` compute saved-ticket counts and review feedback.

**Why SQLite?** It is built into Python, simple to run locally, and stores records across restarts. It avoids introducing a separate database server for the evaluation. It is not evidence of production-scale performance.

**Why state checks?** They prevent steps such as starting work before an agent is assigned, or approving an already reviewed ticket. The HTTP layer returns a 409 for invalid lifecycle transitions.

**Why an audit trail?** It records the AI label, review decision, routing and subsequent human actions so the demo is explainable. The audit and raw message are stored locally; the prototype does not have real identity verification.

### `ticket_routing.py`: rules, not a second model

- `DEPARTMENT_INTENTS` lists each of the 77 intents under one of 10 prototype departments.
- Startup validation checks for missing, unknown or duplicate label assignments.
- `department_for_intent()` looks up the department. `DEMO_AGENTS` contains sample names for the interface.
- **Why:** demonstrate routing clearly without inventing training labels. Banking77 has no department or employee labels, so these rules are inferred from intent names and are **not** validated bank policy.

### Browser files in `web/`

- `index.html`: dashboard, ticket entry, prediction result and links to project evidence; JavaScript calls the local API and renders status/metrics. It uses the server's persisted ticket records alongside some browser-session history.
- `admin_review.html`: review queue page, controls, layout and modal containers.
- `admin_review.js`: fetches queue/labels/agents/metrics; renders ticket details; calls approve, correct, assign, start, note and resolve endpoints. User-visible content is escaped before insertion to reduce HTML injection from ticket text.
- `project_journey.html`: a presentation-friendly explanation of M1–M5, models, metrics and limitations. Its benchmark numbers are saved evidence, not necessarily live measurements.
- **Why split these responsibilities:** browser handles presentation and user actions; the API validates and executes actions; the store persists them. UI changes do not change the model's learned parameters.

**Privacy answer:** the browser sends messages to the local API; successful ticket text is persisted in local SQLite. Browser session history can also hold entries in the current tab. There is no authentication or automatic retention policy; use sample data.

### Important API routes

| Route | Purpose |
|---|---|
| `GET /health` | Process health and whether model is ready |
| `GET /ready` | Readiness; 503 if the model is unavailable |
| `GET /metrics` | In-memory aggregate prediction and error metrics |
| `POST /predict` | Validate, clean, classify and save a ticket |
| `GET /tickets/review-queue` | Tickets awaiting review |
| `GET /tickets`, `GET /tickets/{id}` | Saved tickets and an individual ticket with audit |
| `POST /tickets/{id}/approve` or `/correct` | Save human decision and route |
| `POST /tickets/{id}/assign`, `/start`, `/notes`, `/resolve` | Demonstrate ticket work and resolution |
| `GET /tickets/feedback`, `/tickets/operations` | Aggregate saved review and workflow information |

Additional routes provide labels, departments and demo agents; see `docs/M5_DEPLOYMENT.md`.

## 7. Demo, benchmark, tests and dependencies

### `demo.py` and `demo_live.py`

- `demo.py` is the older M2 preparation walkthrough. It shows data/cleaning evidence and does **not** make a model prediction.
- `demo_live.py` calls the running API to show readiness, one sample prediction, blank-input failure and metrics. The successful prediction creates a saved local sample ticket.

### `benchmark_api.py` and `reports/m5_benchmark.json`

- Sends sequential HTTP requests to the running local server, measures response times and records mean, median, p95, p99 and success rate.
- **Why:** provide basic local performance evidence. It sends the same default sample query repeatedly and is not a realistic concurrent production load test.
- **Side effect:** each successful `/predict` creates a ticket, and the script overwrites `reports/m5_benchmark.json`. Do not casually run 100 requests during the evaluation.

### `tests/test_preprocessing.py`

Ten unit tests check cleaning, negation, supported masking patterns, duplicates and source-file verification. Run:

```bash
python -m unittest discover -s tests -v
python verify.py
```

These tests focus on preparation; they are not a complete automated suite for the UI and ticket lifecycle. The full API flow and browser path were manually exercised during project review, including approval, correction and invalid transitions. Avoid saying every possible production case is tested.

### `requirements.txt`

Pins core packages: NumPy, pandas, scikit-learn, matplotlib and joblib. The HTTP server and SQLite use Python's standard library. Pinned versions help reproduce and load the model, but transitive dependencies and machine differences can still matter.

### Documentation and final artifacts

- `README.md`: setup, reproduction, demo and file overview.
- `docs/M3_MODEL_DEVELOPMENT.md`, `docs/M4_EVALUATION.md`, `docs/M5_DEPLOYMENT.md`: model, evaluation and deployment evidence.
- `docs/INTENT_DEPARTMENT_MAP.md`: readable intent-to-department mapping.
- `deliverables/IEEE_Project_Report.pdf` and `.docx`: final technical report.
- `presentation/`: existing presentation files; the checked PPTs cover M1–M2, so prepare updated final material.
- Git history: records milestone changes. Local edits need to be committed and pushed for the remote repository to contain them; verify access before submission.

## 8. Code-level questions to practise

**Q. If I click “Suggest Intent,” which functions are involved?**  
The browser sends `/predict`. `ApiHandler.do_POST()` validates the request, calls `clean_text()`, asks the loaded pipeline for decision scores, selects top labels, calls `create_ticket()` to persist them, and returns JSON for the UI to render.

**Q. If I correct the AI label, which part determines the department?**  
The review endpoint calls `decide_ticket()`. It validates the selected intent and passes the final label to `department_for_intent()` in `ticket_routing.py`; the result and audit events are saved in SQLite.

**Q. Why is the original prediction saved when corrected?**  
To compare what the model suggested with the human's final decision and retain an audit record. It does not mean the human decision is automatically verified ground truth.

**Q. Does changing HTML or CSS retrain the model?**  
No. Those files change presentation. Training is in `train_models.py` and `m4_evaluation.py`; the running API loads the saved joblib pipeline.

**Q. What is the difference between a CSV and SQLite here?**  
CSV files store the prepared benchmark dataset for training/evaluation. SQLite stores prototype ticket records, decisions, audit events and notes generated by the application.

**Q. What if the server restarts?**  
The saved ticket records remain in SQLite; in-memory API metrics reset. The server loads the saved model again at startup.

**Q. Why is there no automated deployment or login?**  
The deliverable is a local academic prototype. A real deployment would need authentication, authorization, HTTPS, rate limiting, retention controls, durable monitoring and approved infrastructure.

**Q. Why use a separate validation set instead of selecting on test?**  
Validation allows comparing candidates/settings without selecting based on the final benchmark test score. The test result was later viewed during M3, so M4's repeated test reporting is descriptive; a fresh holdout is preferable for independent final assessment.

**Q. Is every line of this project production-ready?**  
No. The prototype demonstrates a complete local workflow and measured benchmark performance. Production requires representative data, stronger testing, security/privacy controls, operations and real business validation.

## 9. Where to look during the viva

1. **Problem and dataset:** `docs/M1_PROBLEM_BRIEF.md`, `docs/DATA_CARD.md`.
2. **Model choices and training:** `train_models.py`, `docs/M3_MODEL_DEVELOPMENT.md`, `reports/m3_experiment_log.csv`.
3. **Optimization and robustness:** `m4_evaluation.py`, `docs/M4_EVALUATION.md`, `reports/m4_summary.json`.
4. **Application:** `api.py`, `ticket_store.py`, `ticket_routing.py`, `web/`.
5. **Final evidence:** `deliverables/IEEE_Project_Report.pdf`, `docs/M5_DEPLOYMENT.md` and the local demo.

Read the project guide first for the spoken story; use this file as a map when the evaluator opens the code.
