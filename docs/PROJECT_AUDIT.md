# Changes for the M1–M2 evaluation

The original folder at `/Users/kush/Downloads/Ticket_Management_System/` is preserved.
This working version lives in `/Users/kush/Documents/ChatGPT/NLP Project/Ticket_Management_System/`.
Use this version during the evaluation.

## What the original contained

The original already covered parts of M2 and M3. Its M2 script validated row counts,
removed some duplicate/conflicting training examples and made a stratified validation split.
It also fitted a TF-IDF vectorizer. Its M3 script compared classifiers and reported model
metrics. Other scripts added sentiment, priority, routing and suggested replies.

## Gaps addressed

| Finding | Change in this version |
|---|---|
| No standalone M1 business brief | Added users, objective, task boundaries, proposed metrics and feasibility |
| No raw CSVs in the shared folder | Included publisher files pinned to a source revision and SHA-256 hashes |
| Source loader could concatenate train and test | Loader returns separate frames |
| No overlap check against official test text | Excludes training groups connected to test text |
| Random stratification could separate very similar queries | Keeps defined near-duplicate groups together |
| Original text remained in processed CSVs | Exports masked and normalized text, omits an unmasked original-text column |
| Small EDA and no complete data card | Added all-class counts, length summaries, charts, privacy counts and data card |
| Removal reasons combined into one count | Records each excluded source row and its first applicable reason |
| README led with model scores | Replaced it with M1–M2 scope and reproduction commands |
| Prediction used different cleaning from preprocessing | Prediction is excluded. One cleaner serves preparation and the M2 demo |
| Relative raw paths depended on the launch directory | Paths resolve from the project directory |

## M3 and later work excluded

The evaluation version does not include `m3_train.py`, `run_reproducible_training.py`,
`predict_ticket.py`, `analyze.py`, `modules.py`, `eval_rules.py`, `models/`, model-comparison
reports, test-performance reports or the old M2–M3 guides. The old full-system diagram and
import helper are also excluded because they do not describe this verified pipeline.

The previous folder preserves them for later work. We have not rerun or validated the
old model scores, and this submission does not repeat those results.

TF-IDF fitting is deferred to M3 to make the M2 endpoint unambiguous. M2 prepares text
and splits. It learns no vocabulary, feature weights or classifier parameters.

## Simplicity decisions

This version uses small Python scripts, CSV outputs, static charts and one offline HTML
report. It has no server, database, paid API, web application or deployment requirement.
The duplicate rule is fixed and explained in the data card. A successful check means zero
overlap under that rule, not proof that every possible semantic overlap has been removed.
