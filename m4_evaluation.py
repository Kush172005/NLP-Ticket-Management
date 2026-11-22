"""Tune and evaluate the Banking77 model using validation data and fixed checks."""
import json
import re

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, classification_report, f1_score

from config import PROCESSED, REPORTS, ROOT, SEED

MODEL_PATH = ROOT / "models" / "banking77_intent_model.joblib"


def load_data(name):
    return pd.read_csv(PROCESSED / f"{name}.csv", keep_default_na=False)


def make_model(c_value=1.0):
    """Build word and character clues, then classify with a linear SVM."""
    features = FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("characters", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                       min_df=2, sublinear_tf=True, max_features=300000)),
    ])
    return Pipeline([
        ("features", features),
        ("classifier", LinearSVC(C=c_value, random_state=SEED)),
    ])


def measures(model, frame):
    predicted = model.predict(frame.clean_text)
    return {
        "accuracy": round(accuracy_score(frame.label, predicted), 4),
        "macro_f1": round(f1_score(frame.label, predicted, average="macro"), 4),
        "weighted_f1": round(f1_score(frame.label, predicted, average="weighted"), 4),
    }


def swap_one_pair(text):
    """Make one small spelling disturbance in the longest usable word."""
    words = text.split()
    choices = [i for i, word in enumerate(words) if len(word) >= 5 and word.isalpha()]
    if not choices:
        return text
    index = max(choices, key=lambda i: len(words[i]))
    word = words[index]
    words[index] = word[0] + word[2] + word[1] + word[3:]
    return " ".join(words)


def keep_first_half(text):
    words = text.split()
    return " ".join(words[:max(1, len(words) // 2)])


def perturb(frame, kind):
    """Create predictable stress inputs from the masked validation messages."""
    texts = frame.masked_text.astype(str).tolist()
    changed = []
    for text in texts:
        if kind == "case_and_punctuation":
            changed.append(text.upper() + "!!!")
        elif kind == "one_character_swap":
            changed.append(swap_one_pair(text))
        elif kind == "first_half_only":
            changed.append(keep_first_half(text))
        else:
            raise ValueError(f"Unknown robustness check: {kind}")
    # Import here so validation uses the same deterministic cleaning as inference.
    from preprocessing import clean_text
    return [clean_text(text) for text in changed]


def error_analysis(model, test):
    predictions = model.predict(test.clean_text)
    report = classification_report(test.label, predictions, output_dict=True, zero_division=0)
    (REPORTS / "m4_test_per_intent.json").write_text(json.dumps(report, indent=2) + "\n")

    rows = []
    for row, prediction in zip(test.itertuples(index=False), predictions):
        if row.label == prediction:
            continue
        tags = []
        if len(row.clean_text.split()) <= 5:
            tags.append("short_query_5_words_or_fewer")
        if re.search(r"<(?:url|email|card|phone|number)>", row.masked_text):
            tags.append("contains_masked_value")
        if not tags:
            tags.append("other_misclassification")
        rows.append({
            "row_id": row.row_id,
            "true_label": row.label,
            "predicted_label": prediction,
            "error_tags": ";".join(tags),
            "clean_text": row.clean_text,
        })
    errors = pd.DataFrame(rows, columns=["row_id", "true_label", "predicted_label", "error_tags", "clean_text"])
    errors.to_csv(REPORTS / "m4_test_errors.csv", index=False)

    confusion = (errors.groupby(["true_label", "predicted_label"]).size()
                 .reset_index(name="count").sort_values("count", ascending=False))
    confusion.to_csv(REPORTS / "m4_common_confusions.csv", index=False)
    per_tag = {}
    for tag in ("short_query_5_words_or_fewer", "contains_masked_value", "other_misclassification"):
        per_tag[tag] = int(errors.error_tags.str.contains(tag).sum()) if len(errors) else 0
    return {
        "test_rows": len(test),
        "wrong_predictions": len(errors),
        "error_rate": round(len(errors) / len(test), 4),
        "error_tag_counts_note": "Tags may overlap; other is used when neither defined pattern applies.",
        "error_tag_counts": per_tag,
        "files": ["reports/m4_test_errors.csv", "reports/m4_common_confusions.csv",
                  "reports/m4_test_per_intent.json"],
    }


def main():
    REPORTS.mkdir(exist_ok=True)
    train, val, test = (load_data(name) for name in ("train", "val", "test"))
    experiments = []
    candidates = {}

    # Iteration 1: try a softer margin. Iteration 2: try a stronger margin.
    # C=1.0 is the M3 model setting and acts as the reference.
    for name, c_value in (("softer_margin_c_0_5", 0.5),
                          ("m3_reference_c_1_0", 1.0),
                          ("stronger_margin_c_2_0", 2.0)):
        model = make_model(c_value)
        model.fit(train.clean_text, train.label)
        result = {"iteration": name, "C": c_value, "split": "validation", **measures(model, val)}
        experiments.append(result)
        candidates[name] = model
        print(result)

    best_row = max(experiments, key=lambda item: item["macro_f1"])
    # Tiny score changes can be noise. Keep the familiar M3 setting unless a
    # candidate improves validation macro F1 by at least 0.001 (0.1 points).
    reference_row = next(item for item in experiments if item["C"] == 1.0)
    if best_row["macro_f1"] - reference_row["macro_f1"] < 0.001:
        winner_row = reference_row
        decision = "Kept C=1.0 because the best candidate gain was below 0.001 macro F1."
    else:
        winner_row = best_row
        decision = "Selected the candidate with the best validation macro F1."
    winner_name = winner_row["iteration"]
    winner_c = winner_row["C"]

    # Lock the settings using validation results, then refit with all non-test data.
    final_model = make_model(winner_c)
    final_model.fit(pd.concat([train.clean_text, val.clean_text]),
                    pd.concat([train.label, val.label]))
    test_scores = measures(final_model, test)
    joblib.dump(final_model, MODEL_PATH)

    # Robustness checks use only validation inputs. They are stress tests, not new labels.
    robustness = []
    # This model was fit on train only, so validation remains unseen in this check.
    robustness_model = candidates[winner_name]
    clean_prediction = robustness_model.predict(val.clean_text)
    from preprocessing import clean_text
    for kind in ("case_and_punctuation", "one_character_swap", "first_half_only"):
        changed = perturb(val, kind)
        changed_predictions = robustness_model.predict(changed)
        robustness.append({
            "check": kind,
            "accuracy_after_change": round(accuracy_score(val.label, changed_predictions), 4),
            "same_prediction_as_original_fraction": round(
                sum(a == b for a, b in zip(clean_prediction, changed_predictions)) / len(val), 4),
            "purpose": {
                "case_and_punctuation": "Expected invariance to casing and punctuation after normalization.",
                "one_character_swap": "Stress check for a small typo; exact same label is not guaranteed.",
                "first_half_only": "Stress check for incomplete input; loss of meaning can change the correct intent.",
            }[kind],
        })

    error_summary = error_analysis(final_model, test)
    experiments.append({"iteration": winner_name, "C": winner_c, "split": "test_final", **test_scores})
    pd.DataFrame(experiments).to_csv(REPORTS / "m4_experiment_log.csv", index=False)
    summary = {
        "selection_metric": "validation macro F1",
        "selection_rule": "Use the best validation macro F1; retain M3 C=1.0 if the gain is under 0.001.",
        "selection_decision": decision,
        "m3_reference_validation": next(item for item in experiments
                                          if item["iteration"] == "m3_reference_c_1_0"),
        "selected_iteration": winner_name,
        "selected_C": winner_c,
        "selected_validation_result": winner_row,
        "final_test_result": test_scores,
        "test_error_analysis": error_summary,
        "robustness_validation_results": robustness,
        "inference_model": "models/banking77_intent_model.joblib",
        "note": "Test scores/errors are descriptive only. They were not used to select settings. Robustness model was trained on train only; validation stayed unseen.",
    }
    (REPORTS / "m4_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Selected setting: {winner_name} (C={winner_c})")
    print(f"Final test metrics: {test_scores}")
    print(f"Test error analysis: {error_summary}")
    print(f"Robustness results: {robustness}")


if __name__ == "__main__":
    main()
