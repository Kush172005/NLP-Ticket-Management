# M2 + M3 — Understanding Guide

**Project:** AI-Powered Customer Support Intelligence & Ticket Triage Platform (Industry Track)

**M2:** Data Preprocessing  
**M3:** Model Development

**Current status:** Official Banking77 dataset integrated, preprocessing completed, intent classifier trained, and test results reproduced.

---

## 0. One-line pitch

A customer submits a support ticket and clicks **Analyze**. The system aims to return the ticket's intent, sentiment, priority, owning team, a one-line summary, and a suggested reply.

The intent classifier uses supervised machine learning. Other triage features use the project's rule-based and template-based components.

## 1. Business problem

Support agents manually read, categorize, prioritize, and route customer tickets. This can increase first-response time and cause misrouting.

For example, a stolen-card report should receive more urgent attention than a general question about changing a PIN.

The project's goal is to automate initial ticket triage while keeping a human agent involved in uncertain or high-risk cases.

## 2. Dataset: Banking77

The project uses the official Banking77 dataset associated with PolyAI.

- **Task:** Banking customer-query intent classification.
- **Intent classes:** 77.
- **Official training split:** 10,003 examples.
- **Official test split:** 3,080 examples.
- **Total:** 13,083 examples.
- **Input column:** `text`.
- **Target column:** `label`.

Dataset source: https://github.com/PolyAI-LDN/task-specific-datasets

### Why Banking77?

Banking77 contains short banking customer queries with fine-grained intent labels. Distinguishing between similar intents makes it a useful benchmark for text classification.

### What labels does it provide?

Banking77 provides an intent label for each query. It does not provide ground-truth labels for sentiment, priority, owning team, summaries, or suggested replies.

Therefore:

- **Intent classification:** supervised machine learning.
- **Sentiment, priority and routing:** rule-based components.
- **Summary and suggested reply:** implemented using the project's existing logic and templates, subject to verification against the source code.

These additional outputs must be evaluated separately from intent classification.

---

## 3. M2 — Data preprocessing

Main file: `m2_preprocess.py`

### 3.1 Current preprocessing pipeline

| Step | Implementation | Purpose |
|---|---|---|
| Load | Reads official Banking77 training and test CSV files | Preserves the original dataset split |
| Validate | Checks expected columns, row counts, missing values and label information | Detects malformed or incomplete data |
| Clean | Cleans text for modeling | Reduces unwanted text variation |
| Deduplicate | Removes duplicate/conflicting examples from training data | Reduces redundancy and conflicting supervision |
| Split | Creates training and validation sets from cleaned training data | Supports model selection without using the official test set |
| TF-IDF | Fits the vectorizer on training text only | Avoids learning vocabulary/IDF statistics from validation or test data |
| EDA | Generates class-distribution and text-length plots | Helps understand class imbalance and ticket length |
| Save | Writes processed splits, a vectorizer and reports | Supports reproducibility |

### 3.2 Actual dataset counts

| Dataset stage | Rows |
|---|---:|
| Official training split | 10,003 |
| Training rows removed during deduplication/conflict handling | 45 |
| Cleaned training data | 9,958 |
| Training subset | 8,464 |
| Validation subset | 1,494 |
| Official test split | 3,080 |
| Intent classes | 77 |
| TF-IDF vocabulary size | 9,036 |

The training and validation counts add up to 9,958. The official test split remains separate and retains all 3,080 examples.

The cleaned training data is split approximately 85% for training and 15% for validation.

### 3.3 Why keep the official test set separate?

- **Training set:** learns model parameters.
- **Validation set:** supports model comparison and model selection.
- **Official test set:** estimates final performance on examples not used for training or model selection.

Combining the official training and test files before splitting would remove the protection offered by the original test split.

The current pipeline reads the official test file separately. It cleans test text for modeling but does not apply the training-data deduplication step to remove test examples.

### 3.4 TF-IDF features

TF-IDF stands for *Term Frequency–Inverse Document Frequency*. It converts text into numerical features that represent how informative words are within the dataset.

The preprocessing script fits TF-IDF on training text only. Its reported vocabulary contains 9,036 features.

The exact n-gram and vectorizer settings should be verified in `m2_preprocess.py`.

### 3.5 Preprocessing outputs

- `data/processed/train.csv`
- `data/processed/val.csv`
- `data/processed/test.csv`
- `models/tfidf_word.joblib`
- `reports/m2_eda.png`
- `reports/m2_stats.json`

### 3.6 Privacy-related preprocessing

Banking applications must protect personal and financial information. Verify the current text-cleaning implementation before claiming that it masks all sensitive information, such as card numbers, email addresses, or other personal data.

Text cleaning alone does not guarantee comprehensive PII protection.

---

## 4. M3 — Model development

Main file: `m3_train.py`

### 4.1 Intent classifier

The classifier predicts one of 77 banking intents from a customer message.

The current experiment compares four candidates:

1. **Majority-class baseline:** predicts the most common training intent.
2. **TF-IDF + Multinomial Naive Bayes:** a fast text-classification baseline.
3. **TF-IDF + Logistic Regression:** a linear classifier for text features.
4. **TF-IDF + calibrated LinearSVC:** a linear support-vector classifier with a calibration layer for confidence estimates.

### 4.2 Actual model comparison

| Model | Validation accuracy | Validation macro-F1 |
|---|---:|---:|
| TF-IDF + calibrated LinearSVC | 88.89% | 88.99% |
| TF-IDF + Logistic Regression | 88.49% | 88.63% |
| TF-IDF + Naive Bayes | 84.81% | 83.25% |
| Majority baseline | 1.87% | 0.05% |

The selected model is **TF-IDF + calibrated LinearSVC**, based on validation performance.

### 4.3 Official test results

After model selection, the training script fits the selected model on the training and validation data and evaluates it on the separate official test split.

| Metric | Result |
|---|---:|
| Official test examples | 3,080 |
| Test accuracy | **89.25%** |
| Test macro-F1 | **89.26%** |
| Test top-3 accuracy | **96.72%** |
| Accuracy when confidence ≥ 0.5 | 94.82% |
| Share of predictions with confidence ≥ 0.5 | 88.38% |
| Accuracy when confidence < 0.5 | 46.93% |

These metrics were reproduced by running `python m3_train.py` again.

### 4.4 Understanding the metrics

- **Accuracy:** proportion of test examples classified correctly.
- **Macro-F1:** calculates F1 for each intent and averages the scores equally across intents.
- **Top-3 accuracy:** checks whether the correct intent appears among the three highest-ranked predictions.
- **Confidence-based accuracy:** measures performance for predictions above or below a chosen confidence threshold.

Confidence estimates are not guarantees of correctness. Low-confidence predictions may need human review.

### 4.5 Weakest intents

The current evaluation report identifies these lower-performing intents:

| Intent | Reported F1 |
|---|---:|
| `pending_transfer` | 72.2% |
| `balance_not_updated_after_bank_transfer` | 74.4% |
| `wrong_exchange_rate_for_cash_withdrawal` | 77.3% |
| `card_not_working` | 78.0% |
| `transfer_not_received_by_recipient` | 78.6% |

Some banking intents have similar meanings. For example, a pending transfer and a transfer that has not reached the recipient can be difficult to distinguish from a short message.

### 4.6 Most-confused intent pairs

The current report identifies these confusions:

- `verify_my_identity` → `why_verify_identity`: 6
- `wrong_exchange_rate_for_cash_withdrawal` → `card_payment_wrong_exchange_rate`: 5
- `card_acceptance` → `card_not_working`: 5
- `balance_not_updated_after_bank_transfer` → `transfer_not_received_by_recipient`: 4
- `top_up_reverted` → `top_up_failed`: 4

These results help identify areas for future improvement.

### 4.7 Saved model and reports

- `models/intent_model.joblib` — trained classifier pipeline.
- `models/tfidf_word.joblib` — vectorizer saved during preprocessing.
- `reports/m3_model_comparison.csv` — model comparison.
- `reports/m3_model_comparison.png` — comparison visualization.
- `reports/m3_per_class_report.csv` — per-intent evaluation.
- `reports/m3_test_results.json` — test metrics.
- `reports/training_evidence.txt` — dataset checks, model metadata, metrics and file fingerprints.

The saved classifier is a scikit-learn `Pipeline` with 77 learned classes.

---

## 5. Rule-based components

The project configuration describes additional triage components in `modules.py` and `config.py`. They are separate from the learned intent classifier.

Verify their current implementation and tests before claiming that every feature is complete.

### 5.1 Sentiment

The design uses a weighted word lexicon to estimate whether a message is positive, neutral, negative, or angry.

Potential signals include negative and positive words, negations, intensifiers, capital letters, and punctuation.

Banking77 does not provide sentiment labels, so intent-classification accuracy does not establish sentiment accuracy. Sentiment requires its own labelled evaluation set.

### 5.2 Team routing

The routing configuration maps intent-name patterns to support teams, including:

- Fraud & Security
- KYC & Account Support
- Billing & Disputes
- Payments & Transfers
- Cards Support
- General Support

This approach is transparent and can be adjusted without retraining the classifier. Routing accuracy still needs to be evaluated separately.

### 5.3 Priority

The original design proposes assigning priority using intent urgency, sentiment, and urgent phrases, with an override for high-risk security issues.

Test that critical cases, such as a stolen-card report, receive the intended priority even when the customer's wording is polite.

Priority is not a ground-truth label in Banking77. The classifier's 89.25% test accuracy does not establish priority accuracy.

### 5.4 Summary and suggested reply

The design describes an extractive summary and template-based suggested reply.

- An **extractive summary** selects informative text from the original message.
- A **template-based reply** assembles a response using predefined language and actions.

Verify these behaviours against `analyze.py` and `modules.py`. Do not claim these outputs are generated by an ML model unless the code confirms it.

### 5.5 Human review

The design proposes marking low-confidence predictions for human review.

The classifier's confidence results support investigating this approach. Verify that the application actually implements the review flag and corresponding workflow before describing it as operational.

---

## 6. Worked example

**Input:**

> My card is not working when I try to make a payment.

Actual output from `predict_ticket.py`:

| Field | Output |
|---|---|
| Predicted intent | `card_not_working` |
| Confidence estimate | 79.23% |
| Second candidate | `declined_card_payment` |
| Second candidate score | 10.26% |
| Third candidate | `card_payment_not_recognised` |
| Third candidate score | 2.21% |

This demonstrates that the saved model can classify an individual ticket.

The confidence values are estimates, not guarantees that the prediction is correct.

Sentiment, priority, owning team, summary and suggested reply should be taken from an actual run of the complete Analyze pipeline.

---

## 7. Limitations

1. **Single domain:** Banking77 contains banking-related queries, not every type of customer-support ticket.
2. **Single-intent framing:** real tickets can contain multiple issues, while the dataset generally provides one intent label per example.
3. **Rule-based outputs:** sentiment, priority and routing are not supervised using Banking77 labels.
4. **Short English messages:** the results do not establish performance on Hinglish, multilingual tickets, or all spelling variations.
5. **Similar intents:** some categories are difficult to distinguish from short messages.
6. **Confidence limitations:** a high confidence estimate does not guarantee correctness.
7. **Independent evaluation needed:** sentiment, priority, routing and reply quality need their own evaluation procedures.
8. **Privacy:** text cleaning alone does not prove that all personal or financial information is masked.
9. **Business impact not yet established:** model metrics do not themselves demonstrate reduced first-response time, lower misrouting, or money saved.

### Honest project status

> The intent-classification model was trained using the official Banking77 training split and evaluated on its separate official test split. The current experiment achieved 89.25% test accuracy, 89.26% macro-F1, and 96.72% top-3 accuracy. Additional triage features require their own implementation checks and evaluation.

---

## 8. Future improvements: M4–M6

### M4 — Evaluation and optimisation

- Tune TF-IDF and classifier hyperparameters using training and validation data.
- Compare word and character n-gram features.
- Evaluate a fine-tuned transformer model such as DistilBERT.
- Evaluate probability calibration and confidence thresholds.
- Build an independently labelled evaluation set for sentiment, priority and routing.
- Test privacy-related text cleaning.

### M5 — Deployment prototype

- Build an interface with an Analyze button.
- Expose analysis through a JSON API.
- Display predicted intent, confidence, and top candidate intents.
- Include human review for uncertain or high-risk tickets.
- Handle empty or malformed inputs safely.

### M6 — Final demo and report

- Demonstrate representative customer tickets.
- Document model performance and limitations.
- Measure end-to-end latency.
- Compare automated routing with human-reviewed assignments.
- Estimate time saved using measured results rather than unsupported assumptions.

---

## 9. How to run the project

Run commands from the project root.

Activate the existing virtual environment:

```bash
source .venv/bin/activate
```

Install dependencies if needed:

```bash
python -m pip install -r requirements.txt
```

Ensure these local dataset files exist:

```text
data/raw/banking77_train.csv
data/raw/banking77_test.csv
```

Run preprocessing:

```bash
python m2_preprocess.py
```

Train and evaluate the intent classifier:

```bash
python m3_train.py
```

Predict an individual ticket:

```bash
python predict_ticket.py
```

Run the rule evaluation if the required examples and dependencies are available:

```bash
python eval_rules.py
```

Run the complete analysis pipeline if its command-line interface is implemented:

```bash
python analyze.py "your ticket text"
```

Regenerate the architecture diagram:

```bash
python draw_diagram.py
```

**Dataset note:** The earlier Hugging Face `data_loader.py --download` approach failed. The current preprocessing workflow reads the local official Banking77 CSV files.

---

## 10. Evidence and reproducibility

The generated file `reports/training_evidence.txt` records:

- Dataset row counts and label counts.
- Dataset file SHA-256 fingerprints.
- Processed split sizes.
- Saved model type and number of learned classes.
- Model file fingerprint.
- Recorded test metrics.
- Source-code fingerprints.

The training command was run again, reproducing the same reported test accuracy and macro-F1.

SHA-256 hashes identify file contents; they do not independently prove a model's training history. For stronger reproducibility, preserve the dataset source, training code, dependency versions, split-generation procedure, and evaluation reports.

---

## 11. Final summary

M2 established a preprocessing pipeline that preserves the official Banking77 test split. M3 compared baseline and linear text-classification models, selected calibrated LinearSVC using validation performance, and evaluated the final classifier on the official test set.

**Current intent-classification results:**

- Test accuracy: **89.25%**
- Test macro-F1: **89.26%**
- Test top-3 accuracy: **96.72%**

These results describe the intent classifier's performance on Banking77. They do not, by themselves, establish the accuracy of sentiment, priority, routing, summaries, suggested replies, or the business impact of the complete platform.
