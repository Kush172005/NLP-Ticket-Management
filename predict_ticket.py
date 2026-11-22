"""Suggest likely Banking77 intents with the saved model."""
import argparse

import joblib

from config import ROOT
from preprocessing import clean_text


def main():
    parser = argparse.ArgumentParser(description="Suggest a Banking77 intent for one query.")
    parser.add_argument("text", help="One English banking support message")
    args = parser.parse_args()
    model_path = ROOT / "models" / "banking77_intent_model.joblib"
    if not model_path.exists():
        raise SystemExit("Model not found. Run: python train_models.py")
    model = joblib.load(model_path)
    cleaned = clean_text(args.text)
    label = model.predict([cleaned])[0]
    print(f"Top suggestion: {label}")

    # Linear SVM scores rank labels, but they are not probabilities.
    scores = model.decision_function([cleaned])[0]
    best = scores.argsort()[::-1][:3]
    print("Other likely categories:")
    for index in best[1:]:
        print(f"- {model.classes_[index]}")
    print("These are model suggestions, not certainty scores. Please have an agent review them.")


if __name__ == "__main__":
    main()
