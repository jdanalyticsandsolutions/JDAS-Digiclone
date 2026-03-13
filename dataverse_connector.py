"""
JDAS Dataverse Connector
=========================
Handles all reads and writes to Microsoft Dataverse for the Digital Clone system.

Tables used:
  jdas_business_inputs    — one active row per business (the wizard inputs)
  jdas_business_snapshot  — weekly engine output history
  jdas_active_projects    — individual project rows
  jdas_weekly_log         — owner-entered actuals for calibration

Environment variables required (set in Render dashboard):
  DATAVERSE_TENANT_ID     — Azure AD tenant ID
  DATAVERSE_CLIENT_ID     — App registration client ID
  DATAVERSE_CLIENT_SECRET — App registration client secret
  DATAVERSE_ORG_URL       — e.g. https://yourorg.crm.dynamics.com
"""

import os
import json
import logging
import datetime
from typing import Optional, Dict, Any

import requests
from msal import ConfidentialClientApplication

logger = logging.getLogger(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

TENANT_ID     = os.getenv("DATAVERSE_TENANT_ID", "")
CLIENT_ID     = os.getenv("DATAVERSE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DATAVERSE_CLIENT_SECRET", "")
ORG_URL       = os.getenv("DATAVERSE_ORG_URL", "").rstrip("/")

# Dataverse table logical names (plural, as used in the Web API)
TABLE_INPUTS    = "jdas_business_inputses"     # jdas_business_inputs
TABLE_SNAPSHOT  = "jdas_business_snapshots"    # jdas_business_snapshot
TABLE_PROJECTS  = "jdas_active_projectses"     # jdas_active_projects
TABLE_WEEKLY    = "jdas_weekly_logs"           # jdas_weekly_log

# The fixed business_id for JDAS own company record
# When you onboard client businesses, each gets their own UUID here
JDAS_BUSINESS_ID = "jdas-001"

# ─── AUTH ─────────────────────────────────────────────────────────────────────

_token_cache: Dict[str, Any] = {}

def get_access_token() -> str:
    """Get a valid OAuth2 token for Dataverse. Caches until 5 min before expiry."""
    now = datetime.datetime.utcnow().timestamp()
    if _token_cache.get("expires_at", 0) > now + 300:
        return _token_cache["access_token"]

    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, ORG_URL]):
        raise RuntimeError(
            "Dataverse credentials not configured. "
            "Set DATAVERSE_TENANT_ID, DATAVERSE_CLIENT_ID, "
            "DATAVERSE_CLIENT_SECRET, DATAVERSE_ORG_URL in Render."
        )

    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    scope     = [f"{ORG_URL}/.default"]

    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET,
    )
    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" not in result:
        error = result.get("error_description", result.get("error", "Unknown auth error"))
        raise RuntimeError(f"Dataverse auth failed: {error}")

    _token_cache["access_token"] = result["access_token"]
    _token_cache["expires_at"]   = now + result.get("expires_in", 3600)
    return _token_cache["access_token"]


def _headers() -> dict:
    return {
        "Authorization":    f"Bearer {get_access_token()}",
        "Content-Type":     "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version":    "4.0",
        "Accept":           "application/json",
        "Prefer":           "return=representation",
    }


def _api(path: str) -> str:
    return f"{ORG_URL}/api/data/v9.2/{path}"


def _raise_for_status(res: requests.Response, context: str):
    if not res.ok:
        try:
            detail = res.json().get("error", {}).get("message", res.text[:300])
        except Exception:
            detail = res.text[:300]
        raise RuntimeError(f"Dataverse {context} failed ({res.status_code}): {detail}")


# ─── FIELD MAPS ───────────────────────────────────────────────────────────────
# Maps Python BusinessInputs field names → Dataverse column logical names.
# Dataverse custom columns use the publisher prefix (jdas_).

INPUTS_FIELD_MAP = {
    "base_leads_per_week":        "jdas_base_leads_per_week",
    "marketing_multiplier":       "jdas_marketing_multiplier",
    "active_workload_hrs":        "jdas_active_workload_hrs",
    "owner_total_hours_week":     "jdas_owner_total_hours_week",
    "admin_hours_week":           "jdas_admin_hours_week",
    "utilization_target":         "jdas_utilization_target",
    "num_active_projects":        "jdas_num_active_projects",
    "num_subcontractors":         "jdas_num_subcontractors",
    "owner_billing_rate":         "jdas_owner_billing_rate",
    "owner_cost_rate":            "jdas_owner_cost_rate",
    "owner_draw_monthly":         "jdas_owner_draw_monthly",
    "base_hourly_rate":           "jdas_base_hourly_rate",
    "avg_hours_per_project":      "jdas_avg_hours_per_project",
    "base_win_rate":              "jdas_base_win_rate",
    "fixed_monthly_expenses":     "jdas_fixed_monthly_expenses",
    "variable_monthly_expenses":  "jdas_variable_monthly_expenses",
    "starting_cash":              "jdas_starting_cash",
    "tax_reserve_rate":           "jdas_tax_reserve_rate",
    "current_retainer_clients":   "jdas_current_retainer_clients",
    "avg_retainer_value_monthly": "jdas_avg_retainer_value_monthly",
    "current_month":              "jdas_current_month",
}

# Reverse map for reading back from Dataverse
INPUTS_FIELD_MAP_REVERSE = {v: k for k, v in INPUTS_FIELD_MAP.items()}


# ─── BUSINESS INPUTS — READ ───────────────────────────────────────────────────

def load_business_inputs(business_id: str = JDAS_BUSINESS_ID) -> Optional[Dict[str, Any]]:
    """
    Load the most recent saved inputs for a business from Dataverse.
    Returns a dict of Python field names → values, or None if no record exists yet.
    """
    try:
        select_cols = ",".join(INPUTS_FIELD_MAP.values())
        url = _api(
            f"{TABLE_INPUTS}"
            f"?$filter=jdas_business_id eq '{business_id}'"
            f"&$select=jdas_business_inputsid,{select_cols}"
            f"&$orderby=modifiedon desc"
            f"&$top=1"
        )
        res = requests.get(url, headers=_headers(), timeout=10)
        _raise_for_status(res, "load_business_inputs GET")

        rows = res.json().get("value", [])
        if not rows:
            logger.info(f"No saved inputs found for business_id={business_id}")
            return None

        row = rows[0]
        result = {"_record_id": row.get("jdas_business_inputsid")}
        for dv_col, py_field in INPUTS_FIELD_MAP_REVERSE.items():
            if dv_col in row:
                result[py_field] = row[dv_col]

        logger.info(f"Loaded inputs for {business_id}: {len(result)-1} fields")
        return result

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"load_business_inputs error: {e}")
        raise RuntimeError(f"Failed to load inputs from Dataverse: {e}")


# ─── BUSINESS INPUTS — WRITE ──────────────────────────────────────────────────

def save_business_inputs(
    inputs_dict: Dict[str, Any],
    business_id: str = JDAS_BUSINESS_ID,
    record_id: Optional[str] = None,
) -> str:
    """
    Upsert business inputs to Dataverse.
    If record_id is provided, PATCHes the existing row.
    If not, checks for an existing row first, then creates or patches.
    Returns the record ID (GUID) of the saved row.
    """
    # Build the Dataverse payload
    payload: Dict[str, Any] = {"jdas_business_id": business_id}
    for py_field, dv_col in INPUTS_FIELD_MAP.items():
        if py_field in inputs_dict:
            payload[dv_col] = inputs_dict[py_field]
    payload["jdas_last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"

    # Try to find existing record if no ID provided
    if not record_id:
        existing = load_business_inputs(business_id)
        if existing:
            record_id = existing.get("_record_id")

    if record_id:
        # PATCH existing row
        url = _api(f"{TABLE_INPUTS}({record_id})")
        res = requests.patch(url, headers=_headers(), json=payload, timeout=10)
        _raise_for_status(res, "save_business_inputs PATCH")
        logger.info(f"Updated inputs for {business_id}, record {record_id}")
        return record_id
    else:
        # POST new row
        url = _api(TABLE_INPUTS)
        res = requests.post(url, headers=_headers(), json=payload, timeout=10)
        _raise_for_status(res, "save_business_inputs POST")
        new_id = res.json().get("jdas_business_inputsid", "unknown")
        logger.info(f"Created new inputs record for {business_id}: {new_id}")
        return new_id


# ─── PROJECTS — WRITE ─────────────────────────────────────────────────────────

def save_projects(
    projects: list,
    business_id: str = JDAS_BUSINESS_ID,
) -> int:
    """
    Upsert the project list for a business.
    Deletes existing active projects for the business first, then inserts fresh rows.
    Returns count of projects saved.
    """
    if not projects:
        return 0

    # Delete existing active project rows for this business
    try:
        url = _api(f"{TABLE_PROJECTS}?$filter=jdas_business_id eq '{business_id}'&$select=jdas_active_projectsid")
        res = requests.get(url, headers=_headers(), timeout=10)
        _raise_for_status(res, "save_projects GET existing")
        existing_rows = res.json().get("value", [])
        for row in existing_rows:
            rid = row.get("jdas_active_projectsid")
            if rid:
                del_res = requests.delete(_api(f"{TABLE_PROJECTS}({rid})"), headers=_headers(), timeout=10)
                # 204 = success, 404 = already gone — both are fine
                if del_res.status_code not in (204, 404):
                    logger.warning(f"Could not delete project row {rid}: {del_res.status_code}")
    except Exception as e:
        logger.warning(f"Could not clean up old project rows: {e}")

    # Insert fresh rows
    saved = 0
    for p in projects:
        payload = {
            "jdas_business_id":    business_id,
            "jdas_project_code":   p.get("code", ""),
            "jdas_client_name":    p.get("client", ""),
            "jdas_project_name":   p.get("name", ""),
            "jdas_hrs_remaining":  p.get("hrs_remaining", 0),
            "jdas_billing_rate":   p.get("billing_rate", 0),
            "jdas_status":         p.get("status", "Active"),
            "jdas_last_updated":   datetime.datetime.utcnow().isoformat() + "Z",
        }
        try:
            res = requests.post(_api(TABLE_PROJECTS), headers=_headers(), json=payload, timeout=10)
            _raise_for_status(res, f"save_projects POST {p.get('code','?')}")
            saved += 1
        except Exception as e:
            logger.error(f"Failed to save project {p.get('code','?')}: {e}")

    logger.info(f"Saved {saved}/{len(projects)} projects for {business_id}")
    return saved


# ─── SNAPSHOT — WRITE ─────────────────────────────────────────────────────────

def save_snapshot(
    outputs: Dict[str, Any],
    business_id: str = JDAS_BUSINESS_ID,
) -> str:
    """
    Write a weekly engine output snapshot to Dataverse for historical tracking.
    Returns the new record ID.
    """
    payload = {
        "jdas_business_id":    business_id,
        "jdas_week_of":        datetime.date.today().isoformat(),
        "jdas_xp_score":       outputs.get("xp_score", 0),
        "jdas_xp_title":       outputs.get("xp_title", ""),
        "jdas_cash_health":    outputs.get("exp_cash_health_status", ""),
        "jdas_ending_cash":    outputs.get("exp_ending_cash", 0),
        "jdas_weekly_burn":    outputs.get("exp_weekly_burn", 0),
        "jdas_backlog_hrs":    outputs.get("exp_backlog_hrs", 0),
        "jdas_stress_score":   outputs.get("exp_capacity_stress_score", 0),
        "jdas_win_rate":       outputs.get("exp_effective_win_rate", 0),
        "jdas_revenue_12w":    outputs.get("exp_total_invoiced_12w", 0),
        "jdas_quality_score":  outputs.get("exp_service_quality_score", 0),
        "jdas_mrr":            outputs.get("exp_current_mrr", 0),
        "jdas_generated_at":   datetime.datetime.utcnow().isoformat() + "Z",
    }
    try:
        res = requests.post(_api(TABLE_SNAPSHOT), headers=_headers(), json=payload, timeout=10)
        _raise_for_status(res, "save_snapshot POST")
        new_id = res.json().get("jdas_business_snapshotid", "unknown")
        logger.info(f"Saved snapshot for {business_id}: {new_id}")
        return new_id
    except Exception as e:
        logger.error(f"save_snapshot error: {e}")
        raise RuntimeError(f"Failed to save snapshot: {e}")


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

def dataverse_health_check() -> Dict[str, Any]:
    """
    Ping Dataverse to confirm connectivity and credentials are working.
    Returns a status dict — safe to expose on the health endpoint.
    """
    try:
        token = get_access_token()
        url = _api(f"{TABLE_INPUTS}?$top=1&$select=jdas_business_id")
        res = requests.get(url, headers=_headers(), timeout=8)
        return {
            "connected":   res.ok,
            "status_code": res.status_code,
            "org_url":     ORG_URL,
            "table":       TABLE_INPUTS,
        }
    except Exception as e:
        return {
            "connected": False,
            "error":     str(e),
            "org_url":   ORG_URL,
        }
