# JDAS Digital Clone — Microsoft Dataverse Schema
# =================================================
# This file defines all tables, columns, and relationships
# needed to wire the 18 engine blocks into Dataverse.
#
# HOW TO USE:
#   1. Open Power Apps → Dataverse → Tables
#   2. Create each table below using the column definitions
#   3. Set relationships as defined in RELATIONSHIPS section
#   4. Use Power Automate to sync data from Excel uploads → Dataverse
#   5. The FastAPI /update-inputs endpoint writes here via the Dataverse Web API
#
# NAMING CONVENTION:
#   All custom tables prefixed: jdas_
#   All custom columns prefixed: jdas_
#   Follows Dataverse naming rules (no spaces, lowercase, underscores)

TABLES = {

    # ── CORE: Business Snapshot (one row per week) ────────────────────────────
    "jdas_business_snapshot": {
        "display_name": "JDAS Business Snapshot",
        "description": "Weekly snapshot of all engine outputs. One row per week.",
        "primary_key": "jdas_snapshotid",
        "columns": {
            "jdas_snapshotid":          {"type": "uniqueidentifier", "required": True,  "description": "Auto-generated PK"},
            "jdas_week_start":          {"type": "datetime",         "required": True,  "description": "Week start date (Monday)"},
            "jdas_created_at":          {"type": "datetime",         "required": True,  "description": "Timestamp of record creation"},
            # Cash
            "jdas_cash_on_hand":        {"type": "money",            "required": True,  "description": "Cash in bank at snapshot"},
            "jdas_weekly_burn":         {"type": "money",            "required": True,  "description": "Weekly cash outflow"},
            "jdas_weekly_in":           {"type": "money",            "required": False, "description": "Weekly cash inflow"},
            "jdas_net_cash_12w":        {"type": "money",            "required": False, "description": "Projected net cash over 12 weeks"},
            "jdas_ending_cash_12w":     {"type": "money",            "required": False, "description": "Projected ending cash at week 12"},
            "jdas_survival_runway_mo":  {"type": "decimal",          "required": False, "description": "Months of cash runway"},
            "jdas_cash_status":         {"type": "nvarchar(50)",     "required": False, "description": "HEALTHY / LOW / CRITICAL / NEGATIVE CASH"},
            "jdas_tax_reserve_12w":     {"type": "money",            "required": False, "description": "Tax reserve to set aside"},
            # Workload
            "jdas_active_workload_hrs": {"type": "decimal",          "required": True,  "description": "Total hours on active projects"},
            "jdas_sustainable_cap_wk":  {"type": "decimal",          "required": False, "description": "Sustainable hours/week (owner + subs)"},
            "jdas_backlog_hrs":         {"type": "decimal",          "required": False, "description": "Hours of backlog beyond capacity"},
            "jdas_delay_days":          {"type": "integer",          "required": False, "description": "Current client wait time in days"},
            "jdas_capacity_stress":     {"type": "decimal",          "required": False, "description": "Capacity stress score 0-100"},
            "jdas_workload_status":     {"type": "nvarchar(50)",     "required": False, "description": "OK / TIGHT / OVERLOADED"},
            # Pipeline
            "jdas_leads_per_week":      {"type": "decimal",          "required": False, "description": "Total leads per week"},
            "jdas_qualified_per_week":  {"type": "decimal",          "required": False, "description": "Qualified leads per week"},
            "jdas_win_rate":            {"type": "decimal",          "required": False, "description": "Effective close rate 0-1"},
            "jdas_avg_project_value":   {"type": "money",            "required": False, "description": "Average project value ($)"},
            "jdas_revenue_12w":         {"type": "money",            "required": False, "description": "Projected invoiced revenue 12 weeks"},
            "jdas_cash_collected_12w":  {"type": "money",            "required": False, "description": "Cash expected to collect in 12 weeks"},
            # Quality
            "jdas_quality_score":       {"type": "decimal",          "required": False, "description": "Service quality score 0-100"},
            "jdas_quality_label":       {"type": "nvarchar(50)",     "required": False, "description": "Excellent / Good / Poor / Critical"},
            "jdas_rework_rate":         {"type": "decimal",          "required": False, "description": "Rework fraction 0-1"},
            "jdas_retention_likelihood":{"type": "decimal",          "required": False, "description": "Probability client returns 0-1"},
            "jdas_referral_likelihood": {"type": "decimal",          "required": False, "description": "Probability of referral 0-1"},
            "jdas_churn_risk":          {"type": "nvarchar(50)",     "required": False, "description": "Low / Medium / High"},
            "jdas_reaction_score":      {"type": "decimal",          "required": False, "description": "Customer reaction score 0-100"},
            # Recurring
            "jdas_mrr":                 {"type": "money",            "required": False, "description": "Current monthly recurring revenue"},
            "jdas_mrr_month12":         {"type": "money",            "required": False, "description": "Projected MRR at month 12"},
            "jdas_mrr_stability":       {"type": "decimal",          "required": False, "description": "MRR stability score 0-100"},
            "jdas_retainer_clients":    {"type": "integer",          "required": False, "description": "Number of active retainer clients"},
            "jdas_mrr_churn_flag":      {"type": "nvarchar(50)",     "required": False, "description": "STABLE / AT RISK / TOO VOLATILE"},
            # Labor
            "jdas_team_capacity_wk":    {"type": "decimal",          "required": False, "description": "Total team capacity hours/week"},
            "jdas_labor_cost_monthly":  {"type": "money",            "required": False, "description": "Total labor cost per month"},
            "jdas_gross_labor_margin":  {"type": "decimal",          "required": False, "description": "Labor gross margin 0-1"},
            "jdas_hire_trigger":        {"type": "nvarchar(50)",     "required": False, "description": "OK / HIRE TRIGGER"},
            # XP
            "jdas_xp_score":            {"type": "integer",          "required": False, "description": "Business score 0-100"},
            "jdas_xp_level":            {"type": "integer",          "required": False, "description": "Level 1-5"},
            "jdas_xp_title":            {"type": "nvarchar(100)",    "required": False, "description": "Level title string"},
        }
    },

    # ── INPUTS: Business Inputs (owner edits these) ───────────────────────────
    "jdas_business_inputs": {
        "display_name": "JDAS Business Inputs",
        "description": "Owner-editable business inputs. One active row per business. "
                       "Updated via the dashboard or POST /update-inputs.",
        "primary_key": "jdas_inputsid",
        "columns": {
            "jdas_inputsid":                    {"type": "uniqueidentifier", "required": True},
            "jdas_business_name":               {"type": "nvarchar(200)",    "required": True,  "description": "Client business name"},
            "jdas_owner_name":                  {"type": "nvarchar(200)",    "required": False, "description": "Owner name"},
            "jdas_industry":                    {"type": "nvarchar(100)",    "required": False, "description": "Industry / business type"},
            "jdas_effective_date":              {"type": "datetime",         "required": True,  "description": "Date these inputs became active"},
            "jdas_is_active":                   {"type": "boolean",          "required": True,  "description": "Is this the current active input set?"},
            # Owner time
            "jdas_owner_total_hrs_wk":          {"type": "decimal",          "required": True,  "description": "Owner total available hours/week"},
            "jdas_admin_hrs_wk":                {"type": "decimal",          "required": True,  "description": "Admin/non-billable hours/week"},
            "jdas_utilization_target":          {"type": "decimal",          "required": False, "description": "Target utilization 0-1 (default 0.85)"},
            # Workload
            "jdas_active_workload_hrs":         {"type": "decimal",          "required": True,  "description": "Current active project hours"},
            "jdas_num_active_projects":         {"type": "integer",          "required": False, "description": "Number of active projects"},
            # Team
            "jdas_num_subcontractors":          {"type": "integer",          "required": False, "description": "Active subcontractors"},
            "jdas_avg_sub_hrs_wk":              {"type": "decimal",          "required": False, "description": "Avg sub hours available/week"},
            "jdas_owner_billing_rate":          {"type": "money",            "required": True,  "description": "Owner hourly billing rate"},
            "jdas_owner_cost_rate":             {"type": "money",            "required": False, "description": "Owner hourly cost to business"},
            "jdas_avg_sub_billing_rate":        {"type": "money",            "required": False, "description": "Sub billing rate to client"},
            "jdas_avg_sub_cost_rate":           {"type": "money",            "required": False, "description": "Sub cost rate (pay to sub)"},
            # Pricing
            "jdas_base_hourly_rate":            {"type": "money",            "required": True,  "description": "Base project hourly rate"},
            "jdas_avg_hrs_per_project":         {"type": "decimal",          "required": False, "description": "Average project scope in hours"},
            "jdas_base_win_rate":               {"type": "decimal",          "required": False, "description": "Baseline win rate 0-1"},
            # Expenses
            "jdas_fixed_monthly_expenses":      {"type": "money",            "required": True,  "description": "Fixed monthly overhead"},
            "jdas_variable_monthly_expenses":   {"type": "money",            "required": False, "description": "Variable monthly costs"},
            "jdas_owner_draw_monthly":          {"type": "money",            "required": True,  "description": "Owner monthly draw"},
            "jdas_starting_cash":               {"type": "money",            "required": True,  "description": "Cash on hand at snapshot date"},
            "jdas_tax_reserve_rate":            {"type": "decimal",          "required": False, "description": "Tax reserve rate (default 0.25)"},
            # Leads
            "jdas_base_leads_per_week":         {"type": "decimal",          "required": False, "description": "Base inbound leads per week"},
            "jdas_marketing_multiplier":        {"type": "decimal",          "required": False, "description": "Marketing effort multiplier"},
            # Recurring
            "jdas_retainer_clients":            {"type": "integer",          "required": False, "description": "Current retainer client count"},
            "jdas_avg_retainer_value":          {"type": "money",            "required": False, "description": "Avg retainer $/month"},
            "jdas_monthly_churn_rate":          {"type": "decimal",          "required": False, "description": "Retainer monthly churn rate"},
            # Customer behavior
            "jdas_customer_sensitivity":        {"type": "nvarchar(20)",     "required": False, "description": "Low / Medium / High"},
            "jdas_communication_quality":       {"type": "decimal",          "required": False, "description": "Communication quality 0-1"},
            "jdas_process_discipline":          {"type": "decimal",          "required": False, "description": "Process discipline 0-1"},
        }
    },

    # ── PROJECTS: Active Projects (feeds Active Workload Engine) ──────────────
    "jdas_active_projects": {
        "display_name": "JDAS Active Projects",
        "description": "Individual active projects tracked in the workload engine. "
                       "Mirrors the Active_Projects sheet in JDAS_Active_Workload_Engine_v1.xlsx.",
        "primary_key": "jdas_projectid",
        "columns": {
            "jdas_projectid":           {"type": "uniqueidentifier", "required": True},
            "jdas_project_code":        {"type": "nvarchar(50)",     "required": True,  "description": "e.g. P-001"},
            "jdas_client_name":         {"type": "nvarchar(200)",    "required": True,  "description": "Client name"},
            "jdas_project_name":        {"type": "nvarchar(300)",    "required": False, "description": "Project description"},
            "jdas_status":              {"type": "nvarchar(50)",     "required": True,  "description": "Active / On Hold / Completed"},
            "jdas_hours_remaining":     {"type": "decimal",          "required": True,  "description": "Hours of work remaining"},
            "jdas_hours_original":      {"type": "decimal",          "required": False, "description": "Original scoped hours"},
            "jdas_start_date":          {"type": "datetime",         "required": False},
            "jdas_target_end_date":     {"type": "datetime",         "required": False},
            "jdas_billing_rate":        {"type": "money",            "required": False, "description": "Project-specific rate if different from default"},
            "jdas_is_retainer":         {"type": "boolean",          "required": False, "description": "Is this a retainer project?"},
        }
    },

    # ── WEEKLY LOG: For trend tracking ───────────────────────────────────────
    "jdas_weekly_log": {
        "display_name": "JDAS Weekly Log",
        "description": "Owner-entered weekly actuals. Used to calibrate predictions vs reality.",
        "primary_key": "jdas_logid",
        "columns": {
            "jdas_logid":               {"type": "uniqueidentifier", "required": True},
            "jdas_week_start":          {"type": "datetime",         "required": True},
            "jdas_actual_cash":         {"type": "money",            "required": False, "description": "Actual cash on hand this week"},
            "jdas_actual_leads":        {"type": "decimal",          "required": False, "description": "Actual leads received"},
            "jdas_actual_closes":       {"type": "integer",          "required": False, "description": "Jobs won this week"},
            "jdas_actual_hrs_worked":   {"type": "decimal",          "required": False, "description": "Hours actually worked"},
            "jdas_actual_invoiced":     {"type": "money",            "required": False, "description": "Amount invoiced this week"},
            "jdas_actual_collected":    {"type": "money",            "required": False, "description": "Cash actually collected"},
            "jdas_owner_notes":         {"type": "nvarchar(2000)",   "required": False, "description": "Free-form owner notes"},
        }
    },
}

# ─── RELATIONSHIPS ────────────────────────────────────────────────────────────

RELATIONSHIPS = [
    {
        "from_table": "jdas_business_snapshot",
        "from_column": "jdas_inputsid_ref",
        "to_table": "jdas_business_inputs",
        "to_column": "jdas_inputsid",
        "type": "many-to-one",
        "description": "Each snapshot links to the inputs that generated it",
    },
    {
        "from_table": "jdas_active_projects",
        "from_column": "jdas_inputsid_ref",
        "to_table": "jdas_business_inputs",
        "to_column": "jdas_inputsid",
        "type": "many-to-one",
        "description": "Projects belong to a business inputs configuration",
    },
    {
        "from_table": "jdas_weekly_log",
        "from_column": "jdas_snapshotid_ref",
        "to_table": "jdas_business_snapshot",
        "to_column": "jdas_snapshotid",
        "type": "many-to-one",
        "description": "Weekly log entries link to the snapshot for that week",
    },
]

# ─── DATAVERSE WEB API HELPERS (Python) ───────────────────────────────────────
# Paste your Dataverse environment URL and use MSAL for auth.
# See: https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/

DATAVERSE_CONFIG = {
    "environment_url": "https://YOUR_ORG.crm.dynamics.com",
    "api_version": "v9.2",
    "base_url": "https://YOUR_ORG.crm.dynamics.com/api/data/v9.2/",
    "auth": {
        "tenant_id": "YOUR_TENANT_ID",
        "client_id": "YOUR_APP_CLIENT_ID",
        "client_secret": "YOUR_APP_CLIENT_SECRET",  # Use Key Vault in production
        "scope": "https://YOUR_ORG.crm.dynamics.com/.default",
    }
}

DATAVERSE_ENDPOINTS = {
    "snapshot_list":    "jdas_business_snapshots",
    "inputs_list":      "jdas_business_inputses",
    "projects_list":    "jdas_active_projectses",
    "weekly_log_list":  "jdas_weekly_logs",
}
