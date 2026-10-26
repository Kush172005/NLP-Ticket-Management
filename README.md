# Banking Ticket Intent Classification

An NLP-based banking support ticket classification project using the official Banking77 dataset.

The model predicts the intent of a banking support message across 77 intent classes. The project includes data preprocessing, model comparison, evaluation, and single-ticket inference.

## Results

| Metric | Result |
|---|---:|
| Dataset | Banking77 |
| Intent classes | 77 |
| Official training rows | 10,003 |
| Official test rows | 3,080 |
| Processed training rows | 8,464 |
| Validation rows | 1,494 |
| Test accuracy | 89.25% |
| Test macro F1 | 89.26% |
| Test top-3 accuracy | 96.72% |
| Selected model | TF-IDF + calibrated LinearSVC |

These results are from the current local training and evaluation run. Reproduce them using the commands below.

## Dataset

Banking77 is a banking customer-service intent classification dataset introduced by PolyAI.

The local CSV files are expected at:

- `data/raw/banking77_train.csv`
- `data/raw/banking77_test.csv`

Each file contains `text` and `label` columns.

Dataset source: https://github.com/PolyAI-LDN/task-specific-datasets

Check the dataset's licence and redistribution terms before publishing the CSV files.

## How the pipeline works

1. Load the official training and test CSV files.
2. Validate the dataset structure and labels.
3. Clean the training data and remove duplicate/conflicting training examples.
4. Split the cleaned training data into training and validation sets.
5. Fit TF-IDF using the training data.
6. Compare baseline and candidate classifiers using validation results.
7. Evaluate the selected model on the separate official test split.
8. Save the model and evaluation reports.

The official test split should remain separate from model selection and training.

## Models compared

- Majority baseline
- TF-IDF + Multinomial Naive Bayes
- TF-IDF + Logistic Regression
- TF-IDF + calibrated LinearSVC

The current run selected TF-IDF + calibrated LinearSVC based on validation performance.

## Setup

Python 3.11 is recommended for the environment used in this project.

Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ensure the two raw Banking77 CSV files exist in `data/raw/` before preprocessing.

## Reproduce preprocessing and training

Run these commands from the project root:

```bash
python m2_preprocess.py
python m3_train.py
```

The preprocessing script generates processed splits and preprocessing reports. The training script compares models, evaluates the selected model, and saves the trained model and evaluation outputs.

## Predict a ticket

After training, run:

```bash
python predict_ticket.py
```

Example input:

```text
My card is not working when I try to make a payment.
```

The script prints the predicted intent, its confidence estimate, and the top three candidate intents.

## Generated artifacts

- `models/intent_model.joblib` — trained intent classifier
- `models/tfidf_word.joblib` — saved TF-IDF vectorizer from preprocessing
- `reports/m2_stats.json` — preprocessing statistics
- `reports/m2_eda.png` — exploratory data analysis chart
- `reports/m3_test_results.json` — test evaluation metrics
- `reports/m3_model_comparison.csv` — model comparison results
- `reports/m3_per_class_report.csv` — per-class evaluation
- `reports/training_evidence.txt` — dataset checks, model metadata, metrics, and file fingerprints

## Reproducibility and limitations

The reported metrics describe the current experiment and should be verified by rerunning the pipeline.

SHA-256 fingerprints identify file contents, but do not independently prove a model's training history. For stronger verification, preserve the dataset source, training code, environment/package versions, split-generation procedure, and evaluation output.

Confidence scores are estimates and are not guarantees of correctness. Similar intents can be confused, and low-confidence predictions may need human review.

## Project structure

```text
ticket_triage/
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── reports/
├── config.py
├── m2_preprocess.py
├── m3_train.py
├── predict_ticket.py
├── requirements.txt
└── README.md
```

## License

Add your project's licence after confirming the terms of the dataset and any third-party dependencies.
