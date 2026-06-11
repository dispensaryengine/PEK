#!/usr/bin/env python3
"""
Central dispensary configuration — all 52 stores across 8 platforms.
Loaded from the CSV at runtime; hard-coded fallbacks for known IDs.
"""

from __future__ import annotations
import csv, os
from pathlib import Path
from typing import Optional

# ── Platform constants ────────────────────────────────────────────────────────
PLATFORM_DUTCHIE    = "dutchie"
PLATFORM_CARROT     = "carrot"
PLATFORM_DISPENSE   = "dispense"   # AIQ
PLATFORM_BLAZE      = "blaze"      # Tymber
PLATFORM_JANE       = "jane"       # iHeartJane / Algolia
PLATFORM_WEEDMAPS   = "weedmaps"
PLATFORM_PROTEUS420 = "proteus420"
PLATFORM_KUSHMART   = "kushmart"
PLATFORM_GOODLIFE   = "goodlife"

# ── Static config that the CSV doesn't carry ─────────────────────────────────

_DISPENSE_EXTRAS = {
    "82-J Cannabis":      {"venue_id": "390243df4f0ee7fa", "menu_url": "https://menus.dispenseapp.com/390243df4f0ee7fa/menu"},
    "Innocence Cannabis": {"venue_id": "0d177a4c05c521ca", "menu_url": "https://menus.dispenseapp.com/0d177a4c05c521ca/menu"},
    "Mrs. Green's":       {"venue_id": "74422ea119bfc60b", "menu_url": "https://menus.dispenseapp.com/74422ea119bfc60b/menu"},
}

_BLAZE_EXTRAS = {
    "Devil's Lettuce": {"store_id": "93903b1d-8fa9-4876-92d9-178e5a4b9080", "origin": "https://devilslettuce.net"},
    "Satisfied Mind":   {"store_id": "4fb40ea7-90ed-40b6-b70c-4a2543d9117c", "origin": "https://satisfiedmind.co"},
}

_JANE_EXTRAS = {
    "Buffalo Dreams": {"store_id": 5876, "store_url": "https://shopbuffalodreams.com/shop/",   "jane_url": "https://www.iheartjane.com/stores/5876/buffalo-dreams/menu"},
    "Stonedhouse":    {"store_id": 6928, "store_url": "https://stonedhouseny.com/order-online/menu/", "jane_url": "https://www.iheartjane.com/stores/6928"},
}

_WEEDMAPS_EXTRAS = {
    "Ether": {"slug": "ether", "wm_origin": "https://etherbuffalo.wm.store"},
}

_PROTEUS420_EXTRAS = {
    "The Cannabis Store": {"slug": "tcsbflo",     "base_url": "https://tcsbflo.com",          "products_ep": "/cart/cart/ajax_getproducts.cfm", "filters_ep": "/cart/cart/ajax_getfilters.cfm"},
    "HONEY Kenmore":      {"slug": "honeykenmore","base_url": "https://cart.honeykenmore.com", "products_ep": "/cart/ajax_getproducts.cfm",      "filters_ep": "/cart/ajax_getfilters.cfm"},
    "Toke Lane":          {"slug": "tokelane",    "base_url": "https://cart.tokelane.com",     "products_ep": "/cart/ajax_getproducts.cfm",      "filters_ep": "/cart/ajax_getfilters.cfm"},
}

_KUSHMART_EXTRAS = {
    "Kush Mart (Lackawanna)": {"shop_url": "https://kushmart.com/location/lackawanna-ny/shop"},
    "Kush Mart (Lancaster)":  {"shop_url": "https://kushmart.com/location/lancaster-ny/shop"},
}

_CARROT_API_URLS = {
    "Greenside Cannabis": "https://api.nevada.getcarrot.io/api/v1",
}

# ── Loader ────────────────────────────────────────────────────────────────────

def load_dispensaries(csv_path: Optional[str] = None) -> list[dict]:
    """Return list of fully-enriched dispensary dicts."""
    if csv_path is None:
        csv_path = os.environ.get(
            "DISPENSARY_CSV",
            str(Path(__file__).parent / "uploads" / "yay_-_sheet1.csv"),
        )

    stores: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            name     = row["Dispensary"].strip()
            platform = row["Platform"].strip().lower()
            store_id = row["Platform Store ID"].strip()
            website  = row["Website"].strip()
            menu_url = row["Menu URL"].strip()

            store: dict = {
                "name":      name,
                "platform":  platform,
                "store_id":  store_id,
                "website":   website,
                "menu_url":  menu_url,
                "address":   row.get("Address", "").strip(),
                "phone":     row.get("Phone", "").strip(),
            }

            # Merge platform-specific extras
            if platform == PLATFORM_DISPENSE:
                store.update(_DISPENSE_EXTRAS.get(name, {}))
            elif platform == PLATFORM_BLAZE:
                store.update(_BLAZE_EXTRAS.get(name, {}))
            elif platform == PLATFORM_JANE:
                store.update(_JANE_EXTRAS.get(name, {}))
            elif platform == PLATFORM_WEEDMAPS:
                store.update(_WEEDMAPS_EXTRAS.get(name, {}))
            elif platform == PLATFORM_PROTEUS420:
                store.update(_PROTEUS420_EXTRAS.get(name, {}))
            elif platform == "custom" and "kush" in name.lower():
                store["platform"] = PLATFORM_KUSHMART
                store.update(_KUSHMART_EXTRAS.get(name, {}))
            elif platform == "custom" and "good life" in name.lower():
                store["platform"] = PLATFORM_GOODLIFE
            elif platform == PLATFORM_CARROT:
                store["api_url"] = _CARROT_API_URLS.get(name)

            stores.append(store)

    return stores


def stores_by_platform(csv_path: Optional[str] = None) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for s in load_dispensaries(csv_path):
        result.setdefault(s["platform"], []).append(s)
    return result
