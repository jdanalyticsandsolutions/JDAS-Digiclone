"""
JDAS Digital Clone — FastAPI Application
=========================================
Public-facing API endpoints for the JDAS Business Intelligence engine.

Storage: PostgreSQL (Render) — persists through spin-downs, accessible from any device.

Endpoints:
  GET  /                    Health check
  GET  /snapshot            Current business state (read-only)
  POST /predict             Run simulation with custom inputs
  POST /stress-test         Run multiple scenarios, return comparison
  GET  /dashboard           Full dashboard data package
  POST /update-inputs       Persist new business inputs to PostgreSQL
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import datetime
import os
import json

logger = logging.getLogger(__name__)

from engine import BusinessInputs, run_all, to_dict

# ─── APP SETUP ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="JDAS Digital Clone API",
    description="Business intelligence engine for JD Analytics & Solutions LLC. "
                "Powers the Digital Clone dashboard — snapshot, prediction, and stress-test endpoints.",
    version="2.0.0",
    contact={
        "name": "JD Analytics & Solutions LLC",
        "url": "https://www.jdanalyticsandsolutions.com",
        "email": "JasonDrunasky@jdanalyticsandsolutions.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── DATABASE SETUP ───────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://small_business_digital_clone_user:cbhs3isY9DoQdgoznCoVVKJBSwNH3WJF@dpg-d6qc2qnpm1nc73b06f10-a/small_business_digital_clone"
)

def get_db_connection():
    """Return a psycopg2 connection."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """
    Create tables on startup if they don't exist.
    - business_inputs: one row per business_id, stores wizard payload as JSON
    - dashboard_snapshots: history of dashboard outputs (optional, for future use)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS business_inputs (
                    business_id TEXT PRIMARY KEY,
                    inputs_json JSONB NOT NULL,
                    projects_json JSONB,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_snapshots (
                    id SERIAL PRIMARY KEY,
                    business_id TEXT NOT NULL,
                    snapshot_json JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
        conn.commit()
        logger.info("JDAS: Database tables ready.")
    except Exception as e:
        logger.error(f"JDAS: DB init failed: {e}")
        conn.rollback()
    finally:
        conn.close()


def load_inputs_from_db(business_id: str) -> Optional[dict]:
    """Load saved business inputs from PostgreSQL. Returns None if not found."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT inputs_json, projects_json FROM business_inputs WHERE business_id = %s",
                (business_id,)
            )
            row = cur.fetchone()
            if row:
                inputs = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                projects = row[1] if isinstance(row[1], dict) else (json.loads(row[1]) if row[1] else [])
                inputs["_projects"] = projects
                return inputs
            return None
    except Exception as e:
        logger.error(f"JDAS: DB load failed: {e}")
        return None
    finally:
        conn.close()


def save_inputs_to_db(business_id: str, inputs_dict: dict, projects: list):
    """Save business inputs to PostgreSQL. Upserts on business_id."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO business_inputs (business_id, inputs_json, projects_json, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (business_id)
                DO UPDATE SET
                    inputs_json = EXCLUDED.inputs_json,
                    projects_json = EXCLUDED.projects_json,
                    updated_at = NOW();
            """, (business_id, json.dumps(inputs_dict), json.dumps(projects)))
        conn.commit()
        logger.info(f"JDAS: Saved inputs for {business_id}")
    except Exception as e:
        logger.error(f"JDAS: DB save failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def save_snapshot_to_db(business_id: str, snapshot: dict):
    """Save a dashboard snapshot row for historical tracking."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dashboard_snapshots (business_id, snapshot_json)
                VALUES (%s, %s);
            """, (business_id, json.dumps(snapshot)))
        conn.commit()
    except Exception as e:
        logger.warning(f"JDAS: Snapshot save failed (non-fatal): {e}")
        conn.rollback()
    finally:
        conn.close()


# ─── BUSINESS ID ──────────────────────────────────────────────────────────────

JDAS_BUSINESS_ID = "jdas-001"

# ─── DEFAULT INPUTS ───────────────────────────────────────────────────────────

DEFAULT_INPUTS = BusinessInputs(
    base_leads_per_week=2.0,
    marketing_multiplier=1.0,
    active_workload_hrs=47.0,
    owner_total_hours_week=20.0,
    admin_hours_week=6.0,
    utilization_target=0.85,
    num_active_projects=4,
    num_subcontractors=0,
    owner_billing_rate=95.0,
    owner_cost_rate=45.0,
    owner_draw_monthly=3000.0,
    base_hourly_rate=95.0,
    avg_hours_per_project=15.0,
    base_win_rate=0.45,
    fixed_monthly_expenses=450.0,
    variable_monthly_expenses=100.0,
    starting_cash=2100.0,
    tax_reserve_rate=0.25,
    current_retainer_clients=0,
    avg_retainer_value_monthly=800.0,
    current_month=3,
)

# In-memory cache — replaced on each successful DB read/write
LIVE_INPUTS = DEFAULT_INPUTS


# ─── PYDANTIC MODELS ──────────────────────────────────────────────────────────

class InputsPayload(BaseModel):
    base_leads_per_week:        Optional[float] = Field(None, ge=0)
    marketing_multiplier:       Optional[float] = Field(None, ge=0, le=10.0)
    active_workload_hrs:        Optional[float] = Field(None, ge=0)
    owner_total_hours_week:     Optional[float] = Field(None, ge=0, le=168)
    admin_hours_week:           Optional[float] = Field(None, ge=0)
    num_subcontractors:         Optional[int]   = Field(None, ge=0, le=50)
    owner_billing_rate:         Optional[float] = Field(None, ge=0)
    owner_cost_rate:            Optional[float] = Field(None, ge=0)
    owner_draw_monthly:         Optional[float] = Field(None, ge=0)
    base_hourly_rate:           Optional[float] = Field(None, ge=0)
    avg_hours_per_project:      Optional[float] = Field(None, ge=0)
    base_win_rate:              Optional[float] = Field(None, ge=0, le=1.0)
    fixed_monthly_expenses:     Optional[float] = Field(None, ge=0)
    variable_monthly_expenses:  Optional[float] = Field(None, ge=0)
    starting_cash:              Optional[float] = Field(None)
    current_retainer_clients:   Optional[int]   = Field(None, ge=0)
    avg_retainer_value_monthly: Optional[float] = Field(None, ge=0)
    current_month:              Optional[int]   = Field(None, ge=1, le=12)
    num_active_projects:        Optional[int]   = Field(None, ge=0)
    projects:                   Optional[List[Dict[str, Any]]] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "base_leads_per_week": 4.0,
                "num_subcontractors": 1,
                "base_hourly_rate": 110.0,
                "owner_draw_monthly": 2500.0,
                "current_retainer_clients": 2,
            }
        }


class ScenarioItem(BaseModel):
    label:  str = Field(..., description="Human-readable scenario name")
    inputs: InputsPayload


class StressTestPayload(BaseModel):
    scenarios: List[ScenarioItem] = Field(..., min_length=1, max_length=10)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def merge_inputs(base: BusinessInputs, overrides: InputsPayload) -> BusinessInputs:
    import dataclasses
    base_dict     = dataclasses.asdict(base)
    engine_fields = set(base_dict.keys())
    override_dict = {
        k: v for k, v in overrides.dict().items()
        if k in overrides.__fields_set__ and k in engine_fields
    }
    base_dict.update(override_dict)
    return BusinessInputs(**base_dict)


def build_dashboard_package(inputs: BusinessInputs, outputs: dict, label: str = "live") -> dict:
    weekly_in  = outputs["exp_cash_received_12w"] / 12
    weekly_out = outputs["exp_weekly_burn"]
    return {
        "meta": {
            "label":        label,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "week_of":      datetime.date.today().isoformat(),
        },
        "score": {
            "xp":    outputs["xp_score"],
            "level": outputs["xp_level"],
            "title": outputs["xp_title"],
        },
        "status_banner": {
            "headline": outputs["status_headline"],
            "issues":   outputs["status_issues"],
            "wins":     outputs["status_wins"],
        },
        "cash": {
            "amount":          inputs.starting_cash,
            "weekly_out":      round(weekly_out, 2),
            "weekly_in":       round(weekly_in, 2),
            "weeks_left":      outputs["exp_survival_runway_months"] * 4.33,
            "net_12w":         outputs["exp_net_cash_12w"],
            "ending_cash":     outputs["exp_ending_cash"],
            "status":          outputs["exp_cash_health_status"],
            "tax_reserve_12w": outputs["exp_tax_reserve_12w"],
        },
        "workload": {
            "active_hrs":      outputs["exp_active_workload_hrs"],
            "sustainable_cap": outputs["exp_sustainable_capacity_wk"],
            "backlog_hrs":     outputs["exp_backlog_hrs"],
            "wait_days":       outputs["exp_delay_days"],
            "stress_score":    outputs["exp_capacity_stress_score"],
            "status":          outputs["exp_workload_status"],
            "hire_trigger":    outputs["exp_hire_trigger_flag"],
        },
        "pipeline": {
            "leads_per_week":     outputs["exp_total_leads_per_week"],
            "qualified_per_week": outputs["exp_qualified_leads_per_week"],
            "proposals_12w":      outputs["exp_proposals_12w"],
            "closes_12w":         outputs["exp_closed_12w_expected"],
            "win_rate":           outputs["exp_effective_win_rate"],
            "avg_project_value":  outputs["exp_avg_project_value"],
            "revenue_12w":        outputs["exp_total_invoiced_12w"],
            "cash_collected_12w": outputs["exp_cash_received_12w"],
        },
        "quality": {
            "score":                outputs["exp_service_quality_score"],
            "label":                outputs["exp_quality_label"],
            "risk":                 outputs["exp_quality_risk"],
            "rework_rate":          outputs["exp_rework_rate"],
            "retention_likelihood": outputs["exp_retention_likelihood"],
            "referral_likelihood":  outputs["exp_referral_likelihood"],
            "churn_risk":           outputs["exp_churn_risk"],
            "reaction_score":       outputs["exp_reaction_score"],
        },
        "recurring": {
            "mrr":              outputs["exp_current_mrr"],
            "mrr_month12":      outputs["exp_mrr_month12"],
            "stability_score":  outputs["exp_mrr_stability_score"],
            "retainer_clients": outputs["exp_retainer_clients"],
            "coverage_pct":     outputs["exp_mrr_coverage_expenses"],
            "churn_flag":       outputs["exp_churn_risk_flag"],
        },
        "labor": {
            "team_capacity_wk":   outputs["exp_team_capacity_per_week"],
            "labor_cost_monthly": outputs["exp_labor_cost_monthly"],
            "gross_margin":       outputs["exp_gross_labor_margin"],
            "sub_markup":         outputs["exp_sub_markup_margin"],
            "num_subs":           inputs.num_subcontractors,
        },
        "raw_exports": outputs,
    }


def badge_eligibility(inputs: BusinessInputs, o: dict) -> dict:
    weekly_in = o["exp_cash_received_12w"] / 12
    return {
        "cash_pos":  weekly_in >= o["exp_weekly_burn"],
        "regular":   inputs.current_retainer_clients >= 1,
        "helper":    inputs.num_subcontractors >= 1,
        "happy":     o["exp_service_quality_score"] >= 80,
        "breathing": o["exp_capacity_stress_score"] < 40,
        "pipeline":  o["exp_closed_12w_expected"] >= 12,
        "steady":    o["exp_current_mrr"] >= o["exp_weekly_burn"] * 4 * 0.5,
        "legend":    o["xp_score"] >= 90,
    }


# ─── LIVE INPUT LOADER ────────────────────────────────────────────────────────

def get_live_inputs() -> BusinessInputs:
    """
    Load current business inputs.
    Priority: PostgreSQL → in-memory cache → DEFAULT_INPUTS
    """
    import dataclasses
    try:
        saved = load_inputs_from_db(JDAS_BUSINESS_ID)
        if saved:
            saved.pop("_projects", None)
            base = dataclasses.asdict(DEFAULT_INPUTS)
            base.update({k: v for k, v in saved.items() if k in base and v is not None})
            return BusinessInputs(**base)
    except Exception as e:
        logger.warning(f"JDAS: DB read failed, using in-memory: {e}")
    return LIVE_INPUTS


# ─── STARTUP ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    try:
        init_db()
    except Exception as e:
        logger.error(f"JDAS: Startup DB init failed: {e}")


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    db_ok = False
    try:
        conn = get_db_connection()
        conn.close()
        db_ok = True
    except Exception:
        pass
    return {
        "service":  "JDAS Digital Clone API",
        "company":  "JD Analytics & Solutions LLC",
        "status":   "online",
        "version":  "2.0.0",
        "docs":     "/docs",
        "database": "connected" if db_ok else "disconnected",
        "storage":  "PostgreSQL (Render)",
    }


@app.get("/snapshot", tags=["Dashboard"])
async def snapshot():
    """Returns the current live business state from PostgreSQL."""
    try:
        inputs  = get_live_inputs()
        outputs = run_all(inputs)
        return build_dashboard_package(inputs, to_dict(outputs), label="live")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict", tags=["Prediction"])
async def predict(payload: InputsPayload):
    """
    Run the full engine chain with custom inputs layered on top of live data.
    Used by the Predictive Playground sliders.
    """
    try:
        live_inputs      = get_live_inputs()
        predicted_inputs = merge_inputs(live_inputs, payload)
        live_outputs     = run_all(live_inputs)
        pred_outputs     = run_all(predicted_inputs)
        live_pkg         = build_dashboard_package(live_inputs,      to_dict(live_outputs), label="live")
        pred_pkg         = build_dashboard_package(predicted_inputs, to_dict(pred_outputs), label="predicted")
        deltas = {
            "cash_net_12w":  round(pred_pkg["cash"]["net_12w"]         - live_pkg["cash"]["net_12w"],        2),
            "revenue_12w":   round(pred_pkg["pipeline"]["revenue_12w"] - live_pkg["pipeline"]["revenue_12w"],2),
            "backlog_hrs":   round(pred_pkg["workload"]["backlog_hrs"]  - live_pkg["workload"]["backlog_hrs"],2),
            "quality_score": round(pred_pkg["quality"]["score"]        - live_pkg["quality"]["score"],       2),
            "xp_score":            pred_pkg["score"]["xp"]             - live_pkg["score"]["xp"],
            "win_rate":      round(pred_pkg["pipeline"]["win_rate"]     - live_pkg["pipeline"]["win_rate"],   4),
            "mrr":           round(pred_pkg["recurring"]["mrr"]        - live_pkg["recurring"]["mrr"],       2),
        }
        return {"live": live_pkg, "predicted": pred_pkg, "deltas": deltas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stress-test", tags=["Prediction"])
async def stress_test(payload: StressTestPayload):
    """Run multiple named scenarios simultaneously and return a side-by-side comparison."""
    try:
        live_inputs = get_live_inputs()
        results = []
        for scenario in payload.scenarios:
            inputs  = merge_inputs(live_inputs, scenario.inputs)
            outputs = run_all(inputs)
            pkg     = build_dashboard_package(inputs, to_dict(outputs), label=scenario.label)
            results.append({
                "label": scenario.label,
                "summary": {
                    "xp":            pkg["score"]["xp"],
                    "title":         pkg["score"]["title"],
                    "cash_net_12w":  pkg["cash"]["net_12w"],
                    "ending_cash":   pkg["cash"]["ending_cash"],
                    "cash_status":   pkg["cash"]["status"],
                    "backlog_hrs":   pkg["workload"]["backlog_hrs"],
                    "wait_days":     pkg["workload"]["wait_days"],
                    "win_rate":      pkg["pipeline"]["win_rate"],
                    "revenue_12w":   pkg["pipeline"]["revenue_12w"],
                    "quality_score": pkg["quality"]["score"],
                    "mrr":           pkg["recurring"]["mrr"],
                },
                "full": pkg,
            })
        return {
            "scenarios": results,
            "best_xp":   max(results, key=lambda r: r["summary"]["xp"])["label"],
            "best_cash": max(results, key=lambda r: r["summary"]["ending_cash"])["label"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard", tags=["Dashboard"])
async def dashboard():
    """
    Full dashboard data package — live state from PostgreSQL, XP, badge eligibility,
    status banner, and all KPI cards.
    """
    try:
        inputs  = get_live_inputs()
        outputs = run_all(inputs)
        o       = to_dict(outputs)
        pkg     = build_dashboard_package(inputs, o, label="live")
        pkg["badges"] = badge_eligibility(inputs, o)
        return pkg
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update-inputs", tags=["Data"])
async def update_inputs(payload: InputsPayload):
    """
    Accepts new business input values from the weekly wizard.
    1. Merges onto current live inputs
    2. Writes to PostgreSQL (persistent across restarts, spin-downs, and devices)
    3. Updates in-memory cache
    4. Saves a snapshot row for historical tracking
    """
    global LIVE_INPUTS
    try:
        import dataclasses
        current = get_live_inputs()
        updated = merge_inputs(current, payload)

        # ── Save to PostgreSQL ──
        inputs_dict = dataclasses.asdict(updated)
        projects    = payload.projects or []
        save_inputs_to_db(JDAS_BUSINESS_ID, inputs_dict, projects)

        # ── Update in-memory cache ──
        LIVE_INPUTS = updated

        # ── Run engine and save snapshot ──
        outputs = run_all(updated)
        o       = to_dict(outputs)
        try:
            save_snapshot_to_db(JDAS_BUSINESS_ID, o)
        except Exception as snap_err:
            logger.warning(f"JDAS: Snapshot save failed (non-fatal): {snap_err}")

        pkg = build_dashboard_package(updated, o, label="updated")
        pkg["badges"] = badge_eligibility(updated, o)

        return {
            "status":   "saved",
            "message":  "Numbers saved to PostgreSQL. Dashboard is now live on all devices.",
            "snapshot": pkg,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
