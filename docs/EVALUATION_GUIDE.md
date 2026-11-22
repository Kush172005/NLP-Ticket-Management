# M1–M2 evaluation guide

Use the revised folder:

```text
/Users/kush/Documents/ChatGPT/NLP Project/Ticket_Management_System
```

The folder in Downloads is the older version and still includes M3 work.

## Before the evaluation

Open `presentation/M1_M2_Evaluation.pptx` and `reports/m2_report.html`. Keep a terminal
in the revised folder. Run the checks once so the terminal and reports are ready:

```bash
cd "/Users/kush/Documents/ChatGPT/NLP Project/Ticket_Management_System"
python3 m2_preprocess.py
python3 verify.py
python3 demo.py
```

On this laptop, the checked `python3` installation has the dependencies. If using a new
environment, follow the setup in README first. A fresh installation needs network access,
but the supplied raw data and reports work offline after setup.

## Suggested 7–9 minute walkthrough

### 1. State the scope, about 30 seconds

“Our project is a ticket management system focused on banking support queries. For M1
and M2, we have defined the business problem and prepared the data. Model development
belongs to the next milestone.”

### 2. Explain M1, about 90 seconds

Show the business-case slides or `docs/M1_PROBLEM_BRIEF.md`.

- Agents spend time manually categorizing queries, and similar issues can receive
  inconsistent labels.
- Support agents, triage staff and managers are the intended users.
- The NLP task is single-label classification of an English banking query into 77 intents.
- The business objective is lower categorization effort and more consistent labeling.
- Future targets include macro F1 and accuracy of at least 0.80, plus 20% lower median
  categorization time in an agent pilot. Say explicitly that these are proposed targets.
- Data preparation runs locally on a laptop. No GPU or paid API is needed for M2.

### 3. Justify the data, about 45 seconds

Show the dataset section of `reports/m2_report.html`.

“We use PolyAI's Banking77 because its queries and intent labels match banking ticket
categorization. It contains 10,003 official training queries and 3,080 official test queries
across 77 intents. We verified the publisher files and retained the license.”

Mention that the dataset contains intents only. It cannot validate sentiment, priority or
team routing. It also does not establish performance for other industries or languages.

### 4. Show understanding of the data, about 60 seconds

Show `reports/m2_eda.png` inside the HTML report.

- There are zero blank source texts or labels.
- Original files have no exact raw text/label duplicates. Normalization creates some
  repeated texts because punctuation, case and numbers can differ before cleaning.
- Final training class counts range from 30 to 160, a 5.33 ratio.
- Median training length is 10 words. Mean is 11.95, and the 95th percentile is 29 words.
- The imbalance means later model evaluation should include macro F1 and per-intent recall.

### 5. Demonstrate preprocessing, about 90 seconds

Run:

```bash
python3 demo.py
```

Point to the actual source examples and their cleaned versions. The printed labels are
dataset annotations, not model predictions.

Explain the decisions:

- Normalize text and mask supported numeric/contact patterns.
- Lowercase and expand common contractions.
- Keep negations. “Not working” and “working” have different meanings.
- Keep stopwords. Short queries can lose meaning if cleaning is too aggressive.
- Avoid stemming, lemmatization, truncation and synthetic augmentation for this submission.

If asked to clean an individual query, use the publisher's public example:

```bash
python3 demo.py --text "Is there a way to know when my card will arrive?"
```

To demonstrate a meaningful contraction change, use another public training example:

```bash
python3 demo.py --text "I got a new card and can't find where to link it."
```

Do not enter private customer information. The preprocessing unit tests exercise masking
on clearly artificial strings. Those fixtures are not added to the dataset.

### 6. Explain exclusions and splits, about 90 seconds

Show the report's split section and `reports/removed_rows.csv`.

| Stage | Rows |
|---|---:|
| Official training source | 10,003 |
| Conflicting-label training rows excluded | 2 |
| Repeated normalized training rows excluded | 42 |
| Training rows in groups connected to test text excluded | 54 |
| Retained training source | 9,905 |
| Final training subset | 8,490 |
| Final validation subset | 1,415 |
| Official test subset | 3,080 |

“We keep the official test membership and labels. We create training and validation only
from the retained official training source. Duplicate groups stay together. The seed is
42, and one of seven grouped stratified folds forms validation.”

All three splits cover 77 intents. The train, validation and test files share zero exact
normalized texts and zero groups under the documented near-duplicate rule.

If asked about the rule: a word trigram contains three adjacent words. For sufficiently
long queries, we compare the sets of trigrams. Jaccard similarity is their intersection
size divided by their union size. A score of at least 0.85 connects a pair. Connected
pairs stay in one group. Shorter queries use exact matching.

Be precise: these checks cover exact and defined lexical overlap. They cannot detect
every semantic paraphrase. The official test contains nine repeated normalized rows and
one conflicting normalized-text group. We disclose them and keep benchmark membership.

### 7. Show verification and finish, about 45 seconds

Run:

```bash
python3 verify.py
```

Explain that it rereads the saved files, checks source labels and transformations, accounts
for all training rows, preserves official test membership, and independently recomputes
duplicate matches. It also checks the recorded code and output hashes.

“Our M2 output is a documented dataset ready for modelling. We have not included model
training or accuracy results in this submission.”

## Quick answers for likely questions

**Why Banking77?** It supplies documented banking queries and fine-grained intent labels
that fit the chosen task. We keep the scope specific to banking.

**Where is the database?** This milestone uses dataset CSV files. An application database
is not necessary to demonstrate data understanding and preparation.

**Why do words sometimes increase after cleaning?** Expanding “isn't” into “is not” turns
one whitespace token into two. Cleaning is not intended to make every query shorter.

**Why not remove all stopwords?** Short queries need context, and removing negation can
reverse meaning. We keep them and defer representation choices to later modelling.

**Why mask every number?** It reduces exposure of numeric identifiers with a simple fixed
rule. It also loses useful counts and amounts. That tradeoff is documented for M3 review.

**Are the data fully anonymous?** No. Regexes handle specific patterns and can miss names,
addresses and unusual IDs. The supplied dataset has no matches for the URL, email,
card-like or phone-like rules. Other numbers match in 205 training-source and 49 test rows.
Those counts do not prove the absence of sensitive data.

**Why inspect test text?** Only for the fixed duplicate-contamination audit. We do not use
test labels or performance to choose cleaning parameters. No model is fitted in M2.

**Why about 14.3% validation?** One of seven folds is about one seventh. Grouped stratification
preserves duplicate groups and approximates label balance. We did not require exactly 15%.

**What does the hash prove?** It shows that a file matches the specific recorded bytes.
The pinned publisher URL provides provenance. A hash alone does not prove the whole project
is correct or that a model was trained.

**Where is the model accuracy?** Model development is M3. This evaluation ends with prepared
data. The stated F1 and accuracy thresholds are proposed success targets.

**What does M3 add?** A training-only fitted representation and baseline models. Validation
will guide selection, while the test set remains reserved for later final evaluation.

## Requirement-to-evidence checklist

| Requirement | What to show |
|---|---|
| M1 problem brief | `docs/M1_PROBLEM_BRIEF.md` |
| M1 user identification | Users table in the brief |
| M1 business objective | Business objective section |
| M1 success metrics | Proposed metrics and future measurement plan |
| M1 feasibility analysis | Feasibility table and limitations |
| M2 data card | `docs/DATA_CARD.md` |
| M2 exploratory analysis | `reports/m2_eda.png`, full class chart and counts |
| M2 cleaning | `preprocessing.py`, `m2_preprocess.py`, example/removal reports |
| M2 statistical analysis | Length summaries and class counts in `reports/m2_stats.json` |
| M2 privacy considerations | Data card and pattern counts in the HTML report |
| M2 documented splits | `data/processed/`, overlap checks and `python3 verify.py` |

If time is short, show the M1 brief, the HTML report, `python3 demo.py` and `python3 verify.py`.
Those four items cover the required story and the executable evidence.
