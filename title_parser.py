#!/usr/bin/env python3
"""
Parse cannabis product titles into structured components.
Extracts: brand, name, weight/unit, strain type, category hint.
"""
from __future__ import annotations
import re

# Weight patterns (covers g, mg, oz, lb, ml, pack sizes, mg:ml)
_WEIGHT_RE = re.compile(
    r'''
    (?P<qty>[\d.]+(?:/[\d.]+)?)   # quantity (e.g. 3.5, 1/8, 100)
    \s*
    (?P<unit>g|gram|grams|mg|oz|ounce|ounces|lb|lbs|ml|pack|ct|count|pcs|pieces|capsule|capsules|tab|tablets|
             1/8|1/4|1/2|oz|fl\.?oz)
    (?:\s|$|,|\))
    ''',
    re.I | re.VERBOSE,
)

# Strain-type keywords
_STRAIN_MAP = {
    "sativa": "SATIVA", "sat": "SATIVA",
    "indica": "INDICA", "ind": "INDICA",
    "hybrid": "HYBRID", "hyb": "HYBRID",
    "cbd": "CBD", "cbg": "CBG", "cbn": "CBN",
    "1:1": "BLEND",
}

# Common brand stopwords (don't treat these as brands)
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "with", "for", "by", "from",
    "cannabis", "dispensary", "weed", "flower", "pre-roll", "preroll",
    "cartridge", "cart", "edible", "tincture", "concentrate", "infused",
}

# Category hint keywords
_CAT_HINTS = {
    "flower": "Flower", "bud": "Flower", "nug": "Flower",
    "pre.?roll": "Pre-Roll", "preroll": "Pre-Roll", "joint": "Pre-Roll",
    "cart": "Vaporizer", "cartridge": "Vaporizer", "vape": "Vaporizer", "pod": "Vaporizer",
    "edible": "Edible", "gummy": "Edible", "gummies": "Edible", "chocolate": "Edible",
    "tincture": "Tincture", "drops": "Tincture",
    "concentrate": "Concentrate", "wax": "Concentrate", "shatter": "Concentrate",
    "rosin": "Concentrate", "live resin": "Concentrate", "badder": "Concentrate",
    "capsule": "Capsule", "pill": "Capsule",
    "topical": "Topical", "cream": "Topical", "lotion": "Topical", "balm": "Topical",
    "patch": "Topical", "suppository": "Topical",
    "beverage": "Beverage", "drink": "Beverage", "soda": "Beverage",
    "kief": "Kief", "hash": "Hash",
    "rso": "RSO", "distillate": "Distillate",
    "pet": "Pet",
}


def parse_title(title: str, brand: str | None = None, category: str | None = None) -> dict:
    """
    Decompose a cannabis product title into structured components.

    Returns:
        {
          "raw_title":    str,
          "clean_name":   str,   # title after removing weight/strain tokens
          "brand":        str | None,
          "weight":       str | None,   # e.g. "3.5g", "100mg"
          "weight_value": float | None,
          "weight_unit":  str | None,
          "strain_type":  str | None,   # SATIVA / INDICA / HYBRID / CBD / etc.
          "category_hint":str | None,
          "tokens":       list[str],
        }
    """
    if not title:
        return _empty(title)

    clean = title.strip()

    # ── 1. Extract weight ─────────────────────────────────────────────────────
    weight_str = weight_value = weight_unit = None
    wm = _WEIGHT_RE.search(clean)
    if wm:
        weight_str   = wm.group(0).strip().rstrip("),")
        weight_value = _to_float(wm.group("qty"))
        weight_unit  = wm.group("unit").lower()
        clean = (clean[:wm.start()] + " " + clean[wm.end():]).strip()

    # ── 2. Extract strain type ────────────────────────────────────────────────
    strain_type = None
    for kw, st in _STRAIN_MAP.items():
        pat = re.compile(r'\b' + re.escape(kw) + r'\b', re.I)
        if pat.search(clean):
            strain_type = st
            clean = pat.sub("", clean).strip()
            break

    # ── 3. Detect category hint ───────────────────────────────────────────────
    cat_hint = category
    if not cat_hint:
        for kw, ch in _CAT_HINTS.items():
            if re.search(r'\b' + kw + r'\b', title, re.I):
                cat_hint = ch
                break

    # ── 4. Clean up punctuation artifacts ────────────────────────────────────
    clean = re.sub(r'[\s,|\-]+$', "", clean)
    clean = re.sub(r'^[\s,|\-]+', "", clean)
    clean = re.sub(r'\s{2,}', " ", clean)

    return {
        "raw_title":    title,
        "clean_name":   clean or title,
        "brand":        brand,
        "weight":       weight_str,
        "weight_value": weight_value,
        "weight_unit":  weight_unit,
        "strain_type":  strain_type,
        "category_hint":cat_hint,
        "tokens":       [t for t in re.split(r'[\s,\-|]+', clean.lower()) if t and t not in _STOPWORDS],
    }


def _empty(title):
    return {"raw_title": title, "clean_name": title, "brand": None,
            "weight": None, "weight_value": None, "weight_unit": None,
            "strain_type": None, "category_hint": None, "tokens": []}


def _to_float(s: str) -> float | None:
    if not s:
        return None
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None
