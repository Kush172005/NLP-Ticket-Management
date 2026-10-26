"""Shared config: paths, intent -> team routing, intent urgency, keyword lists."""
from pathlib import Path

ROOT = Path(__file__).parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
for p in (DATA_RAW, DATA_PROC, MODELS, REPORTS):
    p.mkdir(parents=True, exist_ok=True)

SEED = 42

# ---- Routing: substring of intent label -> team (first match wins, order matters) ----
ROUTING_RULES = [
    (("lost_or_stolen", "compromised", "swallowed", "stolen_phone", "not_recognised",
      "fraud", "unauthorised"), "Fraud & Security"),
    (("verify", "identity", "source_of_funds", "age_limit", "passcode",
      "edit_personal", "terminate_account"), "KYC & Account Support"),
    (("refund", "extra_charge", "fee_charged", "exchange_charge", "wrong_exchange",
      "wrong_amount", "cash_withdrawal_charge", "transfer_fee"), "Billing & Disputes"),
    (("transfer", "top_up", "balance_not_updated", "beneficiary", "direct_debit",
      "receiving_money", "pending_cash", "declined_cash", "pending_card_payment",
      "declined_card_payment", "failed"), "Payments & Transfers"),
    (("card", "pin", "atm", "contactless", "apple_pay", "virtual", "disposable", "visa"),
     "Cards Support"),
]
DEFAULT_TEAM = "General Support"

# ---- Intent urgency (0-3): how much money / security risk the intent carries ----
URGENCY_RULES = [
    (("lost_or_stolen", "compromised", "swallowed", "stolen_phone", "not_recognised"), 3),
    (("declined", "failed", "reverted", "not_received", "wrong_amount", "pending",
      "not_updated", "extra_charge", "wrong_exchange", "blocked", "refund",
      "not_working"), 2),
    (("fee", "charge", "limit", "verify", "identity", "terminate"), 1),
]

# ---- Keyword lists for rule-based sentiment / priority ----
NEG_WORDS = {
    "angry": 3, "furious": 3, "outraged": 3, "unacceptable": 3, "ridiculous": 3,
    "worst": 3, "scam": 3, "fraud": 2, "terrible": 3, "awful": 3, "horrible": 3,
    "useless": 3, "disgusted": 3, "pathetic": 3, "fed": 1, "frustrated": 2,
    "frustrating": 2, "annoyed": 2, "annoying": 2, "disappointed": 2, "upset": 2,
    "bad": 1, "wrong": 1, "problem": 1, "issue": 1, "stuck": 1, "unhappy": 2,
    "waiting": 1, "still": 1, "never": 1, "again": 1, "worried": 1, "stolen": 1,
    "lost": 1, "failed": 1, "declined": 1, "charged": 1, "missing": 1, "blocked": 1,
    "swallowed": 1, "hacked": 1, "twice": 1, "double": 1, "delay": 1, "delayed": 1,
    "urgently": 1, "refuse": 2, "ignored": 2, "rubbish": 3, "joke": 2, "nobody": 1,
}
POS_WORDS = {
    "thanks": 2, "thank": 2, "great": 2, "good": 1, "love": 2, "happy": 2,
    "excellent": 3, "awesome": 2, "perfect": 2, "appreciate": 2, "helpful": 2,
    "wonderful": 2, "pleased": 2, "please": 0.5,
}
NEGATIONS = {"not", "no", "never", "n't", "cannot", "cant", "dont", "didnt", "isnt",
             "wasnt", "wont", "without"}
INTENSIFIERS = {"very": 1.5, "extremely": 2.0, "really": 1.4, "so": 1.3, "totally": 1.6,
                "absolutely": 1.8, "completely": 1.6, "seriously": 1.4}
URGENT_PHRASES = ["immediately", "urgent", "asap", "right now", "right away",
                  "as soon as possible", "emergency", "today", "now!", "within hours",
                  "legal action", "consumer court", "ombudsman", "escalate", "close my account",
                  "switch banks", "report this", "police"]
