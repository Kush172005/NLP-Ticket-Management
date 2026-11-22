"""Predict one banking intent with the saved Milestone 3 model."""
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
    label = model.predict([clean_text(args.text)])[0]
    print(f"Suggested intent: {label}")
    print("Please have a support agent review this suggestion.")


if __name__ == "__main__":
    main()
