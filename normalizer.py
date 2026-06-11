#!/usr/bin/env python3
"""
Product Entity Key (PEK) generation and Master Catalog Product (MCP) normalization.

PEK: deterministic slug used for cross-dispensary de-duplication.
     Format: <category_slug>|<brand_slug>|<name_slug>|<weight_slug>
MCP: canonical product record used for price comparison.

Usage:
    from normalization.normalizer import Normalizer
    norm = Normalizer(db_conn)
    norm.upsert_many(products)
"""

from __future__ import annotations
import re, hashlib, logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PEK helpers
# ─────────────────────────────────────────────────────────────────────────────

_STOP = {
    "the","a","an","and","or","of","with","for","by","from",
    "cannabis","dispensary","inc","llc","co","co.",
}

_CAT_ALIASES = {
    "flower": "flower", "bud": "flower", "nug": "flower", "nugs": "flower",
    "pre-roll": "preroll", "pre_roll": "preroll", "pre roll": "preroll",
    "prerolls": "preroll", "joints": "preroll", "joint": "preroll",
    "vaporizer": "vape", "cartridge": "vape", "cart": "vape", "carts": "vape",
    "vape": "vape", "pod": "vape",
    "edible": "edible", "edibles": "edible", "gummy": "edible",
    "gummies": "edible", "chocolate": "edible",
    "tincture": "tincture", "tinctures": "tincture",
    "concentrate": "concentrate", "concentrates": "concentrate",
    "wax": "concentrate", "shatter": "concentrate", "rosin": "concentrate",
    "live resin": "concentrate", "badder": "concentrate", "crumble": "concentrate",
    "capsule": "capsule", "capsules": "capsule", "pill": "capsule", "pills": "capsule",
    "topical": "topical", "topicals": "topical", "cream": "topical",
    "lotion": "topical", "balm": "topical", "patch": "topical",
    "beverage": "beverage", "beverages": "beverage", "drink": "beverage",
    "kief": "kief", "hash": "hash", "rso": "rso",
    "distillate": "distillate", "extract": "extract", "extracts": "extract",
    "pet": "pet", "pets": "pet",
    "accessory": "accessory", "accessories": "accessory", "gear": "accessory",
    "seeds": "seed", "seed": "seed", "clone": "clone", "clones": "clone",
}


def slugify(s: str) -> str:
    """Lower-case, replace non-alphanum with hyphens, collapse runs, strip."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")


def norm_category(raw: str) -> str:
    if not raw:
        return "other"
    k = raw.lower().strip()
    for alias, canon in _CAT_ALIASES.items():
        if k == alias or re.search(r"\b" + re.escape(alias) + r"\b", k):
            return canon
    return slugify(k) or "other"


def norm_brand(raw: str) -> str:
    if not raw:
        return ""
    words = re.split(r"[\s,\-|]+", raw.lower())
    words = [w for w in words if w and w not in _STOP]
    return "-".join(words) or slugify(raw)


def norm_name(raw: str, brand: str = "") -> str:
    if not raw:
        return ""
    s = raw.lower()
    if brand:
        # strip leading brand prefix
        brand_lo = brand.lower().strip()
        if s.startswith(brand_lo):
            s = s[len(brand_lo):].lstrip(" -|:")
    # remove weight tokens from name
    s = re.sub(r"[\d.]+\s*(?:g|gram|grams|mg|oz|ml|lb)\b", "", s, flags=re.I)
    words = re.split(r"[\s,\-|]+", s)
    words = [w for w in words if w and w not in _STOP]
    return "-".join(words[:6]) or slugify(raw)   # cap at 6 meaningful tokens


def norm_weight(val: Any, unit: str = "") -> str:
    """Return canonical weight string like '3.5g', '100mg', '1oz'."""
    if not val and not unit:
        return ""
    if isinstance(val, str) and not unit:
        m = re.match(r"([\d.]+)\s*([a-z]+)", val.strip(), re.I)
        if m:
            val, unit = m.group(1), m.group(2).lower()
    try:
        v = float(val)
    except (TypeError, ValueError):
        return slugify(str(val))
    unit = (unit or "").lower().strip()
    # normalize common units
    if unit in ("gram", "grams"):
        unit = "g"
    elif unit in ("ounce", "ounces"):
        unit = "oz"
    elif unit in ("milligram", "milligrams"):
        unit = "mg"
    # prettify: drop trailing zeros
    v_str = f"{v:g}"
    return f"{v_str}{unit}" if unit else v_str


def make_pek(category: str, brand: str, name: str,
             weight_val: Any = None, weight_unit: str = "") -> str:
    """
    Build a deterministic Product Entity Key.

    Returns a pipe-delimited string:
        <cat>|<brand>|<name>|<weight>
    where each component is slugified / normalised.
    """
    cat    = norm_category(category or "")
    br     = norm_brand(brand or "")
    nm     = norm_name(name or "", brand or "")
    wt     = norm_weight(weight_val, weight_unit)

    raw    = f"{cat}|{br}|{nm}|{wt}"
    return raw


def make_pek_hash(pek: str) -> str:
    """SHA-1 (12 hex chars) of the PEK string for use as a stable short ID."""
    return hashlib.sha1(pek.encode()).hexdigest()[:12]


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer class
# ─────────────────────────────────────────────────────────────────────────────

class Normalizer:
    """
    Normalizes raw scraped products into MCP rows and upserts them
    into the database.

    Expected DB tables (see SCHEMA.md):
        mcp       — master catalog products
        dpl       — dispensary price list (per-dispensary snapshot)
        products  — raw product rows (populated by scrapers)
    """

    def __init__(self, conn=None):
        self.conn = conn

    # ── Public API ────────────────────────────────────────────────────────────

    def normalize(self, raw: dict) -> dict:
        """Return a normalized MCP-shaped dict for a single raw product."""
        from normalization.title_parser import parse_title

        title      = raw.get("name") or raw.get("product_name") or ""
        brand_raw  = raw.get("brand") or raw.get("brand_name") or ""
        cat_raw    = raw.get("category") or raw.get("product_type") or raw.get("type") or ""
        subcat     = raw.get("subcategory") or raw.get("sub_type") or ""
        strain     = raw.get("strain") or raw.get("strain_name") or ""
        strain_type= raw.get("strain_type") or raw.get("flower_type") or ""

        # price handling
        price_raw  = raw.get("price") or raw.get("unit_price") or 0
        try:
            price  = float(str(price_raw).replace("$","").strip()) if price_raw else None
        except ValueError:
            price  = None

        # weight handling
        weight_val  = raw.get("weight_value") or raw.get("weight")
        weight_unit = raw.get("weight_unit") or ""
        if isinstance(weight_val, str):
            m = re.match(r"([\d.]+)\s*([a-z]*)", weight_val.strip(), re.I)
            if m:
                weight_val  = m.group(1)
                weight_unit = weight_unit or m.group(2).lower()

        # parse title for enrichment when direct fields are sparse
        parsed = parse_title(title, brand=brand_raw or None, category=cat_raw or None)
        if not weight_val and parsed.get("weight_value"):
            weight_val  = parsed["weight_value"]
            weight_unit = parsed["weight_unit"] or weight_unit
        if not strain_type and parsed.get("strain_type"):
            strain_type = parsed["strain_type"]
        if not cat_raw and parsed.get("category_hint"):
            cat_raw = parsed["category_hint"]

        pek       = make_pek(cat_raw, brand_raw, title, weight_val, weight_unit)
        pek_hash  = make_pek_hash(pek)
        now       = datetime.now(timezone.utc).isoformat()

        return {
            # identifiers
            "pek":              pek,
            "pek_hash":         pek_hash,
            # product fields
            "name":             title,
            "clean_name":       parsed.get("clean_name") or title,
            "brand":            brand_raw or None,
            "category":         norm_category(cat_raw),
            "subcategory":      subcat or None,
            "strain":           strain or None,
            "strain_type":      (strain_type or "").upper() or None,
            "weight":           norm_weight(weight_val, weight_unit) or None,
            "weight_value":     _safe_float(weight_val),
            "weight_unit":      weight_unit or None,
            # potency
            "thc":              _safe_float(raw.get("thc")),
            "thca":             _safe_float(raw.get("thca")),
            "cbd":              _safe_float(raw.get("cbd")),
            "cbda":             _safe_float(raw.get("cbda")),
            "cbg":              _safe_float(raw.get("cbg")),
            "cbn":              _safe_float(raw.get("cbn")),
            "terpenes":         raw.get("terpenes") or None,
            # price / availability
            "price":            price,
            "price_unit":       raw.get("price_unit") or None,
            "in_stock":         bool(raw.get("in_stock", True)),
            "quantity":         _safe_int(raw.get("quantity")),
            # source
            "dispensary_name":  raw.get("dispensary_name") or "",
            "platform":         raw.get("platform") or "",
            "product_id":       str(raw.get("product_id") or raw.get("id") or ""),
            "sku":              str(raw.get("sku") or ""),
            "image_url":        raw.get("image_url") or raw.get("image") or None,
            "menu_url":         raw.get("menu_url") or raw.get("detail_url") or None,
            "description":      raw.get("description") or None,
            # timestamps
            "scraped_at":       raw.get("scraped_at") or now,
            "updated_at":       now,
        }

    def upsert_many(self, products: list[dict], table: str = "products") -> int:
        """Normalize + upsert a list of raw products. Returns count upserted."""
        if not self.conn:
            log.warning("No DB connection; skipping upsert")
            return 0
        normalized = [self.normalize(p) for p in products]
        count = 0
        cur = self.conn.cursor()
        for prod in normalized:
            try:
                self._upsert_one(cur, prod, table)
                count += 1
            except Exception as e:
                log.warning("Upsert failed for %s: %s", prod.get("pek"), e)
        self.conn.commit()
        log.info("Upserted %d/%d products into %s", count, len(products), table)
        return count

    def upsert_mcp(self, products: list[dict]) -> int:
        """Upsert into the mcp (master catalog) table — strips dispensary-specific fields."""
        if not self.conn:
            return 0
        normalized = [self.normalize(p) for p in products]
        _MCP_COLS = [
            "pek","pek_hash","name","clean_name","brand","category","subcategory",
            "strain","strain_type","weight","weight_value","weight_unit",
            "thc","thca","cbd","cbda","cbg","cbn","terpenes",
            "image_url","description","updated_at",
        ]
        count = 0
        cur = self.conn.cursor()
        for prod in normalized:
            row = {k: prod[k] for k in _MCP_COLS if k in prod}
            try:
                self._upsert_row(cur, "mcp", row, conflict_key="pek_hash")
                count += 1
            except Exception as e:
                log.warning("MCP upsert failed for %s: %s", prod.get("pek"), e)
        self.conn.commit()
        return count

    def upsert_dpl(self, products: list[dict]) -> int:
        """Upsert into the dpl (dispensary price list) table."""
        if not self.conn:
            return 0
        normalized = [self.normalize(p) for p in products]
        _DPL_COLS = [
            "pek_hash","dispensary_name","platform","product_id","sku",
            "name","brand","category","weight","price","price_unit",
            "in_stock","quantity","menu_url","scraped_at","updated_at",
        ]
        count = 0
        cur = self.conn.cursor()
        for prod in normalized:
            row = {k: prod[k] for k in _DPL_COLS if k in prod}
            try:
                conflict = "(pek_hash, dispensary_name)"
                self._upsert_row(cur, "dpl", row, conflict_key=conflict)
                count += 1
            except Exception as e:
                log.warning("DPL upsert failed for %s: %s", prod.get("pek"), e)
        self.conn.commit()
        return count

    # ── Private helpers ───────────────────────────────────────────────────────

    def _upsert_one(self, cur, prod: dict, table: str):
        self._upsert_row(cur, table, prod, conflict_key="(dispensary_name, product_id)")

    def _upsert_row(self, cur, table: str, row: dict, conflict_key: str = "pek_hash"):
        cols   = list(row.keys())
        vals   = list(row.values())
        ph     = ", ".join(["?"] * len(cols))
        col_s  = ", ".join(cols)
        update_s = ", ".join(f"{c}=excluded.{c}" for c in cols)
        sql = (
            f"INSERT INTO {table} ({col_s}) VALUES ({ph}) "
            f"ON CONFLICT ({conflict_key}) DO UPDATE SET {update_s}"
        )
        cur.execute(sql, vals)


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace("%","").strip())
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None
