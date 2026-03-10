"""
JDAS Digital Clone — FastAPI Application
=========================================
Public-facing API endpoints for the JDAS Business Intelligence engine.

Endpoints:
  GET  /                    Health check
  GET  /snapshot            Current business state (read-only)
  POST /predict             Run simulation with custom inputs
  POST /stress-test         Run multiple scenarios, return comparison
  GET  /dashboard           Full dashboard data package
  POST /update-inputs       Persist new business inputs (Dataverse)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

from engine import BusinessInputs, run_all, to_dict

# ─── APP SETUP ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="JDAS Digital Clone API",
    description="Business intelligence engine for JD Analytics & Solutions LLC. "
                "Powers the Digital Clone dashboard — snapshot, prediction, and stress-test endpoints.",
    version="1.0.0",
    contact={
        "name": "JD Analytics & Solutions LLC",
        "url": "https://www.jdanalyticsandsolutions.com",
        "email": "JasonDrunasky@jdanalyticsandsolutions.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Lock down to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── THE SQUEEZE — default live snapshot ─────────────────────────────────────
# In production this comes from Dataverse. Here it's the baseline stressed state.

LIVE_INPUTS = BusinessInputs(
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


# ─── PYDANTIC MODELS ──────────────────────────────────────────────────────────

class InputsPayload(BaseModel):
    """Owner-editable business inputs for prediction / stress-test calls."""
    base_leads_per_week: Optional[float] = Field(None, description="Base leads per week from outreach/networking")
    marketing_multiplier: Optional[float] = Field(None, ge=0.5, le=5.0)
    active_workload_hrs: Optional[float] = Field(None, ge=0, description="Current hours on active projects")
    owner_total_hours_week: Optional[float] = Field(None, ge=1, le=80)
    admin_hours_week: Optional[float] = Field(None, ge=0)
    num_subcontractors: Optional[int] = Field(None, ge=0, le=20)
    owner_billing_rate: Optional[float] = Field(None, ge=10)
    owner_draw_monthly: Optional[float] = Field(None, ge=0)
    base_hourly_rate: Optional[float] = Field(None, ge=10)
    avg_hours_per_project: Optional[float] = Field(None, ge=1)
    base_win_rate: Optional[float] = Field(None, ge=0.01, le=1.0)
    fixed_monthly_expenses: Optional[float] = Field(None, ge=0)
    variable_monthly_expenses: Optional[float] = Field(None, ge=0)
    starting_cash: Optional[float] = Field(None)
    current_retainer_clients: Optional[int] = Field(None, ge=0)
    avg_retainer_value_monthly: Optional[float] = Field(None, ge=0)
    current_month: Optional[int] = Field(None, ge=1, le=12)
    num_active_projects: Optional[int] = Field(None, ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "base_leads_per_week": 4.0,
                "num_subcontractors": 1,
                "owner_billing_rate": 110.0,
                "owner_draw_monthly": 2500.0,
                "current_retainer_clients": 2,
            }
        }


class ScenarioItem(BaseModel):
    label: str = Field(..., description="Human-readable scenario name")
    inputs: InputsPayload


class StressTestPayload(BaseModel):
    scenarios: List[ScenarioItem] = Field(..., min_items=1, max_items=10)

    class Config:
        json_schema_extra = {
            "example": {
                "scenarios": [
                    {"label": "Current", "inputs": {}},
                    {"label": "Hire 1 Sub", "inputs": {"num_subcontractors": 1}},
                    {"label": "Raise Rate + Sub", "inputs": {"num_subcontractors": 1, "base_hourly_rate": 115.0}},
                ]
            }
        }


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def merge_inputs(base: BusinessInputs, overrides: InputsPayload) -> BusinessInputs:
    """Apply only the fields present in the payload onto the base inputs."""
    import dataclasses
    base_dict = dataclasses.asdict(base)
    override_dict = {k: v for k, v in overrides.dict().items() if v is not None}
    base_dict.update(override_dict)
    return BusinessInputs(**base_dict)


def build_dashboard_package(inputs: BusinessInputs, outputs: dict, label: str = "live") -> dict:
    """Shape engine outputs into the dashboard-ready structure."""
    weekly_in = outputs["exp_cash_received_12w"] / 12
    weekly_out = outputs["exp_weekly_burn"]
    return {
        "meta": {
            "label": label,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "week_of": datetime.date.today().isoformat(),
        },
        "score": {
            "xp": outputs["xp_score"],
            "level": outputs["xp_level"],
            "title": outputs["xp_title"],
        },
        "status_banner": {
            "headline": outputs["status_headline"],
            "issues": outputs["status_issues"],
            "wins": outputs["status_wins"],
        },
        "cash": {
            "amount": inputs.starting_cash,
            "weekly_out": round(weekly_out, 2),
            "weekly_in": round(weekly_in, 2),
            "weeks_left": outputs["exp_survival_runway_months"] * 4.33,
            "net_12w": outputs["exp_net_cash_12w"],
            "ending_cash": outputs["exp_ending_cash"],
            "status": outputs["exp_cash_health_status"],
            "tax_reserve_12w": outputs["exp_tax_reserve_12w"],
        },
        "workload": {
            "active_hrs": outputs["exp_active_workload_hrs"],
            "sustainable_cap": outputs["exp_sustainable_capacity_wk"],
            "backlog_hrs": outputs["exp_backlog_hrs"],
            "wait_days": outputs["exp_delay_days"],
            "stress_score": outputs["exp_capacity_stress_score"],
            "status": outputs["exp_workload_status"],
            "hire_trigger": outputs["exp_hire_trigger_flag"],
        },
        "pipeline": {
            "leads_per_week": outputs["exp_total_leads_per_week"],
            "qualified_per_week": outputs["exp_qualified_leads_per_week"],
            "proposals_12w": outputs["exp_proposals_12w"],
            "closes_12w": outputs["exp_closed_12w_expected"],
            "win_rate": outputs["exp_effective_win_rate"],
            "avg_project_value": outputs["exp_avg_project_value"],
            "revenue_12w": outputs["exp_total_invoiced_12w"],
            "cash_collected_12w": outputs["exp_cash_received_12w"],
        },
        "quality": {
            "score": outputs["exp_service_quality_score"],
            "label": outputs["exp_quality_label"],
            "risk": outputs["exp_quality_risk"],
            "rework_rate": outputs["exp_rework_rate"],
            "retention_likelihood": outputs["exp_retention_likelihood"],
            "referral_likelihood": outputs["exp_referral_likelihood"],
            "churn_risk": outputs["exp_churn_risk"],
            "reaction_score": outputs["exp_reaction_score"],
        },
        "recurring": {
            "mrr": outputs["exp_current_mrr"],
            "mrr_month12": outputs["exp_mrr_month12"],
            "stability_score": outputs["exp_mrr_stability_score"],
            "retainer_clients": outputs["exp_retainer_clients"],
            "coverage_pct": outputs["exp_mrr_coverage_expenses"],
            "churn_flag": outputs["exp_churn_risk_flag"],
        },
        "labor": {
            "team_capacity_wk": outputs["exp_team_capacity_per_week"],
            "labor_cost_monthly": outputs["exp_labor_cost_monthly"],
            "gross_margin": outputs["exp_gross_labor_margin"],
            "sub_markup": outputs["exp_sub_markup_margin"],
            "num_subs": inputs.num_subcontractors,
        },
        "raw_exports": outputs,
    }


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "JDAS Digital Clone API",
        "company": "JD Analytics & Solutions LLC",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/snapshot", tags=["Dashboard"])
async def snapshot():
    """
    Returns the current live business state.
    In production, inputs are pulled from Dataverse.
    Read-only — reflects real business data, not a simulation.
    """
    try:
        outputs = run_all(LIVE_INPUTS)
        return build_dashboard_package(LIVE_INPUTS, to_dict(outputs), label="live")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict", tags=["Prediction"])
async def predict(payload: InputsPayload):
    """
    Run the full engine chain with custom inputs layered on top of live data.
    Used by the Predictive Playground — sliders post here, UI renders the delta.
    Returns both the predicted outputs AND the live baseline for diff display.
    """
    try:
        predicted_inputs = merge_inputs(LIVE_INPUTS, payload)
        live_outputs = run_all(LIVE_INPUTS)
        pred_outputs = run_all(predicted_inputs)
        live_pkg = build_dashboard_package(LIVE_INPUTS, to_dict(live_outputs), label="live")
        pred_pkg = build_dashboard_package(predicted_inputs, to_dict(pred_outputs), label="predicted")
        # Compute top-level deltas for the impact strip
        deltas = {
            "cash_net_12w":      round(pred_pkg["cash"]["net_12w"] - live_pkg["cash"]["net_12w"], 2),
            "revenue_12w":       round(pred_pkg["pipeline"]["revenue_12w"] - live_pkg["pipeline"]["revenue_12w"], 2),
            "backlog_hrs":       round(pred_pkg["workload"]["backlog_hrs"] - live_pkg["workload"]["backlog_hrs"], 2),
            "quality_score":     round(pred_pkg["quality"]["score"] - live_pkg["quality"]["score"], 2),
            "xp_score":          pred_pkg["score"]["xp"] - live_pkg["score"]["xp"],
            "win_rate":          round(pred_pkg["pipeline"]["win_rate"] - live_pkg["pipeline"]["win_rate"], 4),
            "mrr":               round(pred_pkg["recurring"]["mrr"] - live_pkg["recurring"]["mrr"], 2),
        }
        return {
            "live": live_pkg,
            "predicted": pred_pkg,
            "deltas": deltas,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stress-test", tags=["Prediction"])
async def stress_test(payload: StressTestPayload):
    """
    Run multiple named scenarios simultaneously and return a side-by-side comparison.
    Useful for comparing 'What if I hired AND raised my rate' vs each individually.
    Max 10 scenarios per call.
    """
    try:
        results = []
        for scenario in payload.scenarios:
            inputs = merge_inputs(LIVE_INPUTS, scenario.inputs)
            outputs = run_all(inputs)
            pkg = build_dashboard_package(inputs, to_dict(outputs), label=scenario.label)
            results.append({
                "label": scenario.label,
                "summary": {
                    "xp": pkg["score"]["xp"],
                    "title": pkg["score"]["title"],
                    "cash_net_12w": pkg["cash"]["net_12w"],
                    "ending_cash": pkg["cash"]["ending_cash"],
                    "cash_status": pkg["cash"]["status"],
                    "backlog_hrs": pkg["workload"]["backlog_hrs"],
                    "wait_days": pkg["workload"]["wait_days"],
                    "win_rate": pkg["pipeline"]["win_rate"],
                    "revenue_12w": pkg["pipeline"]["revenue_12w"],
                    "quality_score": pkg["quality"]["score"],
                    "mrr": pkg["recurring"]["mrr"],
                },
                "full": pkg,
            })
        return {
            "scenarios": results,
            "best_xp": max(results, key=lambda r: r["summary"]["xp"])["label"],
            "best_cash": max(results, key=lambda r: r["summary"]["ending_cash"])["label"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard", tags=["Dashboard"])
async def dashboard():
    """
    Full dashboard data package — includes live state, XP, badges eligibility,
    status banner, and all KPI cards. This is the primary endpoint for the React dashboard.
    """
    try:
        outputs = run_all(LIVE_INPUTS)
        pkg = build_dashboard_package(LIVE_INPUTS, to_dict(outputs), label="live")
        # Compute badge eligibility
        o = to_dict(outputs)
        weekly_in = o["exp_cash_received_12w"] / 12
        pkg["badges"] = {
            "cash_pos":   weekly_in > o["exp_weekly_burn"],
            "regular":    LIVE_INPUTS.current_retainer_clients >= 1,
            "helper":     LIVE_INPUTS.num_subcontractors >= 1,
            "happy":      o["exp_service_quality_score"] >= 80,
            "breathing":  o["exp_capacity_stress_score"] < 40,
            "pipeline":   o["exp_closed_12w_expected"] >= 12,
            "steady":     o["exp_current_mrr"] >= o["exp_weekly_burn"] * 4 * 0.5,
            "legend":     o["xp_score"] >= 90,
        }
        return pkg
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update-inputs", tags=["Data"])
async def update_inputs(payload: InputsPayload):
    """
    Accepts new business input values and persists them.
    In production: writes to Microsoft Dataverse via Power Automate or direct SDK.
    In development: returns the merged inputs + a fresh engine run.
    """
    try:
        updated = merge_inputs(LIVE_INPUTS, payload)
        outputs = run_all(updated)
        return {
            "status": "accepted",
            "message": "Inputs received. In production these write to Dataverse.",
            "applied_inputs": {
                k: v for k, v in updated.__dict__.items()
                if k in payload.dict() and payload.dict()[k] is not None
            },
            "snapshot": build_dashboard_package(updated, to_dict(outputs), label="updated"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
