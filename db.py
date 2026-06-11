#!/usr/bin/env python3
"""
Database connection + schema initialisation.

• Local dev  : SQLite  (./data/scraper.db)
• Railway    : PostgreSQL  (DATABASE_URL env var, injected automatically)

All tables are sorted by column label (alphabetical within each group).
"""

from __future__ import annotations
import os, logging
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_connection():
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        log.info("Connected to PostgreSQL")
        return conn
    else:
        import sqlite3, pathlib
        pathlib.Path("data").mkdir(exist_ok=True)
        conn = sqlite3.connect("data/scraper.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        log.info("Connected to SQLite: data/scraper.db")
        return conn


def _is_pg(conn) -> bool:
    return "psycopg2" in type(conn).__module__


def init_schema(conn):
    """Create all tables if they do not exist. Columns sorted alphabetically."""
    pg = _is_pg(conn)
    auto = "SERIAL" if pg else "INTEGER"
    text = "TEXT"
    real = "REAL" if not pg else "DOUBLE PRECISION"
    bool_ = "BOOLEAN" if pg else "INTEGER"
    ts    = "TIMESTAMPTZ" if pg else "TEXT"

    ddl_statements = _build_ddl(auto, text, real, bool_, ts)
    cur = conn.cursor()
    for stmt in ddl_statements:
        cur.execute(stmt)
    conn.commit()
    log.info("Schema initialised (%d tables)", len(ddl_statements))


def _build_ddl(auto, text, real, bool_, ts) -> list[str]:
    """
    All tables; within each table columns are SORTED ALPHABETICALLY
    (system columns id / created_at / updated_at anchored at top/bottom).
    """
    return [

        # ── brands ────────────────────────────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS brands (
            id            {auto} PRIMARY KEY,
            brand_slug    {text} UNIQUE NOT NULL,
            created_at    {ts}   DEFAULT CURRENT_TIMESTAMP,
            description   {text},
            logo_url      {text},
            name          {text} NOT NULL,
            updated_at    {ts}   DEFAULT CURRENT_TIMESTAMP,
            website       {text}
        )""",

        # ── categories ───────────────────────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS categories (
            id            {auto} PRIMARY KEY,
            created_at    {ts}   DEFAULT CURRENT_TIMESTAMP,
            description   {text},
            display_order INTEGER DEFAULT 0,
            parent_slug   {text},
            slug          {text} UNIQUE NOT NULL,
            updated_at    {ts}   DEFAULT CURRENT_TIMESTAMP
        )""",

        # ── dispensaries ─────────────────────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS dispensaries (
            id            {auto} PRIMARY KEY,
            address       {text},
            city          {text},
            created_at    {ts}   DEFAULT CURRENT_TIMESTAMP,
            latitude      {real},
            longitude     {real},
            menu_url      {text},
            name          {text} NOT NULL,
            phone         {text},
            platform      {text},
            state         {text},
            store_id      {text},
            updated_at    {ts}   DEFAULT CURRENT_TIMESTAMP,
            website       {text},
            zip           {text}
        )""",

        # ── dpl (dispensary price list) ───────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS dpl (
            id              {auto} PRIMARY KEY,
            brand           {text},
            category        {text},
            created_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            dispensary_name {text} NOT NULL,
            in_stock        {bool_} DEFAULT 1,
            menu_url        {text},
            name            {text},
            pek_hash        {text},
            platform        {text},
            price           {real},
            price_unit      {text},
            product_id      {text},
            quantity        INTEGER,
            scraped_at      {ts},
            sku             {text},
            updated_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            weight          {text},
            UNIQUE (dispensary_name, product_id)
        )""",

        # ── mcp (master catalog products) ─────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS mcp (
            id              {auto} PRIMARY KEY,
            brand           {text},
            category        {text},
            cbd             {real},
            cbda            {real},
            cbg             {real},
            cbn             {real},
            clean_name      {text},
            created_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            description     {text},
            image_url       {text},
            name            {text},
            pek             {text},
            pek_hash        {text} UNIQUE NOT NULL,
            strain          {text},
            strain_type     {text},
            subcategory     {text},
            terpenes        {text},
            thc             {real},
            thca            {real},
            updated_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            weight          {text},
            weight_unit     {text},
            weight_value    {real}
        )""",

        # ── price_history ────────────────────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS price_history (
            id              {auto} PRIMARY KEY,
            created_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            dispensary_name {text} NOT NULL,
            in_stock        {bool_},
            pek_hash        {text} NOT NULL,
            price           {real},
            product_name    {text},
            recorded_at     {ts}   DEFAULT CURRENT_TIMESTAMP,
            weight          {text}
        )""",

        # ── products (raw scraped rows) ───────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS products (
            id              {auto} PRIMARY KEY,
            brand           {text},
            category        {text},
            cbd             {real},
            cbda            {real},
            cbg             {real},
            cbn             {real},
            created_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            description     {text},
            dispensary_id   INTEGER,
            dispensary_name {text},
            image_url       {text},
            in_stock        {bool_} DEFAULT 1,
            menu_url        {text},
            name            {text},
            pek_hash        {text},
            platform        {text},
            price           {real},
            price_unit      {text},
            product_id      {text},
            quantity        INTEGER,
            scraped_at      {ts},
            sku             {text},
            strain          {text},
            strain_type     {text},
            subcategory     {text},
            terpenes        {text},
            thc             {real},
            thca            {real},
            updated_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            weight          {text},
            weight_unit     {text},
            weight_value    {real},
            UNIQUE (dispensary_name, product_id)
        )""",

        # ── scrape_runs ──────────────────────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id              {auto} PRIMARY KEY,
            completed_at    {ts},
            dispensary_name {text},
            error_message   {text},
            platform        {text},
            product_count   INTEGER DEFAULT 0,
            started_at      {ts}   DEFAULT CURRENT_TIMESTAMP,
            status          {text} DEFAULT 'pending',
            updated_at      {ts}   DEFAULT CURRENT_TIMESTAMP
        )""",

        # ── strains ──────────────────────────────────────────────────────────
        f"""
        CREATE TABLE IF NOT EXISTS strains (
            id            {auto} PRIMARY KEY,
            cbd_pct       {real},
            created_at    {ts}   DEFAULT CURRENT_TIMESTAMP,
            description   {text},
            name          {text} NOT NULL,
            slug          {text} UNIQUE NOT NULL,
            strain_type   {text},
            thc_pct       {real},
            updated_at    {ts}   DEFAULT CURRENT_TIMESTAMP
        )""",

        # ── Indexes ───────────────────────────────────────────────────────────
        "CREATE INDEX IF NOT EXISTS idx_dpl_dispensary   ON dpl (dispensary_name)",
        "CREATE INDEX IF NOT EXISTS idx_dpl_pek_hash     ON dpl (pek_hash)",
        "CREATE INDEX IF NOT EXISTS idx_mcp_brand        ON mcp (brand)",
        "CREATE INDEX IF NOT EXISTS idx_mcp_category     ON mcp (category)",
        "CREATE INDEX IF NOT EXISTS idx_mcp_pek_hash     ON mcp (pek_hash)",
        "CREATE INDEX IF NOT EXISTS idx_price_hist_pek   ON price_history (pek_hash)",
        "CREATE INDEX IF NOT EXISTS idx_products_disp    ON products (dispensary_name)",
        "CREATE INDEX IF NOT EXISTS idx_products_pek     ON products (pek_hash)",
        "CREATE INDEX IF NOT EXISTS idx_scrape_runs_disp ON scrape_runs (dispensary_name)",
    ]
