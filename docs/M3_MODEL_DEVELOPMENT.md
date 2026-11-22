# M3: Baseline and model development

## Task

Given one cleaned English Banking77 query, suggest one of the dataset's 77 intent labels.
The suggestion is for an agent to review. This model does not assign priority, route a ticket,
or resolve it.

## Approaches

| Approach | What it does |
|---|---|
| Majority guess | Always predicts the most common training intent. This is a simple reference point. |
| Word TF-IDF + logistic regression | The baseline. TF-IDF gives weight to useful words and two-word phrases; logistic regression learns which patterns indicate each intent. |
| Word and character TF-IDF + linear SVM | Candidate improvement. Adds short character patterns to catch spelling and word-form clues, then separates intents with a linear support vector classifier. |

All feature extraction and model fitting use training data only. The validation split compares candidates.
Macro F1 is the selection metric because it gives each of the 77 intents equal importance despite
uneven class sizes. Accuracy and weighted F1 are also recorded. After selection, the chosen approach
is refit on train plus validation and measured once on the untouched official test split.

## Reproduce

```bash
python -m pip install -r requirements.txt
python train_models.py
python predict_ticket.py "my card payment is pending"
```

The script has fixed model settings and uses the existing prepared splits. It writes the trained
pipeline to `models/banking77_intent_model.joblib`, a comparison table to
`reports/m3_experiment_log.csv`, the overall summary to `reports/m3_summary.json`, and per-intent
test scores to `reports/test_classification_report.json`.

## Results

| Approach | Validation accuracy | Validation macro F1 | Validation weighted F1 |
|---|---:|---:|---:|
| Majority guess | 0.0191 | 0.0005 | 0.0007 |
| Word TF-IDF + logistic regression | 0.8777 | 0.8745 | 0.8783 |
| Word + character TF-IDF + linear SVM | **0.9081** | **0.9056** | **0.9082** |

The word-and-character model won on validation macro F1. After refitting on train plus validation,
it scored **0.9140 accuracy** and **0.9142 macro F1** on the official 3,080-row test split. The
project's provisional M1 targets of 0.80 for accuracy and macro F1 were met on this benchmark.
Per-intent precision, recall and F1 are in `reports/test_classification_report.json`.

These are benchmark results, not proof of performance on live bank tickets. They cannot show time
saved, customer satisfaction, or safe performance on other languages and domains. Review per-intent
errors before considering a real-world pilot.
