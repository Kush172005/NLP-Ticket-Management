import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from config import REPORTS

fig, ax = plt.subplots(figsize=(16, 11))
ax.set_xlim(0, 16); ax.set_ylim(0, 11); ax.axis("off")

C = {"m2": "#DCEBFA", "m3": "#E3F4E1", "rule": "#FFF1D6", "io": "#F3E0F5", "edge": "#2F3E52"}


def box(x, y, w, h, title, sub="", fc="#fff", fs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                fc=fc, ec=C["edge"], lw=1.4))
    ax.text(x + w / 2, y + h * (0.64 if sub else 0.5), title, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=C["edge"])
    if sub:
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=8.3, color="#44546A")


def arrow(x1, y1, x2, y2, label="", rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                                 lw=1.5, color=C["edge"], connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.17, label, ha="center", fontsize=8, color="#44546A")


ax.text(8, 10.6, "AI-Powered Customer Support Intelligence & Ticket Triage Platform",
        ha="center", fontsize=16, fontweight="bold", color=C["edge"])
ax.text(8, 10.22, "Milestone 2 (offline data preprocessing)  +  Milestone 3 (models + live 'Analyze' pipeline)",
        ha="center", fontsize=10.5, color="#44546A")

# ---------------- M2 band
ax.add_patch(FancyBboxPatch((0.2, 6.55), 15.6, 3.3, boxstyle="round,pad=0.02,rounding_size=0.2",
                            fc="#F7FAFE", ec="#9DB9DD", lw=1.2, ls="--"))
ax.text(0.45, 9.55, "M2 - DATA PREPROCESSING  (offline, run once)", fontsize=10.5, fontweight="bold", color="#2B5C99")
xs = [0.5, 3.6, 6.7, 9.8, 12.9]
w, h, y = 2.5, 1.5, 7.55
box(xs[0], y, w, h, "1. Load data", "banking77 CSV\n(text, intent label)", C["m2"])
box(xs[1], y, w, h, "2. Audit + Clean", "lowercase, URLs/emails,\nmask card numbers (PII),\ncontractions, numbers", C["m2"])
box(xs[2], y, w, h, "3. De-duplicate", "same text+label removed;\nsame text, 2 labels\n= dropped (ambiguous)", C["m2"])
box(xs[3], y, w, h, "4. Stratified split", "70 / 15 / 15\ntrain / val / test\n(every intent in each)", C["m2"])
box(xs[4], y, w, h, "5. TF-IDF features", "uni+bi-grams, fit on\nTRAIN only (no leakage)", C["m2"])
for i in range(4):
    arrow(xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)
box(5.2, 6.75, 5.6, 0.55, "6. EDA: class balance, length distribution -> reports/m2_eda.png", fc="#fff", fs=9)
arrow(8, 7.55, 8, 7.32)

# ---------------- M3 training band
ax.add_patch(FancyBboxPatch((0.2, 3.95), 15.6, 2.35, boxstyle="round,pad=0.02,rounding_size=0.2",
                            fc="#F6FBF5", ec="#9CCB95", lw=1.2, ls="--"))
ax.text(0.45, 6.0, "M3a - MODEL DEVELOPMENT  (offline training)", fontsize=10.5, fontweight="bold", color="#2F7A2B")
box(0.5, 4.2, 3.1, 1.45, "Candidate models", "Majority baseline\nNaive Bayes | LogReg\nLinearSVC (calibrated)", C["m3"])
box(4.4, 4.2, 3.0, 1.45, "Select on VALIDATION", "accuracy + macro-F1\n(macro = fair to rare intents)", C["m3"])
box(8.2, 4.2, 3.0, 1.45, "Refit train+val", "report ONCE on\nuntouched TEST set", C["m3"])
box(12.0, 4.2, 3.5, 1.45, "intent_model.joblib", "top-3 acc, confidence check,\nconfusion pairs -> reports/", C["io"])
arrow(3.6, 4.92, 4.4, 4.92); arrow(7.4, 4.92, 8.2, 4.92); arrow(11.2, 4.92, 12.0, 4.92)
arrow(2.05, 6.55, 2.05, 5.7)
ax.text(2.25, 6.43, "processed splits + TF-IDF", fontsize=8, color="#44546A", va="center")

# ---------------- Inference band
ax.add_patch(FancyBboxPatch((0.2, 0.2), 15.6, 3.5, boxstyle="round,pad=0.02,rounding_size=0.2",
                            fc="#FFFCF5", ec="#E3C47F", lw=1.2, ls="--"))
ax.text(0.45, 3.4, "M3b - LIVE 'ANALYZE' PIPELINE  (seconds per ticket)", fontsize=10.5, fontweight="bold", color="#A8740A")
box(0.4, 1.9, 2.2, 1.1, "Customer ticket", "raw message", C["io"])
box(3.2, 1.9, 2.5, 1.1, "Intent classifier", "category + confidence\n+ top-3", C["m3"])
box(6.3, 2.35, 2.6, 0.75, "Sentiment (lexicon)", "raw text: negation, CAPS, '!'", C["rule"], fs=9.5)
box(6.3, 1.45, 2.6, 0.75, "Urgency phrases", "'immediately', 'legal action'", C["rule"], fs=9.5)
box(9.5, 1.9, 2.4, 1.1, "Priority P1-P4", "2 x intent urgency\n+ sentiment + phrases", C["rule"])
box(12.5, 2.35, 3.0, 0.75, "Routing -> team", "intent -> 6 support queues", C["rule"], fs=9.5)
box(12.5, 1.45, 3.0, 0.75, "Summary + reply", "extractive + template w/ SLA", C["rule"], fs=9.5)
arrow(2.6, 2.45, 3.2, 2.45)
arrow(5.7, 2.6, 6.3, 2.7, rad=0.0); arrow(5.7, 2.3, 6.3, 1.85)
arrow(8.9, 2.72, 9.5, 2.55); arrow(8.9, 1.85, 9.5, 2.25)
arrow(11.9, 2.6, 12.5, 2.72); arrow(11.9, 2.2, 12.5, 1.85)
ax.text(8, 0.8, "Output card: category | sentiment | priority | team | summary | suggested reply | needs_human_review (if confidence < 0.35)",
        ha="center", fontsize=9.5, color=C["edge"],
        bbox=dict(boxstyle="round", fc="#F3E0F5", ec=C["edge"]))
arrow(4.45, 3.95, 4.45, 3.02)
ax.text(4.6, 3.82, "loads intent_model.joblib", fontsize=8, color="#44546A", va="center")

plt.savefig(REPORTS / "architecture_m2_m3.png", dpi=150, bbox_inches="tight", facecolor="white")
