"""Show text preparation in the terminal without predicting an intent."""
import argparse
import json

import pandas as pd

from config import REPORTS
from preprocessing import clean_text, mask_text


def main():
    parser = argparse.ArgumentParser(description="M2 preprocessing demonstration")
    parser.add_argument("--text", help="Use a public or fictional example without private details")
    args = parser.parse_args()
    if args.text is not None:
        if not args.text.strip():
            parser.error("Enter a non-blank query")
        print("Masked: ", mask_text(args.text))
        print("Cleaned:", clean_text(args.text))
        return
    stats_path = REPORTS / "m2_stats.json"
    if not stats_path.exists():
        parser.error("Run python m2_preprocess.py first")
    stats = json.loads(stats_path.read_text())
    print("Ticket Management System: M1 and M2")
    print("Dataset: Banking77, 13,083 original queries, 77 banking intents")
    print("\nPrepared splits")
    for name, part in stats["splits"].items():
        print(f"  {name:5} {part['rows']:5,} queries   {part['labels']} intents")
    print("\nTraining-source removals")
    for reason, count in stats["removals"].items():
        print(f"  {reason.replace('_', ' ')}: {count}")
    print("\nCross-split checks")
    for check, value in stats["leakage_checks"].items():
        print(f"  {check.replace('_', ' ')}: {value}")
    print("\nActual source examples (supported sensitive patterns already masked)")
    for row in pd.read_csv(REPORTS / "cleaning_examples.csv").head(3).itertuples():
        print(f"\n  Source label: {row.label}")
        print(f"  Before: {row.before_masked}\n  After:  {row.after}")


if __name__ == "__main__":
    main()
