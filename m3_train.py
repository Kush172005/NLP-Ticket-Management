"""M3 - Model development: compare classifiers for ticket-intent classification,
pick the best on VALIDATION, report once on TEST, save the model.
Run: python m3_train.py   (after m2_preprocess.py)"""
import json
import time
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.dummy import DummyClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from config import DATA_PROC, MODELS, REPORTS, SEED


def tfidf():
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)


def main():
    tr = pd.read_csv(DATA_PROC / "train.csv")
    va = pd.read_csv(DATA_PROC / "val.csv")
    te = pd.read_csv(DATA_PROC / "test.csv")

    candidates = {
        "Majority baseline": make_pipeline(tfidf(), DummyClassifier(strategy="most_frequent")),
        "TF-IDF + Naive Bayes": make_pipeline(tfidf(), MultinomialNB(alpha=0.1)),
        "TF-IDF + LogReg": make_pipeline(tfidf(), LogisticRegression(C=10, max_iter=2000)),
        "TF-IDF + LinearSVC (calibrated)": make_pipeline(
            tfidf(), CalibratedClassifierCV(LinearSVC(C=1.0), cv=3)),
    }
    rows, fitted = [], {}
    for name, m in candidates.items():
        t0 = time.time()
        m.fit(tr.clean_text, tr.label)
        pred = m.predict(va.clean_text)
        rows.append({"model": name,
                     "val_acc": round(accuracy_score(va.label, pred), 4),
                     "val_macro_f1": round(f1_score(va.label, pred, average="macro"), 4),
                     "train_sec": round(time.time() - t0, 2)})
        fitted[name] = m
    res = pd.DataFrame(rows).sort_values("val_macro_f1", ascending=False)
    print(res.to_string(index=False))

    best_name = res.iloc[0].model
    best = fitted[best_name]
    # Final model: refit on train+val, evaluate ONCE on untouched test
    full = pd.concat([tr, va])
    best.fit(full.clean_text, full.label)
    pred = best.predict(te.clean_text)
    test = {"best_model": best_name,
            "test_acc": round(accuracy_score(te.label, pred), 4),
            "test_macro_f1": round(f1_score(te.label, pred, average="macro"), 4)}
    print(test)

    # top-3 accuracy (useful: agent can see 3 suggested intents when unsure)
    proba = best.predict_proba(te.clean_text)
    top3 = np.argsort(-proba, axis=1)[:, :3]
    cls = best.classes_
    test["test_top3_acc"] = round(float(np.mean([t in cls[r] for t, r in zip(te.label, top3)])), 4)

    # confidence calibration view: accuracy when model is confident vs not
    conf = proba.max(axis=1)
    correct = (pred == te.label.values)
    test["acc_when_conf>=0.5"] = round(float(correct[conf >= 0.5].mean()), 4) if (conf >= 0.5).any() else None
    test["share_conf>=0.5"] = round(float((conf >= 0.5).mean()), 4)
    test["acc_when_conf<0.5"] = round(float(correct[conf < 0.5].mean()), 4) if (conf < 0.5).any() else None

    rep = pd.DataFrame(classification_report(te.label, pred, output_dict=True, zero_division=0)).T
    rep.to_csv(REPORTS / "m3_per_class_report.csv")
    worst = rep.drop(["accuracy", "macro avg", "weighted avg"]).sort_values("f1-score").head(5)
    test["weakest_intents"] = {k: round(v, 3) for k, v in worst["f1-score"].items()}

    # most confused pairs
    cm = confusion_matrix(te.label, pred, labels=cls)
    np.fill_diagonal(cm, 0)
    idx = np.dstack(np.unravel_index(np.argsort(-cm, axis=None)[:5], cm.shape))[0]
    test["top_confusions"] = [f"{cls[i]} -> {cls[j]} ({cm[i, j]})" for i, j in idx if cm[i, j] > 0]

    joblib.dump(best, MODELS / "intent_model.joblib")
    res.to_csv(REPORTS / "m3_model_comparison.csv", index=False)
    json.dump(test, open(REPORTS / "m3_test_results.json", "w"), indent=2)

    ax = res.set_index("model")[["val_acc", "val_macro_f1"]].plot.barh(figsize=(8, 3.5))
    ax.set_title("M3: model comparison (validation)")
    plt.tight_layout()
    plt.savefig(REPORTS / "m3_model_comparison.png", dpi=130)
    print(json.dumps(test, indent=2))


if __name__ == "__main__":
    main()
