"""Write the charts, data card and offline report used in the evaluation."""
import os
from html import escape

from config import ROOT, REPORTS

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.titleweight": "bold"})
BLUE, TEAL, ORANGE = "#24557a", "#14847e", "#d18432"


def build_reports(stats, counts, splits):
    train = splits["train"]
    fig, ax = plt.subplots(figsize=(12, 17))
    counts.train.sort_values().plot.barh(ax=ax, color=BLUE)
    ax.set(title="Training queries across all 77 intents", xlabel="Queries", ylabel="")
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS / "class_distribution.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    selected = pd.concat([counts.train.nsmallest(6), counts.train.nlargest(6)]).sort_values()
    labels = [label.replace("_", " ") for label in selected.index]
    axes[0].barh(labels, selected.values, color=[ORANGE] * 6 + [BLUE] * 6)
    axes[0].set(title="Six smallest and six largest training classes", xlabel="Queries")
    axes[0].tick_params(axis="y", labelsize=8)
    axes[1].hist(train.raw_words, bins=30, color=TEAL, edgecolor="white")
    axes[1].axvline(train.raw_words.median(), color=ORANGE, linestyle="--", label="Median")
    axes[1].set(title="Training query length before cleaning", xlabel="Whitespace-separated words", ylabel="Queries")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(REPORTS / "m2_eda.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist([train.raw_words, train.clean_words], bins=30, label=["Before cleaning", "After cleaning"],
            color=[BLUE, TEAL], alpha=.85)
    ax.set(title="Effect of cleaning on training query length", xlabel="Words / tokens", ylabel="Queries")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(REPORTS / "cleaning_lengths.png", dpi=150)
    plt.close(fig)

    with plt.rc_context({"font.size": 14}):
        fig, ax = plt.subplots(figsize=(7, 4.2))
        ax.hist(train.raw_words, bins=30, color=TEAL, edgecolor="white")
        ax.set(xlabel="Words before cleaning", ylabel="Training queries")
        fig.tight_layout()
        fig.savefig(REPORTS / "ticket_lengths.png", dpi=150)
        plt.close(fig)

    write_data_card(stats)
    write_html(stats, counts)


def write_data_card(stats):
    s = stats
    split_rows = "\n".join(f"| {name} | {part['rows']:,} | {part['labels']} |" for name, part in s["splits"].items())
    removal_rows = "\n".join(f"| {reason.replace('_', ' ')} | {n} |" for reason, n in s["removals"].items())
    length = s["length_statistics"]["train"]["raw_words"]
    content = f"""# Banking77 data card

## Source and intended use

Banking77 contains English online-banking customer queries with one intent label per query.
We use it to prepare data for banking support ticket categorization. It is a benchmark for
the text classification component, not a complete operational ticket database.

- Publisher: PolyAI.
- Dataset: https://github.com/PolyAI-LDN/task-specific-datasets
- Paper: Casanueva et al. (2020), *Efficient Intent Detection with Dual Sentence Encoders*.
  https://aclanthology.org/2020.nlp4convai-1.5/
- Source commit: `{s['source_revision']}`.
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
{removal_rows}
| Total | {s['removed_total']} |

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
{split_rows}

The test file follows the official test split. Training and validation come only from the
retained official training rows. We use the first fold of `StratifiedGroupKFold` with seven
folds, shuffle enabled and seed 42. Validation contains approximately
{100 * s['validation_fraction_of_retained_train']:.1f}% of retained training-source rows.
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

Official test internal normalized duplicate rows: {s['official_test_internal_clean_duplicates']}.
Official test normalized texts with conflicting labels: {s['official_test_conflicting_clean_groups']}.
These benchmark rows remain unchanged in membership and labels. Their presence is reported.

## Statistical findings

- Training class sizes range from {s['train_class_min']} to {s['train_class_max']}.
- Largest/smallest training class ratio: {s['train_imbalance_ratio']:.2f}.
- Training text length before cleaning: mean {length['mean']:.2f}, median {length['50%']:.0f},
  standard deviation {length['std']:.2f} and 95th percentile {length['95%']:.0f} words.
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
The local demo does not upload ticket inputs to any service and does not save inputs.

## Coverage and limits

The data covers banking intents in English. It does not establish performance for Hindi,
mixed-language tickets, other industries, multi-intent conversations or out-of-scope queries.
It provides no ground truth for sentiment, urgency, team assignment, resolution time,
summaries or suggested replies. Benchmark class frequencies may differ from real traffic.
We have no measured business time savings and no new model results at M1–M2.

## Reproduction

Run `python m2_preprocess.py`, then `python verify.py` from the project folder.
No training script or fitted vectorizer is part of this evaluation version.
"""
    (ROOT / "docs" / "DATA_CARD.md").write_text(content)


def write_html(stats, counts):
    examples = pd.read_csv(REPORTS / "cleaning_examples.csv")
    split_table = pd.DataFrame(stats["splits"]).T[["rows", "labels", "groups"]].to_html(border=0)
    removal_table = pd.DataFrame(list(stats["removals"].items()), columns=["Reason", "Rows"]).to_html(index=False, border=0)
    privacy_table = pd.DataFrame(stats["privacy_pattern_rows"]).to_html(border=0)
    length = stats["length_statistics"]["train"]["raw_words"]
    checks = "".join(f"<li>{escape(name.replace('_', ' '))}: <strong>{value}</strong></li>"
                     for name, value in stats["leakage_checks"].items())
    html = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ticket Management System | M1 and M2 evidence</title>
<style>
body{{font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#203448;background:#f4f6f7;margin:0}}
main{{max-width:1080px;margin:0 auto;padding:48px 30px;background:white}}
h1{{font-size:38px;line-height:1.18;color:#153e5d}} h2{{margin-top:48px;color:#153e5d}} h3{{margin-top:28px}}
p,li{{max-width:920px}} .scope{{color:#14736f;font-weight:600}} nav a{{margin-right:24px}} a{{color:#24557a}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}}th,td{{padding:10px 12px;border-bottom:1px solid #dae1e6;text-align:left;vertical-align:top}}
th{{background:#eff4f7}}img{{width:100%;height:auto}}code{{background:#eef3f5;padding:3px 6px}}.note{{border-left:4px solid #d18432;padding:12px 18px;background:#fbf5ec}}
.scroll{{overflow-x:auto}} .numbers{{font-size:23px;font-weight:600}} @media print{{body{{background:white}} main{{padding:0}}nav{{display:none}}h2{{break-after:avoid}}img{{max-height:500px;object-fit:contain}}}}
</style><main>
<p class="scope">Industry Track / M1 and M2</p>
<h1>Ticket Management System</h1><p>Banking support ticket classification: problem definition and data preparation.</p>
<nav><a href="#m1">Business case</a><a href="#data">Dataset</a><a href="#cleaning">Preprocessing</a><a href="#splits">Splits</a><a href="#privacy">Privacy</a></nav>
<p class="note">This version ends with prepared data. It contains no trained classifier, fitted vocabulary or prediction results.</p>
<h2 id="m1">M1: Problem and business case</h2>
<p>Support agents manually read and categorize incoming banking queries. Similar issues can receive inconsistent labels, increasing triage effort. The project aims to help agents categorize those queries while keeping a person responsible for uncertain cases.</p>
<p><strong>Users:</strong> support agents, triage staff and support managers.<br>
<strong>NLP task:</strong> map one English banking query to one of 77 intent labels in a later milestone.<br>
<strong>Business objective:</strong> reduce categorization time and inconsistent assignments.</p>
<p>Proposed future targets: macro F1 ≥ 0.80, accuracy ≥ 0.80 and a 20% reduction in median categorization time in an agent pilot. These are planning targets. We have not measured them in M1–M2.</p>
<p>The full problem brief, feasibility analysis and measurement plan are in <a href="../docs/M1_PROBLEM_BRIEF.md">M1_PROBLEM_BRIEF.md</a>.</p>
<h2 id="data">M2: Dataset and exploratory analysis</h2>
<p class="numbers">13,083 queries &nbsp; / &nbsp; 77 intents &nbsp; / &nbsp; English banking</p>
<p>PolyAI's Banking77 is suitable for the intent classification part of a banking support project. It provides text and intent labels. It does not provide sentiment, priority, routing or resolution labels.</p>
<p>Source: <a href="https://github.com/PolyAI-LDN/task-specific-datasets">PolyAI repository</a>, CC BY 4.0.<br>Paper: <a href="https://aclanthology.org/2020.nlp4convai-1.5/">Casanueva et al., 2020</a>.<br>All four raw source files pass pinned SHA-256 verification.</p>
<img src="m2_eda.png" alt="Training class sizes and query lengths">
<p>Training class sizes range from {stats['train_class_min']} to {stats['train_class_max']} queries, a {stats['train_imbalance_ratio']:.2f} ratio. This imbalance makes macro F1 and per-intent recall useful future measures. The median training query has {length['50%']:.0f} words. The mean is {length['mean']:.2f}, with a standard deviation of {length['std']:.2f}. The 95th percentile is {length['95%']:.0f} words.</p>
<p><a href="class_distribution.png">All 77 classes</a> · <a href="class_distribution.csv">Class counts CSV</a> · <a href="m2_stats.json">Complete statistics</a> · <a href="../docs/DATA_CARD.md">Data card</a></p>
<h2 id="cleaning">Cleaning and exclusions</h2>
<p>Source audit: both splits contain zero blank texts and zero blank labels. Cleaning normalizes Unicode, masks supported patterns, lowercases, expands common contractions and removes punctuation. Negations and stopwords remain. We do not stem, lemmatize or truncate.</p>
<p>Training rows leave the pipeline for the first applicable reason below. Every removal has a source row ID in <a href="removed_rows.csv">removed_rows.csv</a>.</p>
{removal_table}
<h3>Examples from the official training data</h3>
<p>The left column already masks supported numeric and contact patterns. No fabricated training examples are added.</p>
<div class="scroll">{examples[['row_id', 'before_masked', 'after', 'label']].head(4).to_html(index=False, border=0, escape=True)}</div>
<img src="cleaning_lengths.png" alt="Query length before and after preprocessing">
<h2 id="splits">Split construction and leakage checks</h2>
{split_table}
<p>All 3,080 official test rows retain their membership and labels. The remaining official training rows form train and validation using seed 42 and a grouped stratified split. Validation is {100 * stats['validation_fraction_of_retained_train']:.1f}% of retained training-source data. Every split includes all 77 intents.</p>
<p>Exact normalized queries share a group. Queries with at least three distinct word trigrams also share a group when Jaccard similarity is at least 0.85. Groups connected to test text leave the training pool. The train/validation split keeps each remaining group together.</p>
<ul>{checks}</ul>
<p class="note">These checks establish zero exact overlap and zero overlap under the defined lexical grouping rule. Semantic paraphrases can still remain. The dataset has no customer or conversation IDs for stronger separation.</p>
<p>Official test internal duplicate rows after normalization: {stats['official_test_internal_clean_duplicates']}. We retain these benchmark rows and report them.</p>
<h2 id="privacy">Privacy considerations</h2>
<p>Masking runs in this order: URLs, emails, card-like numbers, phone-like numbers, then remaining numbers. Counts below show rows matching each rule after preceding replacements. They do not establish that a matched value is real personal data.</p>
{privacy_table}
<p>Processed data excludes an unmasked original-text column. Regexes can still miss names, addresses and alphanumeric account IDs. Raw benchmark data stays separate. The terminal demo runs locally and does not store entered queries. Real private tickets would require access controls and manual review of redaction.</p>
<h2>Reproducibility and next milestone</h2>
<p>Run <code>python m2_preprocess.py</code>, followed by <code>python verify.py</code>. The <a href="manifest.json">manifest</a> records source, code and output hashes plus environment versions. No network is needed when the supplied raw files are present.</p>
<p>M3 will fit features and train models using training data. Validation will guide model selection. The test set remains reserved for later final evaluation. This submission reports data preparation only.</p>
</main></html>"""
    (REPORTS / "m2_report.html").write_text(html)
