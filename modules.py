"""Rule-based / extractive components of the triage pipeline:
sentiment, priority, routing, summary, suggested reply."""
import re
import numpy as np
from config import (NEG_WORDS, POS_WORDS, NEGATIONS, INTENSIFIERS, URGENT_PHRASES,
                    ROUTING_RULES, DEFAULT_TEAM, URGENCY_RULES)


# ------------------------------------------------------------------ sentiment
def sentiment(raw: str) -> dict:
    """Lexicon sentiment with negation + intensifier handling + shouting/exclamation cues.
    Runs on RAW text (caps and '!' carry emotion, so we must not use the cleaned text)."""
    toks = re.findall(r"[a-zA-Z']+|!", raw)
    score, i = 0.0, 0
    low = [t.lower().replace("'", "") for t in toks]
    for i, t in enumerate(low):
        w = NEG_WORDS.get(t)
        sign = -1
        if w is None:
            w, sign = POS_WORDS.get(t), 1
        if w is None:
            continue
        mult = 1.0
        window = low[max(0, i - 3):i]
        for p in window:
            mult *= INTENSIFIERS.get(p, 1.0)
        if any(p in NEGATIONS or p.endswith("nt") for p in window):
            sign, mult = -sign, mult * 0.7        # "not happy" -> negative; "not bad" -> mild positive
        score += sign * w * mult
    caps_words = [t for t in toks if len(t) > 2 and t.isupper()]
    bangs = raw.count("!")
    score -= 0.8 * len(caps_words) + 0.5 * min(bangs, 4) if score < 0 or caps_words else 0
    if score <= -5:
        label = "angry"
    elif score <= -0.75:
        label = "negative"
    elif score >= 1.5:
        label = "positive"
    else:
        label = "neutral"
    return {"label": label, "score": round(float(score), 2)}


# ------------------------------------------------------------------ routing
def route(intent: str) -> str:
    key = intent.lower()
    for subs, team in ROUTING_RULES:
        if any(s in key for s in subs):
            return team
    return DEFAULT_TEAM


def intent_urgency(intent: str) -> int:
    key = intent.lower()
    for subs, lvl in URGENCY_RULES:
        if any(s in key for s in subs):
            return lvl
    return 0


# ------------------------------------------------------------------ priority
SENT_WEIGHT = {"angry": 3.0, "negative": 1.5, "neutral": 0.0, "positive": -0.5}


def priority(intent: str, sent: dict, raw: str, intent_conf: float) -> dict:
    """Transparent additive score so a PM / professor can read why a ticket is P1.
       score = 2*intent_urgency + sentiment_weight + 1.5*urgent_phrases(max 2) (+0.5 if low conf)"""
    u = intent_urgency(intent)
    urg_hits = sum(p in raw.lower() for p in URGENT_PHRASES)
    s = 2 * u + SENT_WEIGHT[sent["label"]] + 1.5 * min(urg_hits, 2)
    if intent_conf < 0.35:
        s += 0.5                                  # unsure -> bump so a human looks sooner
    if s >= 8 or u == 3:                          # security/fraud intents are always P1
        p = "P1 - Critical"
    elif s >= 4.5:
        p = "P2 - High"
    elif s >= 2.5:
        p = "P3 - Medium"
    else:
        p = "P4 - Low"
    return {"label": p, "score": round(s, 2), "intent_urgency": u, "urgent_phrases": urg_hits}


# ------------------------------------------------------------------ summary
FILLER = re.compile(r"^(hi|hello|hey|please help|i need help|quick question|thanks in advance|dear [a-z ]+)[,.:!]*\s*", re.I)


def humanize(intent: str) -> str:
    return intent.replace("_", " ").strip().lower()


def summarize(raw: str, intent: str, idf: dict) -> str:
    """Extractive: pick the most informative sentence (sum of idf of its words), prefix with issue type."""
    sents = [FILLER.sub("", s).strip() for s in re.split(r"(?<=[.!?])\s+", raw.strip()) if s.strip()]
    sents = [s for s in sents if len(s.split()) >= 3] or [raw.strip()]
    def sc(s):
        ws = re.findall(r"[a-z]+", s.lower())
        return sum(idf.get(w, 1.0) for w in set(ws)) / (len(ws) ** 0.5 + 1e-6)
    best = max(sents, key=sc)
    best = best[:200].rstrip(" .!") + ("..." if len(best) > 200 else "")
    return f"[{humanize(intent)}] {best}"


# ------------------------------------------------------------------ reply
EMPATHY = {
    "angry": "I am really sorry for the trouble this has caused, and I understand how frustrating this is.",
    "negative": "I am sorry about the inconvenience.",
    "neutral": "thanks for reaching out.",
    "positive": "thanks for getting in touch.",
}
ACTIONS = {
    "Fraud & Security": "For your safety, we have flagged this for our security team. Please freeze your card from the app now if you have not already; a specialist will contact you shortly.",
    "KYC & Account Support": "Our account team will review this. Please keep your ID documents handy in case we need to re-verify.",
    "Billing & Disputes": "Our billing team is reviewing the charge on your account and will confirm any correction or refund.",
    "Payments & Transfers": "Our payments team is tracing this transaction and will update you as soon as we have its status.",
    "Cards Support": "Our cards team will help with this right away.",
    "General Support": "A support specialist will look into this and get back to you.",
}
SLA = {"P1 - Critical": "within 1 hour", "P2 - High": "within 4 hours",
       "P3 - Medium": "within 1 business day", "P4 - Low": "within 2 business days"}


def reply(sent_label: str, team: str, prio: str, intent: str) -> str:
    return (f"Hi, {EMPATHY[sent_label]} We have logged your request about "
            f"\"{humanize(intent)}\". {ACTIONS[team]} You can expect an update {SLA[prio]}.")
