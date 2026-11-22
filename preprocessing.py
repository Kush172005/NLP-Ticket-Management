"""Fixed text cleaning and duplicate grouping. No vocabulary or model is fitted."""
import re
import unicodedata
from collections import defaultdict

from config import NEAR_DUPLICATE_THRESHOLD

PATTERNS = {
    "url": re.compile(r"https?://\S+|www\.\S+", re.I),
    "email": re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", re.I),
    "card": re.compile(r"(?<!\w)(?:\d[ -]?){12,18}\d(?!\w)"),
    "phone": re.compile(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)"),
    "number": re.compile(r"\b\d+(?:[.,]\d+)*\b"),
}


def mask_text(text):
    text = unicodedata.normalize("NFKC", str(text)).replace("’", "'")
    for name, pattern in PATTERNS.items():
        text = pattern.sub(f" <{name}> ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text):
    text = mask_text(text).lower()
    for word, expanded in (("can't", "cannot"), ("won't", "will not"), ("shan't", "shall not")):
        text = re.sub(rf"\b{re.escape(word)}\b", expanded, text)
    for suffix, expanded in (("n't", " not"), ("'re", " are"), ("'ve", " have"),
                             ("'ll", " will"), ("'m", " am")):
        text = text.replace(suffix, expanded)
    text = re.sub(r"[^a-z<>\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def shingles(text):
    words = text.split()
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


def duplicate_groups(texts, threshold=NEAR_DUPLICATE_THRESHOLD):
    """Connect exact matches and long queries with similar word-trigram sets.

    The inverted index skips pairs that cannot share any trigram. Short queries
    use exact matching because a small wording change can change their intent.
    """
    parent = list(range(len(texts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)

    exact, index, sets, pairs = {}, defaultdict(list), [], []
    for i, text in enumerate(texts):
        if text in exact:
            union(i, exact[text])
            pairs.append((exact[text], i, 1.0, "exact"))
            sets.append(set())
            continue
        exact[text] = i
        current = shingles(text)
        sets.append(current)
        if len(current) < 3:
            continue
        candidates = {j for token in current for j in index[token]}
        for j in sorted(candidates):
            previous = sets[j]
            if min(len(current), len(previous)) / max(len(current), len(previous)) < threshold:
                continue
            similarity = len(current & previous) / len(current | previous)
            if similarity >= threshold:
                union(i, j)
                pairs.append((j, i, round(similarity, 6), "near"))
        for token in current:
            index[token].append(i)
    return [find(i) for i in range(len(texts))], pairs
