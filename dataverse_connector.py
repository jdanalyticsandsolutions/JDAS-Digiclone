"""
JDAS Data Connector — PostgreSQL Backend
==========================================
Replaces the Dataverse connector with a PostgreSQL implementation.
All function signatures are identical so main.py requires zero changes.

Uses the DATABASE_URL environment variable set in Render (auto-injected
by the PostgreSQL environment group you linked).

Tables created automatically on first startup:
  jdas_business_inputs    — one active row per business (wizard inputs)
  jdas_business_snapshots — weekly engine output history
  jdas_active_projects    — individual project rows
"""

import os
import json
import logging
import datetime
from typing import Optional, Dict, Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "")

# The fixed business_id for JDAS own company record
JDAS_BUSINESS_ID = "jdas-001"


# ─── CONNECTION ───────────────────────────────────────────────────────────────

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL not configured. "
            "Make sure the PostgreSQL environment group is linked in Render."
        )
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn


# ─── SCHEMA BOOTSTRAP ─────────────────────────────────────────────────────────
# Called once at startup — creates tables if they don't exist yet.

def bootstrap_schema():
    """Create all required tables if they don't already exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS jdas_business_inputs (
        id                        SERIAL PRIMARY KEY,
        business_id               TEXT NOT NULL UNIQUE,
        base_leads_per_week       FLOAT,
        marketing_multiplier      FLOAT,
        active_workload_hrs       FLOAT,
        owner_total_hours_week    FLOAT,
        admin_hours_week          FLOAT,
        utilization_target        FLOAT,
        num_active_projects       INT,
        num_subcontractors        INT,
        owner_billing_rate        FLOAT,
        owner_cost_rate           FLOAT,
        owner_draw_monthly        FLOAT,
        base_hourly_rate          FLOAT,
        avg_hours_per_project     FLOAT,
        base_win_rate             FLOAT,
        fixed_monthly_expenses    FLOAT,
        variable_monthly_expenses FLOAT,
        starting_cash             FLOAT,
        tax_reserve_rate          FLOAT,
        current_retainer_clients  INT,
        avg_retainer_value_monthly FLOAT,
        current_month             INT,
        last_updated              TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS jdas_business_snapshots (
        id             SERIAL PRIMARY KEY,
        business_id    TEXT NOT NULL,
        week_of        DATE,
        xp_score       FLOAT,
        xp_title       TEXT,
        cash_health    TEXT,
        ending_cash    FLOAT,
        weekly_burn    FLOAT,
        backlog_hrs    FLOAT,
        stress_score   FLOAT,
        win_rate       FLOAT,
        revenue_12w    FLOAT,
        quality_score  FLOAT,
        mrr            FLOAT,
        generated_at   TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS jdas_active_projects (
        id             SERIAL PRIMARY KEY,
        business_id    TEXT NOT NULL,
        project_code   TEXT,
        client_name    TEXT,
        project_name   TEXT,
        hrs_remaining  FLOAT,
        billing_rate   FLOAT,
        status         TEXT,
        last_updated   TIMESTAMP DEFAULT NOW()
    );
    """
    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        conn.close()
        logger.info("✅ PostgreSQL schema bootstrapped.")
    except Exception as e:
        logger.error(f"Schema bootstrap error: {e}")
        raise


# ─── BUSINESS INPUTS — READ ───────────────────────────────────────────────────

INPUTS_FIELDS = [
    "base_leads_per_week", "marketing_multiplier", "active_workload_hrs",
    "owner_total_hours_week", "admin_hours_week", "utilization_target",
    "num_active_projects", "num_subcontractors", "owner_billing_rate",
    "owner_cost_rate", "owner_draw_monthly", "base_hourly_rate",
    "avg_hours_per_project", "base_win_rate", "fixed_monthly_expenses",
    "variable_monthly_expenses", "starting_cash", "tax_reserve_rate",
    "current_retainer_clients", "avg_retainer_value_monthly", "current_month",
]


def load_business_inputs(business_id: str = JDAS_BUSINESS_ID) -> Optional[Dict[str, Any]]:
    """
    Load saved inputs for a business from PostgreSQL.
    Returns a dict of field names → values, or None if no record exists yet.
    """
    try:
        conn = get_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM jdas_business_inputs WHERE business_id = %s LIMIT 1",
                    (business_id,)
                )
                row = cur.fetchone()
        conn.close()

        if not row:
            logger.info(f"No saved inputs found for business_id={business_id}")
            return None

        result = {"_record_id": row["id"]}
        for field in INPUTS_FIELDS:
            if field in row and row[field] is not None:
                result[field] = row[field]

        logger.info(f"Loaded inputs for {business_id}: {len(result)-1} fields")
        return result

    except Exception as e:
        logger.error(f"load_business_inputs error: {e}")
        raise RuntimeError(f"Failed to load inputs from PostgreSQL: {e}")


# ─── BUSINESS INPUTS — WRITE ──────────────────────────────────────────────────

def save_business_inputs(
    inputs_dict: Dict[str, Any],
    business_id: str = JDAS_BUSINESS_ID,
    record_id: Optional[str] = None,
) -> str:
    """
    Upsert business inputs to PostgreSQL.
    Uses INSERT ... ON CONFLICT DO UPDATE so it always works regardless of
    whether a row exists yet.
    Returns the business_id as the record identifier.
    """
    fields = [f for f in INPUTS_FIELDS if f in inputs_dict]
    if not fields:
        logger.warning("save_business_inputs called with no recognizable fields")
        return business_id

    set_clause = ", ".join(f"{f} = EXCLUDED.{f}" for f in fields)
    col_names  = ", ".join(["business_id"] + fields + ["last_updated"])
    placeholders = ", ".join(["%s"] * (len(fields) + 2))  # +2 for business_id and last_updated

    values = [business_id] + [inputs_dict[f] for f in fields] + [datetime.datetime.utcnow()]

    sql = f"""
        INSERT INTO jdas_business_inputs ({col_names})
        VALUES ({placeholders})
        ON CONFLICT (business_id) DO UPDATE SET
            {set_clause},
            last_updated = EXCLUDED.last_updated
    """

    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
        conn.close()
        logger.info(f"Saved inputs for {business_id}")
        return business_id
    except Exception as e:
        logger.error(f"save_business_inputs error: {e}")
        raise RuntimeError(f"Failed to save inputs to PostgreSQL: {e}")


# ─── PROJECTS — WRITE ─────────────────────────────────────────────────────────

def save_projects(
    projects: list,
    business_id: str = JDAS_BUSINESS_ID,
) -> int:
    """
    Replace all active projects for a business with the supplied list.
    Returns count of projects saved.
    """
    if not projects:
        return 0

    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                # Clear existing rows for this business
                cur.execute(
                    "DELETE FROM jdas_active_projects WHERE business_id = %s",
                    (business_id,)
                )
                # Insert fresh rows
                for p in projects:
                    cur.execute("""
                        INSERT INTO jdas_active_projects
                            (business_id, project_code, client_name, project_name,
                             hrs_remaining, billing_rate, status, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        business_id,
                        p.get("code", ""),
                        p.get("client", ""),
                        p.get("name", ""),
                        p.get("hrs_remaining", 0),
                        p.get("billing_rate", 0),
                        p.get("status", "Active"),
                        datetime.datetime.utcnow(),
                    ))
        conn.close()
        logger.info(f"Saved {len(projects)} projects for {business_id}")
        return len(projects)
    except Exception as e:
        logger.error(f"save_projects error: {e}")
        raise RuntimeError(f"Failed to save projects to PostgreSQL: {e}")


# ─── SNAPSHOT — WRITE ─────────────────────────────────────────────────────────

def save_snapshot(
    outputs: Dict[str, Any],
    business_id: str = JDAS_BUSINESS_ID,
) -> str:
    """
    Write a weekly engine output snapshot for historical tracking.
    Returns a string record identifier.
    """
    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO jdas_business_snapshots
                        (business_id, week_of, xp_score, xp_title, cash_health,
                         ending_cash, weekly_burn, backlog_hrs, stress_score,
                         win_rate, revenue_12w, quality_score, mrr, generated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    business_id,
                    datetime.date.today(),
                    outputs.get("xp_score", 0),
                    outputs.get("xp_title", ""),
                    outputs.get("exp_cash_health_status", ""),
                    outputs.get("exp_ending_cash", 0),
                    outputs.get("exp_weekly_burn", 0),
                    outputs.get("exp_backlog_hrs", 0),
                    outputs.get("exp_capacity_stress_score", 0),
                    outputs.get("exp_effective_win_rate", 0),
                    outputs.get("exp_total_invoiced_12w", 0),
                    outputs.get("exp_service_quality_score", 0),
                    outputs.get("exp_current_mrr", 0),
                    datetime.datetime.utcnow(),
                ))
        conn.close()
        logger.info(f"Saved snapshot for {business_id}")
        return business_id
    except Exception as e:
        logger.error(f"save_snapshot error: {e}")
        raise RuntimeError(f"Failed to save snapshot to PostgreSQL: {e}")


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

def dataverse_health_check() -> Dict[str, Any]:
    """
    Ping PostgreSQL to confirm connectivity.
    Returns a status dict safe to expose on the health endpoint.
    """
    try:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        conn.close()
        return {
            "connected": True,
            "backend":   "postgresql",
            "status":    "ok",
        }
    except Exception as e:
        return {
            "connected": False,
            "backend":   "postgresql",
            "error":     str(e),
        }
