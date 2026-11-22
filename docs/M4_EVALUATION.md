# M4: Evaluation and optimization

## What M4 does

M4 checks how the M3 intent model behaves, tries a small safe improvement, studies wrong answers,
and checks what happens when a message is changed. It does not automatically handle customer
accounts or take actions. Predictions are suggestions for an agent to review.

## Optimization and iteration record

The M3 model used a linear SVM setting called `C=1.0`. C controls how strongly the model tries to
fit the training examples. M4 compares `C=0.5`, `C=1.0`, and `C=2.0` on validation data. To avoid
changing the model over a tiny score difference, M4 keeps the familiar `C=1.0` when the best
candidate improves validation macro F1 by less than 0.001. The official test split is not used to
select settings. Exact results are saved to `reports/m4_experiment_log.csv` and
`reports/m4_summary.json`.

| SVM setting | Validation accuracy | Validation macro F1 | Decision |
|---|---:|---:|---|
| C=0.5 | 90.67% | 90.54% | Tested, lower score |
| C=1.0 (M3 setting) | 90.81% | 90.56% | Kept |
| C=2.0 | 90.74% | 90.59% | Tested; gain was only 0.03 percentage points |

The small validation gain for C=2.0 was below the 0.1 percentage-point threshold we set for
changing the existing model. We kept C=1.0. This is a documented optimization iteration, but it
does not claim a measurable model improvement.

After choosing a setting, the script trains the final model on train plus validation data, saves it
to `models/banking77_intent_model.joblib`, and calculates final test metrics. Because the M3 test
result had already been viewed, M4 treats test results and test errors as descriptive evidence only;
they are not used to make another model choice.

## Error analysis

The script records every wrong test prediction with its true and predicted intent. It adds simple,
readable tags for short queries (five words or fewer), queries containing a masked number/contact
pattern, and other mistakes. It also lists the most common true-intent/predicted-intent pairs and
per-intent precision, recall and F1.

- `reports/m4_test_errors.csv`: each test error and its tags.
- `reports/m4_common_confusions.csv`: most frequent kinds of category mix-ups.
- `reports/m4_test_per_intent.json`: test results for each intent.

On the 3,080 test messages, the selected model made 265 errors (8.60%). Of those, 23 were short
queries, 3 contained a masked value pattern, and 239 were other cases. Common category mix-ups
include `top_up_failed` predicted as `top_up_reverted` (4 cases; the reverse occurred 3 times) and
`pending_transfer` predicted as `failed_transfer` (4 cases; the reverse occurred 2 times). These
categories are similar in wording, so small distinctions in the message matter.

The tags describe patterns; they do not prove why the model made an error. Tags can overlap.

## Robustness checks

Controlled changes are applied to validation messages, then compared with their original labels and
predictions:

1. Uppercase plus punctuation checks normalization. Predictions should remain the same.
2. A small character swap checks sensitivity to a typo.
3. Keeping only the first half checks what happens when a message is incomplete. Its meaning may
   change, so this is a stress check, not a promise that the original label must stay correct.

These checks use a model trained on the training split only, leaving validation messages unseen.

Results include accuracy after the change and the fraction of predictions that stayed the same.
They are in `reports/m4_summary.json`. These synthetic checks do not replace testing on real,
representative customer messages.

| Validation stress check | Accuracy after change | Same prediction as original |
|---|---:|---:|
| Uppercase + punctuation | 90.81% | 100.00% |
| One character swap | 84.17% | 89.19% |
| First half only | 42.61% | 44.52% |

The model handled formatting changes consistently. Typos reduced accuracy, and removing half the
message caused a larger drop, showing why incomplete tickets should be reviewed carefully.

## Try a prediction

```bash
python m4_evaluation.py
python predict_ticket.py "my card payment is pending"
```

The inference script shows the top three suggested categories. Its SVM ranking scores are not
probabilities or guarantees. An agent should review the suggestions, especially for short or
incomplete messages.
