# Presentation Q&A — M2 + M3
Short, defensible answers. Replace `[X]` with *your* real numbers after running on banking77.

---

## A. Data & preprocessing (M2)

**1. Why banking77?**
Public, real customer-style queries, 77 fine-grained intents — a hard enough classification task, and banking maps directly to my ticket-triage use case (fraud, transfers, cards). Limitation: it is one domain, so I claim banking support, not "all support".

**2. It has no sentiment or priority labels. How do you get them?**
Intent is learned (supervised). Sentiment and priority are rule-based, deliberately: no labels exist, rules are explainable, and support managers can edit them without retraining. I validated them on a hand-labelled set and I am transparent that this is the weaker part (M4 upgrades it).

**3. Why re-split instead of using the given train/test?**
I need three sets: train to fit, validation to choose the model, test to report once. Selecting a model on the test set would make the reported score optimistic.

**4. What is stratified splitting and why?**
Each split keeps the same per-intent proportions. With 77 classes and few examples per class, a random split can leave a rare intent out of test entirely.

**5. What is data leakage and where did you prevent it?**
Information from val/test reaching training. Three places: (a) TF-IDF vocabulary/IDF fit on **train only**; (b) duplicates removed *before* splitting so the same sentence is not in both train and test; (c) test touched once, at the end.

**6. Why remove conflicting duplicates?**
Same text with two labels teaches the model contradictory targets and caps achievable accuracy; it is label noise.

**7. Why mask card numbers?**
Banking data is regulated; PII should not enter logs, training data or model artefacts. I mask before anything is stored — privacy-by-design.

**8. Why no stemming / stop-word removal?**
Short texts: words like "not", "no", "never" carry meaning ("card **not** working"). Removing stop-words risks deleting negation. Bigrams capture "not working".

**9. Why clean for the classifier but not for sentiment?**
CAPS, "!!" and negation are emotional signals. Lowercasing and stripping punctuation would erase exactly what sentiment needs.

**10. Class imbalance?**
Report imbalance ratio from EDA ([X]). banking77 is only mildly imbalanced, so I use **macro-F1** (every intent counts equally) instead of relying on accuracy alone; class weights are an M4 experiment if needed.

---

## B. Models (M3)

**11. Why TF-IDF + linear models and not BERT?**
For M3 I wanted a strong, fast, explainable baseline: trains in seconds on CPU, easy to debug. A fine-tuned transformer is the planned M4 comparison — if it wins by [X] points, I can quantify whether the extra cost is worth it.

**12. What does TF-IDF do?**
Scores a word high if frequent in this ticket but rare across all tickets, so "stolen" matters and "my" does not. 1–2 grams add short phrases.

**13. Why a majority-class baseline?**
It is the floor. If my model is not clearly above it, it has learned nothing. Reported: [X]%.

**14. How did you choose the final model?**
Highest **macro-F1 on validation** among NB, LogReg, calibrated LinearSVC. Then refit on train+val and evaluated once on test: accuracy [X], macro-F1 [X], top-3 [X].

**15. What is calibration and why did you add it?**
LinearSVC outputs margins, not probabilities. `CalibratedClassifierCV` converts them so "0.9 confidence" really means ≈90% right. I need honest confidence for the human-review threshold.

**16. What is the confidence threshold for?**
Below 0.35 the ticket is flagged `needs_human_review` and priority is bumped. It trades automation for safety; the threshold is tunable from the accuracy-vs-confidence table.

**17. Why top-3 accuracy?**
If the top-1 is wrong but the right intent is in the top 3, an agent can fix it in one click. It reflects the real workflow.

**18. Which intents are confused and why?**
From `m3_test_results.json` → top confusions (e.g. [X] vs [X]). Typically semantically close pairs like *declined transfer* vs *failed transfer*, or *pending* vs *not received*. Root cause is label overlap, not model weakness.

**19. Is 99%/100% accuracy believable?**
No — unusually high accuracy should prompt checks for data leakage, duplicate examples, and an overly easy evaluation set. On the official Banking77 test set, the recorded results are 89.25% accuracy, 89.26% macro-F1, and 96.72% top-3 accuracy.

---

## C. Priority, sentiment, routing, reply

**20. How is priority computed?**
`2 × intent urgency + sentiment weight + 1.5 × urgent phrases`, thresholds → P1–P4. Lost/stolen/compromised card is always P1. Fully additive so I can show *why* a ticket got P1.

**21. Why not train a priority model?**
No priority ground truth. Training on my own rule outputs would just copy the rules. With real historical tickets + agent-assigned priorities, I would train one.

**22. How accurate is sentiment/priority?**
On my [N]-ticket hand-labelled set: sentiment [X]%, priority exact [X]%, within-one-level [X]%. Caveat: small, self-labelled; rules were tuned on part of it.

**23. Where will sentiment fail?**
Sarcasm ("great, another failed transfer"), mild complaints with polite wording, and non-English / Hinglish text. M4: compare against a pre-trained sentiment model.

**24. How does routing work?**
Intent → team lookup table (6 teams). Deterministic and auditable; ops can change a mapping without retraining.

**25. Is the reply generated by an LLM?**
No — templated: empathy line (by sentiment) + team action + SLA (by priority). Intentionally safe: it cannot invent promises or refund amounts. LLM drafting + human approval is a possible extension.

**26. How is the summary made?**
Extractive: remove greetings, pick the sentence with the highest summed IDF, prepend the category. It cannot hallucinate because it only reuses the customer's words.

---

## D. Evaluation, business, critique

**27. Which metric matters most for the business?**
Priority/routing errors on **P1** tickets (a missed fraud case is costly). Overall accuracy hides this; I would report P1 recall separately.

**28. What is the business impact?**
Target: lower first-response time and misrouting rate. Measured in M6 by simulation (e.g. manual triage time vs seconds), not claimed yet.

**29. Biggest weakness of your system?**
Sentiment/priority are rule-based and validated on a small set; single-domain, single-intent data. I would fix this with labelled tickets from a real support desk.

**30. What would you do with more time/data?**
Fine-tune DistilBERT; multi-label intents (tickets with two problems); learned priority from agent history; multilingual support; drift monitoring.

**31. How would this go to production?**
REST API around `analyze()`, model + thresholds versioned, human-review queue, log confidence and agent overrides → retrain monthly.

**32. Ethical/privacy risks?**
PII in tickets (masked), biased sentiment on dialects/non-native English, automation errors on vulnerable customers — hence human-in-the-loop for low confidence and P1.

---

## E. Rapid-fire (one-liners)
- **Precision vs recall?** Precision = of predicted X, how many right. Recall = of actual X, how many found.
- **Macro vs weighted F1?** Macro averages per-class equally; weighted favours big classes.
- **Overfitting?** Great on train, worse on val/test. Controlled by regularisation + separate val/test.
- **Why bigrams?** "not working" ≠ "working".
- **Why fit TF-IDF on train only?** To avoid test leakage.
- **Why sublinear tf?** Log-damps repeated words so one repeated word doesn't dominate.
- **Why `min_df=2`?** Drops words seen once (typos, noise) → smaller, more stable vocabulary.
- **Random seed?** Fixed (`42`) so results are reproducible.

---

## Demo script (60 seconds)
1. Calm ticket: *"How do I change my pin?"* → P4, Cards Support.
2. Angry ticket: *"This is UNACCEPTABLE!! My card was stolen yesterday and I still cannot block it. Fix this immediately."* → angry, P1, Fraud & Security.
3. Ambiguous ticket → low confidence → `needs_human_review`. **Test candidates on your real model before the demo** (e.g. *"something is wrong with my account"*, *"help"*); pick one that actually falls below 0.35. Say: "this is the safety valve." If none does, lower-confidence behaviour is shown from the accuracy-vs-confidence table instead.
