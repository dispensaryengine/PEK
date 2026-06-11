# Database Schema

All tables have their columns **sorted alphabetically by label** (system columns
`id`, `created_at`, `updated_at` are anchored at top/bottom for clarity).

---

## Table: `brands`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK, auto-increment |
| `brand_slug` | TEXT | Unique slug for de-duplication |
| `created_at` | TIMESTAMP | Row creation time |
| `description` | TEXT | Brand bio / notes |
| `logo_url` | TEXT | Brand logo image URL |
| `name` | TEXT | Display name |
| `updated_at` | TIMESTAMP | Last updated |
| `website` | TEXT | Brand homepage |

---

## Table: `categories`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `created_at` | TIMESTAMP | |
| `description` | TEXT | Human-readable description |
| `display_order` | INTEGER | Sort order in UI (default 0) |
| `parent_slug` | TEXT | Parent category slug (for sub-cats) |
| `slug` | TEXT | Unique canonical slug (e.g. `flower`, `vape`) |
| `updated_at` | TIMESTAMP | |

---

## Table: `dispensaries`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `address` | TEXT | Street address |
| `city` | TEXT | |
| `created_at` | TIMESTAMP | |
| `latitude` | REAL | GPS lat |
| `longitude` | REAL | GPS lng |
| `menu_url` | TEXT | Dispensary menu URL |
| `name` | TEXT | Display name |
| `phone` | TEXT | Contact phone |
| `platform` | TEXT | `dutchie` / `carrot` / `blaze` / … |
| `state` | TEXT | 2-letter state code |
| `store_id` | TEXT | Platform-specific store ID |
| `updated_at` | TIMESTAMP | |
| `website` | TEXT | Dispensary homepage |
| `zip` | TEXT | ZIP / postal code |

---

## Table: `dpl` — Dispensary Price List

Per-dispensary snapshot of prices. Updated on every scrape run.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `brand` | TEXT | Brand name |
| `category` | TEXT | Normalised category slug |
| `created_at` | TIMESTAMP | |
| `dispensary_name` | TEXT | Dispensary display name |
| `in_stock` | BOOLEAN | Availability flag |
| `menu_url` | TEXT | Link to product on dispensary menu |
| `name` | TEXT | Product name |
| `pek_hash` | TEXT | FK → `mcp.pek_hash` |
| `platform` | TEXT | Scraping platform |
| `price` | REAL | Price in USD |
| `price_unit` | TEXT | e.g. `each`, `per_gram` |
| `product_id` | TEXT | Platform-native product ID |
| `quantity` | INTEGER | Quantity on hand |
| `scraped_at` | TIMESTAMP | When this price was captured |
| `sku` | TEXT | SKU / external ID |
| `updated_at` | TIMESTAMP | |
| `weight` | TEXT | e.g. `3.5g`, `100mg` |

**Unique constraint**: `(dispensary_name, product_id)`

---

## Table: `mcp` — Master Catalog Products

One canonical row per unique product across all dispensaries.
De-duplicated via `pek_hash` (SHA-1 of the Product Entity Key).

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `brand` | TEXT | Normalised brand name |
| `category` | TEXT | Normalised category slug |
| `cbd` | REAL | CBD % |
| `cbda` | REAL | CBDa % |
| `cbg` | REAL | CBG % |
| `cbn` | REAL | CBN % |
| `clean_name` | TEXT | Name with weight/strain tokens removed |
| `created_at` | TIMESTAMP | |
| `description` | TEXT | Product description |
| `image_url` | TEXT | Primary product image |
| `name` | TEXT | Raw product name |
| `pek` | TEXT | Human-readable Product Entity Key |
| `pek_hash` | TEXT | SHA-1(12) of PEK — unique row key |
| `strain` | TEXT | Strain name |
| `strain_type` | TEXT | `SATIVA` / `INDICA` / `HYBRID` / `CBD` |
| `subcategory` | TEXT | Sub-category |
| `terpenes` | TEXT | Terpene profile (JSON or plain text) |
| `thc` | REAL | THC % |
| `thca` | REAL | THCa % |
| `updated_at` | TIMESTAMP | |
| `weight` | TEXT | Canonical weight string (e.g. `3.5g`) |
| `weight_unit` | TEXT | `g` / `mg` / `oz` / `ml` |
| `weight_value` | REAL | Numeric weight value |

---

## Table: `price_history`

Append-only ledger — one row per (dispensary × product × scrape run).
Used for price trend analysis.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `created_at` | TIMESTAMP | |
| `dispensary_name` | TEXT | |
| `in_stock` | BOOLEAN | |
| `pek_hash` | TEXT | FK → `mcp.pek_hash` |
| `price` | REAL | Price in USD at time of scrape |
| `product_name` | TEXT | Name at time of scrape (snapshot) |
| `recorded_at` | TIMESTAMP | Scrape timestamp |
| `weight` | TEXT | Weight at time of scrape |

---

## Table: `products`

Raw scraped rows — one row per (dispensary, platform product ID). Upserted on every scrape.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `brand` | TEXT | |
| `category` | TEXT | Raw category as returned by platform |
| `cbd` | REAL | |
| `cbda` | REAL | |
| `cbg` | REAL | |
| `cbn` | REAL | |
| `created_at` | TIMESTAMP | |
| `description` | TEXT | |
| `dispensary_id` | INTEGER | FK → `dispensaries.id` |
| `dispensary_name` | TEXT | |
| `image_url` | TEXT | |
| `in_stock` | BOOLEAN | |
| `menu_url` | TEXT | |
| `name` | TEXT | |
| `pek_hash` | TEXT | FK → `mcp.pek_hash` |
| `platform` | TEXT | |
| `price` | REAL | |
| `price_unit` | TEXT | |
| `product_id` | TEXT | Platform-native product ID |
| `quantity` | INTEGER | |
| `scraped_at` | TIMESTAMP | |
| `sku` | TEXT | |
| `strain` | TEXT | |
| `strain_type` | TEXT | |
| `subcategory` | TEXT | |
| `terpenes` | TEXT | |
| `thc` | REAL | |
| `thca` | REAL | |
| `updated_at` | TIMESTAMP | |
| `weight` | TEXT | |
| `weight_unit` | TEXT | |
| `weight_value` | REAL | |

**Unique constraint**: `(dispensary_name, product_id)`

---

## Table: `scrape_runs`

Audit log of every scrape attempt.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `completed_at` | TIMESTAMP | When run finished |
| `dispensary_name` | TEXT | |
| `error_message` | TEXT | Error text if status = `error` |
| `platform` | TEXT | |
| `product_count` | INTEGER | Products scraped this run |
| `started_at` | TIMESTAMP | |
| `status` | TEXT | `pending` / `running` / `ok` / `error` |
| `updated_at` | TIMESTAMP | |

---

## Table: `strains`

Canonical strain library for enrichment / search.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER / SERIAL | PK |
| `cbd_pct` | REAL | Typical CBD % |
| `created_at` | TIMESTAMP | |
| `description` | TEXT | |
| `name` | TEXT | Display name |
| `slug` | TEXT | Unique slug |
| `strain_type` | TEXT | `SATIVA` / `INDICA` / `HYBRID` |
| `thc_pct` | REAL | Typical THC % |
| `updated_at` | TIMESTAMP | |

---

## Entity Relationship Summary

```
dispensaries ──< products >── mcp
                products >── brands
                products >── categories
                products >── strains
mcp ──< dpl
mcp ──< price_history
scrape_runs (audit, no FK)
```

## Product Entity Key (PEK)

Format (pipe-delimited):

```
<category_slug>|<brand_slug>|<name_slug>|<weight_slug>
```

Example:
```
flower|deadhead-farms|og-kush|3-5g
```

`pek_hash` = `SHA1(pek)[:12]` — used as the stable cross-dispensary deduplication key.
