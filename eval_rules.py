"""Small hand-labelled set to sanity-check the RULE-BASED parts (sentiment, priority).
banking77 has intent labels only - no sentiment/priority ground truth - so we create our own.
(text, expected_sentiment, expected_priority)  -- extend this set to 100+ before final submission."""
import json
from analyze import analyze

EVAL = [
    ("This is UNACCEPTABLE!! My card was stolen yesterday and I still cannot block it. Fix this immediately.", "angry", "P1 - Critical"),
    ("I lost my card, please block it asap", "negative", "P1 - Critical"),
    ("There is a payment on my statement I do not recognise, I think my card is hacked", "negative", "P1 - Critical"),
    ("Worst bank ever. Third time my transfer failed and nobody replies. I will close my account!", "angry", "P2 - High"),
    ("My transfer is still pending after 5 days, very frustrating", "negative", "P2 - High"),
    ("The atm declined my withdrawal and I am stuck without cash right now", "negative", "P2 - High"),
    ("I was charged twice for the same purchase, please fix this", "negative", "P2 - High"),
    ("Where is my refund? It has been two weeks and I am really upset", "negative", "P2 - High"),
    ("Hi, how do I change my pin?", "neutral", "P4 - Low"),
    ("What is the exchange rate you use for conversion?", "neutral", "P4 - Low"),
    ("Can I use apple pay with my card?", "neutral", "P4 - Low"),
    ("How do I activate my new card", "neutral", "P4 - Low"),
    ("Thanks, the app is great. Just wondering how to get a virtual card", "positive", "P4 - Low"),
    ("Which countries are supported?", "neutral", "P4 - Low"),
    ("Why do you need to verify my identity?", "neutral", "P3 - Medium"),
    ("I want to update my address", "neutral", "P4 - Low"),
    ("Why was I charged a fee for a transfer? That is ridiculous", "negative", "P3 - Medium"),
    ("my top up failed again!! this app is useless", "angry", "P2 - High"),
    ("Not happy with the delay on my card delivery", "negative", "P3 - Medium"),
    ("The atm swallowed my card, I need help urgently", "negative", "P1 - Critical"),
]


def run():
    s_ok = p_ok = p_near = 0
    for text, es, ep in EVAL:
        r = analyze(text)
        s, p = r["sentiment"]["label"], r["priority"]["label"]
        s_ok += s == es
        p_ok += p == ep
        p_near += abs(int(p[1]) - int(ep[1])) <= 1
        if s != es or p != ep:
            print(f"MISS  sent {s}/{es}  prio {p}/{ep}  | {text[:70]}")
    n = len(EVAL)
    out = {"n": n, "sentiment_acc": round(s_ok / n, 3), "priority_exact": round(p_ok / n, 3),
           "priority_within_1_level": round(p_near / n, 3)}
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
