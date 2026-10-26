import re
import joblib
from config import MODELS

model = joblib.load(MODELS / "intent_model.joblib")

def clean_text(text):
    text = text.lower().strip()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

ticket = input("Enter your banking ticket: ").strip()

if not ticket:
    print("Please enter a ticket message.")
    raise SystemExit(1)

cleaned = clean_text(ticket)

probabilities = model.predict_proba([cleaned])[0]
classes = model.classes_
top_indices = probabilities.argsort()[::-1][:3]

print("\n===== TICKET PREDICTION =====")
print("Ticket:", ticket)
print("Predicted intent:", classes[top_indices[0]])
print(f"Confidence: {probabilities[top_indices[0]]:.2%}")

print("\nTop 3 possible intents:")
for index in top_indices:
    print(f"- {classes[index]}: {probabilities[index]:.2%}")
