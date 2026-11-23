# Banking77 data card

## Source and intended use

Banking77 contains English online-banking customer queries with one intent label per query.
We use it to prepare data for banking support ticket categorization. It is a benchmark for
the text classification component, not a complete operational ticket database.

- Publisher: PolyAI.
- Dataset: https://github.com/PolyAI-LDN/task-specific-datasets
- Paper: Casanueva et al. (2020), *Efficient Intent Detection with Dual Sentence Encoders*.
  https://aclanthology.org/2020.nlp4convai-1.5/
- Source commit: `57ec275d8078af65b7731c2a98be812d844a6d6b`.
- License: CC BY 4.0. The publisher's license is retained in `data/raw/LICENSE.txt`.
- Original size: 10,003 training queries and 3,080 test queries, across 77 intents.
- The pipeline downloads no generated replacements and preserves the original source bytes.
- `reports/manifest.json` records source URLs, SHA-256 hashes and package versions.

## Schema

The publisher's CSVs have `text` and `category` columns. The loader renames `category` to
`label` in memory. Labels keep the publisher's spelling and capitalization, including
`Refund_not_showing_up` and `reverted_card_payment?`.

Processed files contain:

| Column | Meaning |
|---|---|
| row_id | Original split and zero-based source row position |
| source_split | Publisher's train or test origin |
| masked_text | Original wording with supported patterns replaced |
| clean_text | Normalized text for later modelling |
| label | Publisher's intent annotation, never inferred |
| group_id | Connected component of exact / defined near-duplicate text |
| raw_words | Whitespace word count before cleaning |
| clean_words | Whitespace token count after cleaning |

Raw text remains only in `data/raw/`. Reports and processed files omit an unmasked text
column. The masked column can still contain sensitive information the regexes miss.

## Quality and exclusions

Both source splits have zero blank texts and zero blank labels. The loader checks all 77
labels against `categories.json`, verifies row counts and rejects changed source files.

Training exclusions use a fixed order: empty normalized text, conflicting labels for the
same normalized text, repeated same-label normalized text, then groups overlapping test.
The first matching reason accounts for each excluded source row exactly once.

| Exclusion reason | Rows |
|---|---:|
| overlap with official test group | 54 |
| duplicate training text | 42 |
| conflicting training labels | 2 |
| Total | 98 |

`reports/removed_rows.csv` records source row IDs and reasons, without copying ticket text.
All 3,080 official test rows and their labels remain in the test file.

## Cleaning decisions

1. Normalize Unicode width and curly apostrophes.
2. Mask URLs, emails, card-like digit strings, phone-like digit strings and other numbers,
   in that order. These are pattern matches, not verified PII detections.
3. Lowercase and expand common unambiguous contractions. Keep negation words.
4. Replace punctuation and non-English letters with spaces. Collapse extra whitespace.
5. Keep ordinary words. Do not remove stopwords, stem, lemmatize or truncate queries.

For this English-only task, simple cleaning keeps the code explainable. Number masking
reduces identifier exposure but loses amounts and counts, which may matter in some queries.
We will review that tradeoff using training/validation evidence during M3.

## Splits and leakage controls

| Split | Rows | Intents |
|---|---:|---:|
| train | 8,490 | 77 |
| val | 1,415 | 77 |
| test | 3,080 | 77 |

The test file follows the official test split. Training and validation come only from the
retained official training rows. We use the first fold of `StratifiedGroupKFold` with seven
folds, shuffle enabled and seed 42. Validation contains approximately
14.3% of retained training-source rows.
Grouping takes precedence over exact class proportions, so validation is approximate.

Exact normalized matches share a group. For queries with at least three distinct word
trigrams, Jaccard similarity of at least 0.85 also connects them. A trigram is three adjacent
words. Jaccard is shared trigrams divided by all distinct trigrams in the pair. Connections
are transitive. Training groups connected to official test text are excluded, regardless
of their labels. Test content is used only for this predefined contamination audit.

Every pair of exported splits has zero shared normalized texts and zero shared groups.
This protects against exact overlap and the stated lexical near-duplicate rule. It does
not prove that every semantic paraphrase is absent. Customer/thread IDs and timestamps
are unavailable, so customer-level and temporal leakage cannot be assessed.

Official test internal normalized duplicate rows: 9.
Official test normalized texts with conflicting labels: 1.
These benchmark rows remain unchanged in membership and labels. Their presence is reported.

## Statistical findings

- Training class sizes range from 30 to 160.
- Largest/smallest training class ratio: 5.33.
- Training text length before cleaning: mean 11.95, median 10,
  standard deviation 7.92 and 95th percentile 29 words.
- Full class counts: `reports/class_distribution.csv` and `reports/class_distribution.png`.
- Length statistics for all splits: `reports/m2_stats.json`.

Class imbalance supports using macro F1 and per-intent recall in the future evaluation.
We do not resample validation or test data. Long training queries remain available.
Short and similarly worded intents may need context that this dataset does not provide.

## Privacy and responsible use

The public benchmark is not proof that future customer tickets are safe to share.
Regexes can miss names, addresses, alphanumeric account IDs and unusual number formats.
No names or addresses are reliably anonymized here. Do not enter real customer details
in the demo. Use the publisher's examples for evaluation. Review redaction manually before
sharing derived data. Limit access and retention for any future private tickets.
The local demo runs on `127.0.0.1` and does not upload ticket inputs to a third-party service.
For the Admin Review workflow, successful prediction inputs are retained in the local, Git-ignored
SQLite file `data/tickets.sqlite3` so a support reviewer can inspect the ticket and preserve the
classification decision, audit history, agent-entered internal notes, and resolution summary. Do not use real customer data in this classroom prototype:
the database has no automatic retention or deletion policy, and the prototype has no sign-in or
role-based access control. Remove the local database file to delete its stored ticket records.

## Coverage and limits

The data covers banking intents in English. It does not establish performance for Hindi,
mixed-language tickets, other industries, multi-intent conversations or out-of-scope queries.
It provides no ground truth for sentiment, urgency, team assignment, resolution time,
summaries or suggested replies. Benchmark class frequencies may differ from real traffic.
We have no measured business time savings and no new model results at M1–M2.

## Reproduction

Run `python m2_preprocess.py`, then `python verify.py` from the project folder.
No training script or fitted vectorizer is part of this evaluation version.
