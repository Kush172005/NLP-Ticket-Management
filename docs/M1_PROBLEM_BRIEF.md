# M1: Problem definition and business case

**Project:** Ticket Management System  
**Scope:** Banking support ticket classification  
**Track:** Industry  
**Current submission:** M1 and M2

## Problem brief

Banking support agents receive short messages about card payments, transfers, account
verification and other issues. An agent must read each message and decide what the
customer needs before handling it. Similar wording can describe different issues, such
as a pending transfer and a transfer that failed. Manual categorization takes time and
can lead to inconsistent labels.

Our project prepares an NLP component that will suggest an intent category for a banking
support query. An agent will review the suggestion. This submission defines the task and
prepares the dataset. It does not claim an operational ticket-management application.

## Users and stakeholders

| User | Need | Intended benefit |
|---|---|---|
| Support agent | Understand the query's category quickly | Less manual categorization effort |
| Triage staff | Apply the same intent definitions consistently | Fewer inconsistent assignments |
| Support manager | Understand the distribution of incoming issues | More consistent reporting by category |
| Customer | Reach relevant support sooner | A possible downstream benefit to validate later |

These are intended users. We have not interviewed a bank or run a customer pilot.

## Business objective

Reduce the time agents spend categorizing banking queries and improve consistency of
intent labels. The tool should assist agents rather than decide financial or security
actions automatically. Categorization is only one step in ticket handling, so an intent
score alone cannot establish faster resolution or customer satisfaction.

## NLP task and boundaries

- **Input:** one English banking-support query.
- **Future output:** one of Banking77's 77 intent labels, with agent review.
- **Learning setup:** supervised, single-label, multiclass text classification.
- **M1 work:** problem, users, objective, success measures and feasibility.
- **M2 work:** data card, exploratory and statistical analysis, cleaning, privacy review,
  and reproducible splits ready for modelling.
- **Later work:** feature extraction, baseline comparison and model development in M3.

Example from the publisher: “Is there a way to know when my card will arrive?” has the
source label `card_arrival`. Showing that label in the demo is displaying an existing
annotation, not making a prediction.

Sentiment, priority, team routing, summaries and replies are outside the evaluated task.
Banking77 supplies no ground-truth labels for those outputs. Other industries, multilingual
queries, multiple intents and complete ticket lifecycle management also fall outside this
submission.

## Proposed success measures

These are provisional project targets, not measured achievements or bank requirements.

| Measure | Proposed target | How to measure it later |
|---|---|---|
| Macro F1 | At least 0.80 | Compute each intent's F1 and average equally on held-out data |
| Accuracy | At least 0.80 | Correct intent predictions divided by all evaluated queries |
| Per-intent recall | Inspect every intent, especially low-performing categories | Report correct predictions divided by examples of each true intent |
| Categorization effort | At least 20% lower median time | Time comparable manual and assisted tasks in an agent pilot |
| Agent correction rate | Lower than the manual inconsistency rate | Compare final reviewed labels against an agreed reference |

For the timing pilot, use matched query sets with similar intent and length distributions.
Counterbalance which workflow each agent uses first. Include review and correction time,
record sample size and variability, and report `(manual median - assisted median) / manual
median`. No timing or operational improvement has been measured yet.

M2 acceptance checks are concrete: source verification passes, every output row has a valid
label and nonempty normalized text, all splits cover 77 intents, all official test rows
remain present, and exported splits share neither exact normalized text nor groups under
the documented duplicate rule. Privacy limitations must be documented.

## Feasibility analysis

| Area | Assessment |
|---|---|
| Data availability | Banking77 supplies 10,003 training and 3,080 test examples with intent labels |
| Task fit | Strong fit for English banking-query intent categorization |
| Compute | Data preparation fits on a normal laptop. No GPU or paid API is required |
| Reproducibility | Pinned source commit and hashes, fixed split seed, saved reports and package versions |
| Privacy | Public benchmark with limited regex masking. Real customer data would require stronger review |
| Label coverage | Intent only. No validation of sentiment, priority or routing is possible from these labels |
| Generalization | Benchmark data cannot establish real-bank performance, multilingual coverage or operational gains |
| Delivery | M1–M2 can be demonstrated offline once Python dependencies are installed |

Main risks are similar intents, uneven class sizes, loss of context in short queries,
masking that removes useful numbers, and differences between benchmark and real traffic.
M2 reports these limits. Later milestones should evaluate errors and out-of-scope handling
before any agent pilot.

## Data choice

We keep Banking77 because it gives a clear task, documented labels and a publisher-defined
test split. It is a dataset, not an application database. CSV files are sufficient for this
milestone. Adding a database would not improve the required preprocessing evidence.

Source: [PolyAI Banking77](https://github.com/PolyAI-LDN/task-specific-datasets).  
Citation: Casanueva et al. (2020), [Efficient Intent Detection with Dual Sentence Encoders](https://aclanthology.org/2020.nlp4convai-1.5/).

## Current endpoint

The M1–M2 submission ends with documented, cleaned data and checked splits. Feature fitting,
model training and measured classification results begin in later milestones.
