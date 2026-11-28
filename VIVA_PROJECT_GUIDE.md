# NLP final viva: understand and defend the project

**Project:** Banking support ticket intent classification and human-reviewed ticket management  
**Focus:** M3–M6, with a short M1–M2 recap  
**How to use this:** First read the one-minute explanation and the “numbers to remember.” Then practise the starred questions aloud. Finally, run the demo. You do not need to memorize every answer word for word.

---

## 1. The project in one minute

> Our project helps a support team understand and manage banking-related customer tickets. The NLP part takes one English customer message and suggests one of 77 banking intents. We trained it using the public Banking77 dataset. We compared a word-based TF-IDF and logistic regression baseline with a word-and-character TF-IDF and linear SVM model. The SVM performed better on validation, and the saved model achieved 91.40% accuracy and 91.42% macro F1 on the official test set. In the application, the AI suggestion is reviewed by a human, who can approve or correct it. Simple rules then map the final intent to a department, and a demo agent can work on and resolve the ticket. This is a local academic prototype: we have not tested it on a bank's real customer data or measured actual time savings.

**Keep the distinction clear:** the **model predicts an intent**. The **application** adds human review, rule-based routing, assignment, notes and resolution. The model does not generate answers, predict priority, decide which agent to assign, or resolve tickets automatically.

### One example from start to finish

1. Customer message: “My card payment is pending.”
2. The application validates and cleans the text.
3. Word and character TF-IDF convert it into numbers; the trained Linear SVM ranks the 77 intent labels.
4. The API suggests `pending_card_payment` and two alternative categories, then saves a local ticket.
5. The reviewer approves the suggestion or corrects it to another valid intent.
6. The **final reviewed intent** is mapped by a simple rule to a department, for example Card Payments Team.
7. A demo agent is assigned, work begins, a note is added, and a resolution summary is saved.
8. SQLite retains the ticket and audit events locally.

A model suggestion is not guaranteed to be correct. That is why the human review step comes before routing.

---

## 2. What was already covered: M1 and M2

### M1 — Problem and business case

- **Problem:** support staff have to read and categorize banking queries; similar messages can be difficult to distinguish and categorization can be inconsistent.
- **Users:** support agents, triage staff and managers. Customers may benefit indirectly, but that benefit remains unmeasured.
- **Objective:** assist categorization and make it more consistent. Faster handling is a goal to evaluate, not a proven result.
- **NLP task:** supervised, single-label, multiclass classification: one English query → one of 77 Banking77 intents.
- **Provisional benchmark targets:** accuracy and macro F1 of at least 0.80 each. A 20% reduction in median categorization time was proposed for a future pilot; it has **not** been measured.

### M2 — Data understanding and preparation

The project used **Banking77**, a public English banking intent dataset from PolyAI. Its original files contain **10,003 training-source queries and 3,080 official test queries**, with **77 intent labels**. The dataset is an NLP benchmark, not a bank's actual ticket database.

We checked source file hashes and labels, explored class counts and message lengths, and cleaned the text. Cleaning normalizes case and punctuation, expands common contractions, preserves negation, and masks selected URL, email, phone-like, card-like and numeric patterns. We do not remove stopwords, stem or truncate the text.

Of the 10,003 training-source rows, **98 were excluded**: 54 linked to defined test-overlap groups, 42 repeated normalized training texts, and 2 conflicting-label rows. The retained data was split with grouped stratification and seed 42. The final files are:

| Split | Rows | Purpose |
|---|---:|---|
| Train | 8,490 | Fit features and model |
| Validation | 1,415 | Compare approaches and settings |
| Official test | 3,080 | Report benchmark results |

All splits cover 77 intents. There is no cross-split exact normalized-text overlap or overlap according to the project's defined lexical near-duplicate grouping rule. **That does not prove there is no semantic, customer-level or temporal leakage.** Customer IDs and timestamps are not available. The predefined duplicate audit used test **text** to remove overlapping training groups; test labels and test performance were not used for model selection. The official test membership and labels remained unchanged.

**Transition to M3:** “At the end of M2, we had cleaned, documented splits. In M3, we trained models on them and compared a baseline with a candidate.”

### M1/M2 quick questions

**Q. Why Banking77?** It is publicly available, labelled for English banking intent classification, has 77 relevant categories and an official test split. It fits the project scope, though it may not represent real bank traffic.

**Q. Why keep words like ‘not’?** They can reverse the meaning of a short message. Removing stopwords blindly might remove important context.

**Q. Why three splits?** Train fits the model, validation guides choices, and test provides held-out reporting. This reduces the temptation to choose a model based on the final test score.

**Q. Why group duplicates?** Near-identical examples in different splits can make evaluation look better than generalization. We group exact and defined lexical near-duplicates; this is a limited check, not a guarantee against every paraphrase.

**Q. Is masking complete anonymization?** No. The pattern rules can miss names, addresses, account IDs and unusual formats. Use sample data in the demo.

---

## 3. M3 — Baseline and model development

### What we actually did

We compared three approaches on the **validation** split. Feature extractors and models were fitted on training text only for this comparison.

| Approach | Purpose | Validation accuracy | Validation macro F1 |
|---|---|---:|---:|
| Most-frequent intent | Simple reference floor | 1.91% | 0.05% |
| Word TF-IDF + logistic regression | Main baseline | 87.77% | 87.45% |
| Word + character TF-IDF + Linear SVM | Candidate | 90.81% | **90.56%** |

The candidate's validation macro F1 was **3.11 percentage points higher** than the logistic-regression baseline. We chose it using validation macro F1. Then we refitted that selected approach on train plus validation and reported its performance on the official test set: **91.40% accuracy, 91.42% macro F1 and 91.42% weighted F1**.

Important: the candidate changes **both** the features and classifier compared with the baseline. The comparison shows the combined approach performed better; it does **not** separately prove that character n-grams or SVM alone caused the improvement.

### Explain the techniques in plain words

- **Supervised learning:** learn from example messages with known intent labels.
- **TF-IDF:** converts text into numeric features. It gives weight to terms that occur in a message while reducing the relative importance of terms that appear across many documents. It is a statistical representation, not a complete understanding of meaning.
- **Word n-grams:** one-word and two-word sequences, such as “card” and “card payment.” They capture useful words and short phrases.
- **Character n-grams:** short sequences of characters. The candidate uses `char_wb` lengths 3–5, created within word boundaries. They can capture word-form and spelling patterns.
- **Logistic regression:** a linear classifier that learns a score for each class based on the input features. It is a strong, fast and explainable baseline for sparse text.
- **Linear SVM / `LinearSVC`:** a linear classifier that learns separating boundaries with a margin between categories. It works well with high-dimensional sparse text features and is practical on a laptop.
- **Pipeline:** keeps feature extraction and the classifier together, so the same fitted transformations are applied consistently during prediction. It also makes it easier to avoid fitting the vectorizer on validation or test data during selection.

### M3 viva questions and follow-ups

**★ Q. What is a baseline, and why did you use one?**  
A baseline is a reference model. Without one we cannot tell whether a candidate is actually useful. We used majority class as a simple floor and word TF-IDF plus logistic regression as a meaningful text baseline.

**Follow-up: Why not compare only with the majority class?**  
Always predicting one class is too weak to tell us whether the proposed NLP approach is competitive. The logistic-regression baseline provides a more realistic comparison.

**★ Q. Why TF-IDF instead of raw text?**  
The classifier needs numbers. TF-IDF gives a simple, sparse numeric representation of the words and patterns in the text. It is fast, easy to explain and works well as a text-classification starting point.

**Follow-up: What do TF and IDF mean?**  
Term frequency reflects how often a term occurs in a document. Inverse document frequency reduces the weight of terms appearing across many documents. The actual vectorizer also applies the configured normalization and sublinear term frequency.

**Q. Why word and character features together?**  
Word features capture terms and short phrases; character features add information about word forms and small spelling differences. Their combination was part of the candidate that performed better on validation. The experiment does not isolate their individual contributions.

**★ Q. Why choose SVM rather than logistic regression?**  
The combined word-and-character TF-IDF plus SVM candidate achieved higher validation macro F1 than our word-only logistic-regression baseline. Both are efficient for sparse text. We selected based on the evidence, not because SVM is always better.

**Q. Why not BERT or another transformer?**  
We chose a simpler and computationally cheaper approach that can run locally and is easier to explain. A transformer might improve performance, but we did not run a transformer comparison, so we cannot claim it would be better or worse here.

**Q. How many labels can it predict?**  
One top suggestion from 77 known intent labels, plus two alternatives for review. It is single-label classification, not multi-label classification.

**Q. What about an unrelated or multi-intent message?**  
The model still ranks the known labels. There is no validated out-of-scope rejection mechanism or multi-intent model, so the reviewer must be cautious. These are limitations and future work.

**Q. What does `C` in Linear SVM mean?**  
It controls the trade-off between a wider margin and penalizing training classification errors. A larger C penalizes errors more strongly; it does not guarantee better generalization.

**Q. Why are there alternatives but no confidence percentage?**  
`LinearSVC` returns decision scores that can rank classes, but those scores are not calibrated probabilities. Showing them as confidence percentages would be misleading.

**Q. Is the saved model only the SVM?**  
It is a saved scikit-learn pipeline: the fitted word/character TF-IDF features and the classifier are saved together using joblib.

---

## 4. M4 — Evaluation and optimization

### Metrics without jargon

- **Accuracy:** correct predictions / total predictions. On test, 2,815 of 3,080 predictions were correct: **91.40%**.
- **Precision for one intent:** among messages predicted as that intent, how many really belong to it? `TP / (TP + FP)`.
- **Recall for one intent:** among messages that really belong to that intent, how many did we find? `TP / (TP + FN)`.
- **F1 for one intent:** harmonic mean of precision and recall: `2 × precision × recall / (precision + recall)`.
- **Macro F1:** calculate F1 for each intent, then average all intents equally. Useful when classes have different sizes.
- **Weighted F1:** average class F1 scores weighted by the number of examples in each class.

**A simple example:** if the model predicts “card arrival” 10 times and 8 are correct, precision is 8/10 = 80%. If there are actually 20 card-arrival examples and it finds 8, recall is 8/20 = 40%. F1 combines both; accuracy alone does not reveal this particular category's weakness.

### Optimization: what changed and what did not

We compared three SVM C values using validation data:

| C | Validation macro F1 | Decision |
|---|---:|---|
| 0.5 | 90.54% | Lower |
| 1.0 | 90.56% | Retained |
| 2.0 | 90.59% | Only 0.03 percentage points higher |

The project's rule required a gain of at least **0.1 percentage points** to replace the existing setting. Because the observed gain was smaller, we retained C=1.0. This is an optimization experiment, **not evidence of a meaningful M4 improvement**. The threshold is a simple project decision, not a statistical significance test. A larger validation set, repeated splits or cross-validation would better assess whether such a tiny difference is reliable.

The test result had already been viewed after M3. Therefore, M4's test results and error analysis are treated as **descriptive**. We did not select C using test scores. A truly fresh external holdout would be valuable for a final independent estimate after development.

### Error analysis

The selected model made **265 mistakes out of 3,080** test examples. The error file records the true label, predicted label and simple tags. Recorded tags include **23 short-query cases**, **3 cases with a masked-value pattern**, and **239 other cases**. Tags may overlap; they describe observable patterns, not proven root causes. “Other” is broad, so the analysis is a starting point rather than a complete explanation of every error.

Examples of frequent confusions:

- `pending_transfer` predicted as `failed_transfer`: 4 cases.
- `top_up_failed` predicted as `top_up_reverted`: 4 cases.

A reasonable explanation is that the intents are similar and short messages may lack details. That is a hypothesis; the tags alone do not prove the cause.

### Robustness checks

The project perturbed validation text using a model trained on **train only**, so validation messages were not used in its fitting.

| Change to validation text | Accuracy after change | Prediction unchanged |
|---|---:|---:|
| Uppercase + punctuation | 90.81% | 100.00% |
| One character swap | 84.17% | 89.19% |
| First half only | 42.61% | 44.52% |

Formatting normalization explains the stability in the first check. The typo check shows a drop of **6.64 percentage points** from the original 90.81% validation accuracy. Truncation is a stress test: the shortened text may lose the information that justified the original label, so its original label is not necessarily still correct. These synthetic checks are not proof of performance on real customers or all typo patterns.

### M4 viva questions and follow-ups

**★ Q. Why macro F1 instead of only accuracy?**  
We have 77 categories with unequal counts. Accuracy can look good while some categories perform poorly. Macro F1 gives every category equal weight, so it helps expose weaker intents. We still report accuracy and per-intent results.

**Q. Is 91.42% macro F1 the same thing as 91.42% accuracy?**  
No. Accuracy counts overall correct predictions; macro F1 averages the precision/recall balance across classes. Their values happen to be close here.

**★ Q. What did optimization achieve?**  
We tested C=0.5, 1.0 and 2.0. C=2.0 was slightly higher on validation, but the gain was below our chosen threshold, so we kept C=1.0. We documented the iteration honestly rather than claiming an improvement we could not establish.

**Q. What is a confusion matrix?**  
A table showing true classes against predicted classes. Our common-confusions CSV gives the most frequent true-label/predicted-label mistake pairs; the per-intent report gives class-level metrics.

**Q. What is overfitting?**  
When a model fits patterns in training data that do not generalize well to new data. Separate validation/test splits and regularization help assess or limit it, but do not eliminate it.

**Q. What is data leakage?**  
Information that would not be available at prediction time improperly influences model fitting or selection. Examples include fitting TF-IDF on test data or allowing duplicate messages across splits. Our checks address specified overlap and fit features on the appropriate training data; they cannot rule out every form of leakage.

**Q. Did you use the test data more than once?**  
The M3 result was viewed and M4 later reported test metrics and errors again. We did not use those test results to choose C, but the test set is no longer a completely unseen final audit. A fresh external test set would be a stronger next step.

**Q. Is the model 91.4% accurate in a real bank?**  
We do not know. That score is on the Banking77 test set. Real tickets may differ in vocabulary, language, class mix and ambiguity. We need representative bank data and a pilot.

**Q. Why can the result fail despite good aggregate accuracy?**  
Similar categories, short or incomplete messages, typos, new topics and missing context can lead to mistakes. Some individual intents may perform worse than the average; inspect per-intent metrics and examples.

---

## 5. M5 — Deployment prototype and demonstration

### Architecture in one line

`Browser → local Python HTTP API → cleaning → saved TF-IDF + SVM → intent suggestion → human review → rule-based department routing → local SQLite ticket and audit`

The Python server loads the saved model at startup and serves the browser UI and API on `127.0.0.1:8000` by default. It is a **local deployment prototype**, not a public cloud service. The AI does not decide which employee to assign or resolve the case.

### Demo script: 3–5 minutes

1. Start the project and open the dashboard. Explain: “This is a local human-in-the-loop support prototype.”
2. Choose **Analyze a ticket**, select the sample **Card payment pending**, and click **Suggest Intent**. Explain the suggested category and alternatives.
3. Click **Continue to human review**. Explain that the suggestion is not a certainty and the original AI label is kept.
4. Approve the suggestion, or correct it if demonstrating an incorrect prediction. Show the department selected from the **final reviewed intent**.
5. Assign a demo agent → start work → add an internal note → enter a resolution summary and resolve.
6. Expand the audit trail to show the recorded steps. Optionally show a blank-input error or the `/ready` and `/metrics` endpoints.
7. Finish with the limitation: sample data only, local SQLite, no real-bank integration or authentication.

Sample note: “Checked the payment status.” Sample resolution: “Payment status checked and customer informed.” These are demonstration notes, not actual actions performed on a bank account.

### Run commands on this computer

```bash
cd /Users/Kush/Downloads/EndSem/Ticket_Management_System
source .venv/bin/activate
python api.py
```

Open `http://127.0.0.1:8000`. Leave the terminal running. Stop it with **Ctrl+C**. If port 8000 is already in use, check whether the project is already running before starting another copy. On a different computer, use that computer's project folder and install the pinned requirements first.

**Only use sample messages.** Successful predictions store original input text in the local Git-ignored `data/tickets.sqlite3` database. Demo-agent names and routing are prototype data. Do not remove an existing database without checking whether its contents are needed.

### Monitoring and failure handling

- `/health`: service process alive; reports whether model is ready.
- `/ready`: succeeds only when the model is loaded and ready.
- `/metrics`: in-memory prediction counts, errors, average latency and predicted-label counts. Counters reset on restart.
- Structured logs include request ID, status and latency; prediction logs do not intentionally contain submitted text. Local SQLite **does** retain successful ticket text.
- Invalid or blank text returns 400; oversized input 413; wrong content type 415; unavailable model 503; unexpected errors return a generic 500.
- The monitoring guide proposes future readiness, error-rate and latency alerts. Those alerts and durable monitoring are a **plan**, not already deployed infrastructure.

The saved local benchmark used **100 sequential localhost requests with the same sample message**: 100 succeeded, mean **0.96 ms**, median **0.88 ms**, and p95 **1.28 ms**. This includes local HTTP overhead and was recorded on a particular machine. It is not a concurrent load test, cloud latency, real traffic, or a production capacity guarantee. Running the benchmark sends prediction requests, creates sample tickets and overwrites its benchmark report; do not run it during the demo unless you intend that.

### M5 viva questions and follow-ups

**★ Q. What did you deploy?**  
We deployed the saved model as part of a local Python HTTP service, with a browser interface and SQLite workflow on our machine. We did not deploy a public cloud service. If the evaluator expects a public URL, that is not currently available.

**Q. What is an API?**  
A defined way for software components to communicate. Here the browser sends an HTTP request to `/predict`; the server returns JSON containing a suggestion, alternatives and ticket information.

**Q. Why load the model once?**  
Loading at startup avoids reading the model file for every request. `/ready` indicates whether it loaded successfully.

**★ Q. How does routing work? Is it learned by the model?**  
No. After a human approves or corrects the predicted intent, a predefined Python mapping maps that final intent to a department. It covers all 77 dataset labels exactly once. The dataset does not provide bank department labels, so the mapping is a prototype rule, not bank-validated ground truth.

**Q. Why require human review?**  
The model can be wrong and does not have reliable calibrated confidence or a validated out-of-scope detector. Human review allows correction before routing and preserves the original AI suggestion for audit.

**Q. How are tickets stored?**  
SQLite stores successful predictions and ticket state locally. Separate tables retain audit events and notes. This is simple for a single-machine demonstration; it is not presented as a scalable production architecture.

**Q. What if the model file is missing?**  
The server can report that it is not ready; prediction requests return 503. It should not invent an answer.

**Q. What if an empty ticket is entered?**  
The API validates the input and returns a 400 error instead of making a prediction.

**Q. What about privacy/security?**  
Use sample data. The app stores successful input text locally and has no login, role enforcement, automatic retention policy, HTTPS or rate limiting. It should not be exposed publicly or used with real bank data without appropriate controls.

**Q. What is drift, and how would you monitor it?**  
Drift means incoming data or model performance changes over time. A future pilot could inspect input/intent distribution and compare suggestions with reviewed labels. A human correction is useful feedback, but it is not automatically verified ground truth.

**Q. Do human corrections retrain the model?**  
No. Corrections are recorded for feedback and audit; there is no automatic retraining pipeline.

---

## 6. M6 — Final delivery and viva

The repository contains code, saved model and evidence; a technical report exists in both PDF and DOCX under `deliverables/`. The live demo is the local application. **The existing PPT files were originally M1–M2 slides**, so prepare or update a final M3–M6 presentation before relying on them. Confirm the latest local changes are committed and pushed and that evaluators can access the GitHub link. Submit the report and repository link through the provided form when available.

### Suggested 20–30 minute structure

Adjust to the evaluator's instructions and leave time for questions.

| Time | What to cover |
|---|---|
| 0–2 min | Problem, users and one-sentence solution |
| 2–4 min | Very short M1–M2 recap and data splits |
| 4–8 min | Baseline, candidate, why TF-IDF/SVM and validation choice |
| 8–12 min | Test metrics, error example, optimization and robustness |
| 12–17 min | Live ticket demo, human review and local architecture |
| 17–20 min | Monitoring, privacy, limitations and next steps |
| Remaining time | Questions and follow-ups; extend the demo if requested |

**Q. What was your contribution?** Give your own truthful role. Do not claim you trained or coded a part you did not personally do. You can explain the team's implementation and your role in reviewing, testing, demonstrating or preparing it.

**Q. What would you improve next?** First evaluate representative and privacy-approved bank tickets, add a fresh independent holdout, examine weak intents and out-of-scope cases, and run an agent pilot. For a real deployment, add access controls, secure hosting, retention rules and durable monitoring.

**Q. What business outcome did you achieve?** We achieved a benchmark classifier and a workflow prototype. Faster categorization and more consistent real-world handling are objectives; we have not measured them with agents.

---

## 7. Numbers to remember

- **13,083** total original queries = 10,003 training source + 3,080 official test.
- **77** intent labels; English, one label per query.
- **98** training-source rows removed; final **8,490 train / 1,415 validation / 3,080 test**.
- Validation macro F1: **87.45%** logistic baseline → **90.56%** word + character SVM candidate.
- Final test: **91.40% accuracy**, **91.42% macro F1**, **265 errors**.
- M4: C=1.0 kept; C=2.0 improved validation macro F1 by only **0.03 percentage points**.
- Robustness: original validation **90.81%**, typo **84.17%**, first-half stress **42.61%**.
- Deployment: **local API + human review + rule-based routing + SQLite**, not a public bank system.

## 8. Last-minute checklist

- [ ] Each member can explain the problem, model choice, numbers and their own contribution.
- [ ] Prepare the final presentation; do not present the old M1–M2-only deck as the complete final deck.
- [ ] Start the app on the actual demo laptop; rehearse one complete ticket and a correction.
- [ ] Open the final report and verify the GitHub link and permissions; push the latest changes.
- [ ] Keep the report, code, experiment logs and per-intent errors available offline.
- [ ] Explain limits honestly: benchmark only, local prototype, incomplete privacy controls, no measured time savings.
- [ ] If a number is forgotten, say where it is recorded; do not invent it.

**Main evidence:** `docs/M3_MODEL_DEVELOPMENT.md`, `docs/M4_EVALUATION.md`, `docs/M5_DEPLOYMENT.md`, `reports/m3_experiment_log.csv`, `reports/m4_summary.json`, and `deliverables/IEEE_Project_Report.pdf`.
