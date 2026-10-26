"""The 'Analyze' button: raw ticket text -> structured triage result.
Usage:  python analyze.py "I'm FURIOUS, my card was stolen and you do nothing!"
"""
import sys
import json
import joblib
from config import MODELS
from m2_preprocess import clean_text
import modules as M

_model = None
_idf = None


def _load():
    global _model, _idf
    if _model is None:
        _model = joblib.load(MODELS / "intent_model.joblib")
        vec = _model.steps[0][1]
        _idf = dict(zip(vec.get_feature_names_out(), vec.idf_))
    return _model, _idf


def analyze(text: str) -> dict:
    model, idf = _load()
    cleaned = clean_text(text)
    proba = model.predict_proba([cleaned])[0]
    order = proba.argsort()[::-1][:3]
    intent, conf = model.classes_[order[0]], float(proba[order[0]])
    sent = M.sentiment(text)                       # raw text on purpose
    team = M.route(intent)
    prio = M.priority(intent, sent, text, conf)
    return {
        "category": intent,
        "confidence": round(conf, 3),
        "top3": [(model.classes_[i], round(float(proba[i]), 3)) for i in order],
        "needs_human_review": conf < 0.35,
        "sentiment": sent,
        "priority": prio,
        "route_to": team,
        "summary": M.summarize(text, intent, idf),
        "suggested_reply": M.reply(sent["label"], team, prio["label"], intent),
    }


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "This is UNACCEPTABLE!! My card was stolen yesterday and I still can't block it. Fix this immediately."
    print(json.dumps(analyze(msg), indent=2))
