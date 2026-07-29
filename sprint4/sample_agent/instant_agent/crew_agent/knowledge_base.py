"""
knowledge_base.py
------------------
Loads the local product catalog and company context from JSON files in
/data and exposes fast, cheap (no-LLM) lookup helpers. Agents call these
through tools instead of hitting the web, keeping responses fast and
token-light.

Bilingual + fuzzy matching: the catalog text (names/specs) is in English,
but users write in Arabic - often with typos or dialect spelling
("لابتويات" instead of "لابتوبات", missing/extra "ال", etc). SYNONYMS maps
common Arabic/English terms to a category. Matching tolerates small
spelling differences, and only the single best-scoring category is kept
for fuzzy (non-exact) hits, so one stray typo can't pull in an unrelated
category and mix results together.
"""

import difflib
import json
import os
import re
from functools import lru_cache

from secret_config import DATA_DIR

PRODUCTS_PATH = os.path.join(DATA_DIR, "products.json")
CONTEXT_PATH = os.path.join(DATA_DIR, "company_context.json")

FUZZY_THRESHOLD = 0.72

# Arabic (formal + colloquial) and English synonyms -> catalog category.
SYNONYMS = {
    # Laptops
    "لابتوب": "Laptops", "لاب توب": "Laptops", "لابتوبات": "Laptops",
    "لاب": "Laptops", "notebook": "Laptops", "laptop": "Laptops",
    # Servers
    "سيرفر": "Servers", "سيرفرات": "Servers", "خادم": "Servers", "خوادم": "Servers", "server": "Servers",
    # Monitors
    "شاشة": "Monitors", "شاشات": "Monitors", "مونيتور": "Monitors", "monitor": "Monitors", "screen": "Monitors",
    # Networking
    "شبكة": "Networking", "شبكات": "Networking", "راوتر": "Networking", "سويتش": "Networking",
    "network": "Networking", "switch": "Networking", "router": "Networking",
    # Printers
    "طابعة": "Printers", "طابعات": "Printers", "printer": "Printers",
    # Office Furniture
    "كرسي": "Office Furniture", "كراسي": "Office Furniture", "أثاث": "Office Furniture",
    "اثاث مكتبي": "Office Furniture", "chair": "Office Furniture", "furniture": "Office Furniture",
    # Software Licenses (note: "ترخيص/تراخيص" deliberately excluded - they
    # collide with the unrelated word "رخيص" (cheap) under fuzzy matching)
    "برنامج": "Software Licenses", "برامج": "Software Licenses",
    "software": "Software Licenses", "license": "Software Licenses",
}


# ---------------------------------------------------------------------------
# Fuzzy Arabic text matching helpers
# ---------------------------------------------------------------------------

def _normalize_arabic(text: str) -> str:
    """Strip diacritics and unify common letter variants so spelling
    differences (ا/أ/إ/آ, ة/ه, ى/ي) don't break matching."""
    text = re.sub(r"[\u064B-\u0652]", "", text)  # remove diacritics
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return text


def _strip_al_prefix(word: str) -> str:
    """Strip a leading Arabic definite article 'ال' (possibly doubled)."""
    while word.startswith("ال") and len(word) > 4:
        word = word[2:]
    return word


def _fuzzy_ratio(term: str, word: str) -> float:
    """
    Similarity between `term` and `word` (0-1), tolerant of typos and a
    missing/extra 'ال' prefix. A short string fully contained in a longer
    one counts as a full match ONLY if it makes up a large enough share of
    the longer word (avoids matching a short word buried inside an
    unrelated longer one).
    """
    term = _normalize_arabic(term.lower())
    word = _normalize_arabic(_strip_al_prefix(word.lower()))

    if not term or not word:
        return 0.0

    shorter, longer = (term, word) if len(term) <= len(word) else (word, term)
    if shorter in longer and len(shorter) / len(longer) >= 0.55:
        return 1.0

    if abs(len(term) - len(word)) > 2:
        return 0.0  # too different in length to be a typo of each other

    return difflib.SequenceMatcher(None, term, word).ratio()


def _match_categories(query: str) -> set:
    """
    Find catalog categories implied by the query. Exact/near-exact hits
    (ratio == 1.0) are all kept, since a query naming two real categories
    should return both. Below that, only the single best-scoring category
    is kept, so one fuzzy/typo-based hit can't drag in an unrelated one.
    """
    words = query.strip().split()
    if not words:
        return set()

    scores = {}
    for term, category in SYNONYMS.items():
        for word in words:
            ratio = _fuzzy_ratio(term, word)
            if ratio > scores.get(category, 0.0):
                scores[category] = ratio

    if not scores:
        return set()

    best = max(scores.values())
    if best < FUZZY_THRESHOLD:
        return set()
    if best >= 0.999:
        return {cat for cat, s in scores.items() if s >= 0.999}
    return {cat for cat, s in scores.items() if s == best}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_products():
    with open(PRODUCTS_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_company_context():
    with open(CONTEXT_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_categories():
    products = load_products()
    return sorted({p["category"] for p in products})


# ---------------------------------------------------------------------------
# Search / rank
# ---------------------------------------------------------------------------

def search_products(query: str, max_price: float = None, limit: int = 6):
    """
    Search the catalog. First tries fuzzy bilingual category synonyms (so
    Arabic or English words - even with typos - match instantly); falls
    back to plain keyword substring matching over name/brand/specs.
    """
    query_lower = (query or "").strip().lower()
    products = load_products()

    matched_categories = _match_categories(query_lower)

    if matched_categories:
        results = [p for p in products if p["category"] in matched_categories]
    else:
        results = []
        for p in products:
            haystack = " ".join([
                p["name"], p["brand"], p["category"],
                " ".join(f"{k} {v}" for k, v in p["specs"].items())
            ]).lower()
            if query_lower == "" or any(token in haystack for token in query_lower.split()):
                results.append(p)

    if max_price is not None:
        results = [p for p in results if p["price_usd"] <= max_price]

    results.sort(key=lambda p: p["price_usd"])
    return results[:limit]


def get_products_by_ids(ids):
    products = load_products()
    id_set = set(ids)
    return [p for p in products if p["id"] in id_set]


def rank_by_value(products, price_weight: float = 0.5, rating_weight: float = 0.5):
    """
    Simple value score: cheaper price and higher rating both increase score.
    Score is normalized 0-100 for readability, not a statistical guarantee.
    """
    if not products:
        return []

    prices = [p["price_usd"] for p in products]
    ratings = [p["rating"] for p in products]
    min_price, max_price = min(prices), max(prices)
    min_rating, max_rating = min(ratings), max(ratings)

    ranked = []
    for p in products:
        price_range = (max_price - min_price) or 1
        rating_range = (max_rating - min_rating) or 1

        price_score = 1 - ((p["price_usd"] - min_price) / price_range)
        rating_score = (p["rating"] - min_rating) / rating_range

        value_score = round(
            (price_score * price_weight + rating_score * rating_weight) * 100, 1
        )
        ranked.append({**p, "value_score": value_score})

    ranked.sort(key=lambda p: p["value_score"], reverse=True)
    return ranked