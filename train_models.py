"""Train and compare simple text classifiers for Banking77 (Milestone 3)."""
import json

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score

from config import PROCESSED, ROOT, SEED

MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"


def load_split(name):
    """Read one prepared split. The model only sees clean_text and label."""
    return pd.read_csv(PROCESSED / f"{name}.csv", keep_default_na=False)


def score(model, texts, labels):
    predictions = model.predict(texts)
    return {
        "accuracy": round(accuracy_score(labels, predictions), 4),
        "macro_f1": round(f1_score(labels, predictions, average="macro"), 4),
        "weighted_f1": round(f1_score(labels, predictions, average="weighted"), 4),
    }


def build_models():
    """Return a simple baseline and a richer word+character model."""
    baseline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("classifier", LogisticRegression(C=4, max_iter=1000, random_state=SEED)),
    ])
    improved = Pipeline([
        ("features", FeatureUnion([
            ("words", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
            ("characters", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                           min_df=2, sublinear_tf=True, max_features=300000)),
        ])),
        ("classifier", LinearSVC(C=1.0, random_state=SEED)),
    ])
    return {
        "majority_guess": DummyClassifier(strategy="most_frequent"),
        "word_tfidf_logistic_regression": baseline,
        "word_and_character_tfidf_linear_svm": improved,
    }


def main():
    MODEL_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    train, val, test = (load_split(name) for name in ("train", "val", "test"))
    x_train, y_train = train.clean_text, train.label
    results = []
    fitted = {}

    # Compare every candidate on validation data. The official test data is untouched here.
    for name, model in build_models().items():
        model.fit(x_train, y_train)
        fitted[name] = model
        results.append({"model": name, "split": "validation", **score(model, val.clean_text, val.label)})
        print(f"{name}: {results[-1]}")

    # Pick the strongest model using validation macro F1, the project's main metric.
    candidates = [row for row in results if row["model"] != "majority_guess"]
    winner = max(candidates, key=lambda row: row["macro_f1"])["model"]

    # Refit the selected approach on train + validation, then use the official test once.
    final_model = fitted[winner]
    final_model.fit(pd.concat([train.clean_text, val.clean_text]),
                    pd.concat([train.label, val.label]))
    test_scores = score(final_model, test.clean_text, test.label)
    results.append({"model": winner, "split": "test_final", **test_scores})
    joblib.dump(final_model, MODEL_DIR / "banking77_intent_model.joblib")

    test_predictions = final_model.predict(test.clean_text)
    report = classification_report(test.label, test_predictions, output_dict=True, zero_division=0)
    (REPORT_DIR / "test_classification_report.json").write_text(json.dumps(report, indent=2) + "\n")
    pd.DataFrame(results).to_csv(REPORT_DIR / "m3_experiment_log.csv", index=False)
    summary = {
        "selected_model": winner,
        "selection_rule": "Highest validation macro F1 among trained text models",
        "train_rows": len(train), "validation_rows": len(val), "test_rows": len(test),
        "validation_results": [row for row in results if row["split"] == "validation"],
        "final_test_result": test_scores,
        "test_report": "reports/test_classification_report.json",
        "model_file": "models/banking77_intent_model.joblib",
        "warning": "Benchmark results do not establish real-bank performance or time savings.",
    }
    (REPORT_DIR / "m3_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Selected using validation macro F1: {winner}")
    print(f"Final held-out test result: {test_scores}")


if __name__ == "__main__":
    main()
