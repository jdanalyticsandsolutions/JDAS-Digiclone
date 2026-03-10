"""
JDAS Digital Clone — Core Business Engine
==========================================
Translates all 18 Excel engine blocks into pure Python.
Each function mirrors the logic of its corresponding .xlsx file.
Inputs flow through the chain exactly as wired in the spreadsheets.

Chain order (dependency-safe):
  Inputs → Block0_Lead → Qualify → Pricing → Proposal → Close
        → Active_Workload → Block2_Capacity → Block3_Backlog
        → Block4_Customer → Block5_Quality → Block6_Retain
        → Block8_Labor → Deliver → Invoice → GetPaid
        → Block7_Expense → Block9_Recurring → Dashboard
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import math


# ─── INPUT SCHEMA ─────────────────────────────────────────────────────────────

@dataclass
class BusinessInputs:
    """All owner-editable inputs across the 18 engines.
    Default values = The Squeeze scenario (stressed state).
    """
    # ── Block 0: Lead Engine
    base_leads_per_week: float = 2.0
    marketing_multiplier: float = 1.0
    referral_conversion_factor: float = 1.0
    lead_seasonality_enabled: bool = True
    current_month: int = 3             # 1–12

    # ── Active Workload
    active_workload_hrs: float = 47.0  # Current hours on active projects
    owner_total_hours_week: float = 20.0
    admin_hours_week: float = 6.0
    utilization_target: float = 0.85
    num_active_projects: int = 4

    # ── Block 8: Labor & Subs
    num_subcontractors: int = 0
    avg_sub_hours_week: float = 20.0
    owner_billing_rate: float = 95.0   # $/hr
    owner_cost_rate: float = 45.0      # $/hr
    avg_sub_billing_rate: float = 75.0
    avg_sub_cost_rate: float = 50.0
    owner_draw_monthly: float = 3000.0

    # ── Pricing Engine
    base_hourly_rate: float = 95.0
    avg_hours_per_project: float = 15.0
    base_win_rate: float = 0.45
    min_project_floor: float = 500.0

    # ── Block 7: Expenses
    fixed_monthly_expenses: float = 450.0   # rent, software, insurance, phone
    variable_monthly_expenses: float = 100.0 # marketing, materials
    starting_cash: float = 5000.0
    tax_reserve_rate: float = 0.25

    # ── Block 9: Recurring Revenue
    current_retainer_clients: int = 0
    avg_retainer_value_monthly: float = 800.0
    retainer_hours_per_month: float = 8.0
    new_retainer_conversions_per_month: float = 0.5
    monthly_churn_rate: float = 0.05
    target_retainer_clients: int = 5

    # ── Block 4: Customer Behavior
    customer_sensitivity: str = "Medium"  # Low / Medium / High
    communication_quality: float = 0.8
    relationship_strength: float = 0.7
    target_promise_days: int = 7

    # ── Block 5: Service Quality
    base_quality_score: float = 90.0
    delay_tolerance_days: int = 3
    max_delay_penalty: float = 25.0
    reaction_weight: float = 0.35
    process_discipline: float = 0.75
    base_rework_rate: float = 0.05
    rework_sensitivity: float = 0.25

    # ── Block 6: Retain/Refer
    avg_repeat_work_hrs: float = 8.0
    referral_conversion_rate: float = 0.35
    avg_new_project_hrs_referral: float = 10.0

    # ── Spine: Close
    delay_penalty_sensitivity: float = 0.01
    delay_threshold_days: int = 2
    quality_bonus_sensitivity: float = 0.003
    avg_delivery_hrs_per_project: float = 12.0

    # ── GetPaid
    starting_ar_balance: float = 1800.0
    collection_lag_same_week: float = 0.05
    collection_lag_1wk: float = 0.55
    collection_lag_2wk: float = 0.30
    collection_lag_3wk: float = 0.10
    pct_collected_eventually: float = 0.98

    # ── Simulation
    horizon_weeks: int = 12


# ─── OUTPUT SCHEMA ────────────────────────────────────────────────────────────

@dataclass
class EngineOutputs:
    """All export fields, matching the Exports sheets 1:1."""

    # Block 0 — Leads
    exp_total_leads_per_week: float = 0.0
    exp_total_leads_12w: float = 0.0
    exp_leads_week1: float = 0.0
    exp_leads_week2: float = 0.0
    exp_leads_week3: float = 0.0

    # Active Workload
    exp_active_workload_hrs: float = 0.0
    exp_available_delivery_hrs_wk: float = 0.0
    exp_sustainable_capacity_wk: float = 0.0
    exp_capacity_balance: float = 0.0
    exp_workload_status: str = "OK"

    # Block 2 — Capacity Comparison
    exp_capacity_stress_score: float = 0.0
    exp_capacity_status: str = "OK"

    # Block 3 — Backlog / Delay
    exp_backlog_hrs: float = 0.0
    exp_delay_days: int = 0
    exp_delay_status: str = "OK"
    exp_promise_days: int = 0

    # Block 4 — Customer Reaction
    exp_reaction_score: float = 0.0
    exp_reaction_label: str = "Happy"
    exp_churn_risk: str = "Low"
    exp_suggested_action: str = "Standard update cadence"

    # Block 5 — Service Quality
    exp_service_quality_score: float = 0.0
    exp_quality_label: str = "Good"
    exp_quality_risk: str = "Low"
    exp_rework_rate: float = 0.0
    exp_delivery_hrs_multiplier: float = 1.0
    exp_referral_likelihood: float = 0.0
    exp_retention_likelihood: float = 0.0

    # Block 6 — Retain / Refer
    exp_retained_projects: float = 0.0
    exp_converted_referral_projects: float = 0.0
    exp_future_work_hours: float = 0.0
    exp_new_work_hours_per_week: float = 0.0

    # Block 7 — Expense & Tax
    exp_monthly_expenses: float = 0.0
    exp_weekly_burn: float = 0.0
    exp_net_cash_12w: float = 0.0
    exp_ending_cash: float = 0.0
    exp_survival_runway_months: float = 0.0
    exp_tax_reserve_12w: float = 0.0
    exp_cash_health_status: str = "OK"
    exp_mrr_adjusted_runway: float = 0.0

    # Block 8 — Labor & Subs
    exp_team_capacity_per_week: float = 0.0
    exp_labor_cost_monthly: float = 0.0
    exp_gross_labor_margin: float = 0.0
    exp_capacity_gap_wk1: float = 0.0
    exp_hire_trigger_flag: str = "OK"
    exp_sub_markup_margin: float = 0.0

    # Block 9 — Recurring Revenue
    exp_current_mrr: float = 0.0
    exp_mrr_month12: float = 0.0
    exp_mrr_stability_score: float = 0.0
    exp_recurring_share: float = 0.0
    exp_churn_risk_flag: str = "STABLE"
    exp_mrr_coverage_expenses: float = 0.0
    exp_retainer_clients: int = 0

    # Spine: Pricing & Margin
    exp_effective_hourly_rate: float = 0.0
    exp_effective_win_rate_price: float = 0.0
    exp_project_gross_margin: float = 0.0
    exp_avg_project_value: float = 0.0
    exp_est_monthly_revenue: float = 0.0
    exp_margin_label: str = "OK"

    # Spine: Qualify
    exp_qual_rate_effective: float = 0.0
    exp_qualified_leads_per_week: float = 0.0
    exp_qualified_leads_12w: float = 0.0
    exp_qualified_week1: float = 0.0
    exp_qualified_week2: float = 0.0
    exp_qualified_week3: float = 0.0

    # Spine: Proposal
    exp_effective_proposal_rate: float = 0.0
    exp_proposals_week1: float = 0.0
    exp_proposals_week2: float = 0.0
    exp_proposals_week3: float = 0.0
    exp_proposals_12w: float = 0.0
    exp_proposal_hours_12w: float = 0.0
    exp_followup_rate: float = 0.0

    # Spine: Close
    exp_effective_win_rate: float = 0.0
    exp_closed_week1_expected: float = 0.0
    exp_closed_week2_expected: float = 0.0
    exp_closed_week3_expected: float = 0.0
    exp_closed_12w_expected: float = 0.0
    exp_new_work_hours_12w_expected: float = 0.0

    # Spine: Deliver
    exp_invoiceable_cap_per_week: float = 0.0
    exp_delivered_12w: float = 0.0
    exp_invoice_ready_12w: float = 0.0
    exp_labor_hours_spent_12w: float = 0.0
    exp_end_backlog_week12: float = 0.0
    exp_projects_completed_12w: float = 0.0

    # Spine: Invoice
    exp_total_invoiced_12w: float = 0.0
    exp_billable_hours_12w: float = 0.0
    exp_avg_invoice_per_week: float = 0.0
    exp_effective_rate: float = 0.0

    # Spine: GetPaid
    exp_cash_received_12w: float = 0.0
    exp_ending_ar_week12: float = 0.0
    exp_invoices_issued_12w: float = 0.0
    exp_collection_pct_12w: float = 0.0

    # Dashboard summary
    xp_score: int = 0
    xp_level: int = 1
    xp_title: str = "Tough Week"
    status_headline: str = ""
    status_issues: list = field(default_factory=list)
    status_wins: list = field(default_factory=list)


# ─── SEASONALITY TABLE ────────────────────────────────────────────────────────

SEASONALITY = {1:1.0, 2:1.0, 3:1.1, 4:1.1, 5:1.1, 6:1.0,
               7:0.9, 8:0.9, 9:1.0, 10:1.0, 11:0.9, 12:0.8}


# ─── ENGINE FUNCTIONS ─────────────────────────────────────────────────────────

def run_block0_leads(i: BusinessInputs, o: EngineOutputs):
    """Block 0 — Lead Engine"""
    seasonal = SEASONALITY.get(i.current_month, 1.0) if i.lead_seasonality_enabled else 1.0
    base = i.base_leads_per_week * i.marketing_multiplier * seasonal
    referral_boost = o.exp_converted_referral_projects * i.referral_conversion_factor / 4.0
    total = base + referral_boost
    o.exp_total_leads_per_week = round(total, 2)
    o.exp_total_leads_12w = round(total * i.horizon_weeks, 2)
    o.exp_leads_week1 = round(total * SEASONALITY.get(i.current_month, 1.0), 2)
    o.exp_leads_week2 = round(total, 2)
    o.exp_leads_week3 = round(total, 2)


def run_active_workload(i: BusinessInputs, o: EngineOutputs):
    """Active Workload Engine"""
    delivery_hrs = i.owner_total_hours_week - i.admin_hours_week
    sustainable = delivery_hrs * i.utilization_target
    balance = sustainable - i.active_workload_hrs
    if balance >= 0:
        status = "OK"
    elif balance >= -10:
        status = "TIGHT"
    else:
        status = "OVERLOADED"
    o.exp_active_workload_hrs = i.active_workload_hrs
    o.exp_available_delivery_hrs_wk = delivery_hrs
    o.exp_sustainable_capacity_wk = round(sustainable, 2)
    o.exp_capacity_balance = round(balance, 2)
    o.exp_workload_status = status


def run_block2_capacity(i: BusinessInputs, o: EngineOutputs):
    """Block 2 — Capacity Comparison"""
    delivery_hrs = i.owner_total_hours_week - i.admin_hours_week
    sustainable = delivery_hrs * i.utilization_target
    sub_hrs = i.num_subcontractors * i.avg_sub_hours_week * i.utilization_target
    total_cap = sustainable + sub_hrs
    balance = total_cap - i.active_workload_hrs
    stress = max(0.0, min(100.0, round((i.active_workload_hrs / max(total_cap, 1)) * 100 - 50, 1)))
    if balance >= 0:
        status = "OK"
    elif balance >= -15:
        status = "TIGHT"
    else:
        status = "OVERLOADED"
    o.exp_sustainable_capacity_wk = round(total_cap, 2)
    o.exp_capacity_balance = round(balance, 2)
    o.exp_capacity_stress_score = stress
    o.exp_capacity_status = status


def run_block3_backlog(i: BusinessInputs, o: EngineOutputs):
    """Block 3 — Backlog / Delay"""
    cap = max(o.exp_sustainable_capacity_wk, 1.0)
    backlog = max(0.0, i.active_workload_hrs - cap)
    delay_days = int(round((backlog / cap) * 7)) if backlog > 0 else 0
    promise_days = delay_days + 2  # service promise buffer from inputs
    if delay_days == 0:
        status = "OK"
    elif delay_days <= 7:
        status = "Warning"
    else:
        status = "Critical"
    o.exp_backlog_hrs = round(backlog, 1)
    o.exp_delay_days = delay_days
    o.exp_delay_status = status
    o.exp_promise_days = promise_days


def run_block4_customer(i: BusinessInputs, o: EngineOutputs):
    """Block 4 — Customer Reaction"""
    sensitivity_mult = {"Low": 0.5, "Medium": 1.0, "High": 1.5}.get(i.customer_sensitivity, 1.0)
    delay_over = max(0, o.exp_delay_days - i.target_promise_days)
    delay_penalty = min(40.0, delay_over * 5.0 * sensitivity_mult)
    comm_bonus = i.communication_quality * 10
    rel_bonus = i.relationship_strength * 10
    score = max(0.0, min(100.0, 100 - delay_penalty + comm_bonus * 0.3 + rel_bonus * 0.3 - 10))
    if score >= 85:
        label, churn, action = "Happy", "Low", "Standard update cadence"
    elif score >= 70:
        label, churn, action = "Satisfied", "Low", "Monitor"
    elif score >= 50:
        label, churn, action = "Concerned", "Medium", "Proactive communication needed"
    else:
        label, churn, action = "Frustrated", "High", "Immediate escalation required"
    o.exp_reaction_score = round(score, 1)
    o.exp_reaction_label = label
    o.exp_churn_risk = churn
    o.exp_suggested_action = action


def run_block5_quality(i: BusinessInputs, o: EngineOutputs):
    """Block 5 — Service Quality"""
    delay_over = max(0, o.exp_delay_days - i.delay_tolerance_days)
    delay_penalty = min(i.max_delay_penalty, delay_over * 3.0)
    reaction_adj = (o.exp_reaction_score - 75) * i.reaction_weight * 0.2
    process_bonus = i.process_discipline * 10
    score = max(0.0, min(100.0,
        i.base_quality_score - delay_penalty + reaction_adj + process_bonus - 10))
    if score >= 85:
        label, risk = "Excellent", "Low"
    elif score >= 70:
        label, risk = "Good", "Low"
    elif score >= 55:
        label, risk = "Poor", "High"
    else:
        label, risk = "Critical", "High"
    rework = min(0.6, i.base_rework_rate + max(0, (80 - score) / 100) * i.rework_sensitivity)
    multiplier = 1 + rework
    referral = max(0.0, min(1.0, 0.25 + (score - 75) / 100))
    retention = max(0.0, min(1.0, 0.85 + (score - 75) / 100 * 0.5))
    o.exp_service_quality_score = round(score, 2)
    o.exp_quality_label = label
    o.exp_quality_risk = risk
    o.exp_rework_rate = round(rework, 3)
    o.exp_delivery_hrs_multiplier = round(multiplier, 3)
    o.exp_referral_likelihood = round(referral, 3)
    o.exp_retention_likelihood = round(retention, 3)


def run_block6_retain(i: BusinessInputs, o: EngineOutputs):
    """Block 6 — Retain / Refer"""
    retained = i.num_active_projects * o.exp_retention_likelihood
    referrals_gen = retained * 0.6 * i.referral_conversion_factor
    converted = referrals_gen * i.referral_conversion_rate
    future_hrs = (retained * i.avg_repeat_work_hrs +
                  converted * i.avg_new_project_hrs_referral)
    new_work_per_week = future_hrs / max(i.horizon_weeks, 1) * 0.6
    o.exp_retention_likelihood = o.exp_retention_likelihood
    o.exp_referral_likelihood = o.exp_referral_likelihood
    o.exp_retained_projects = round(retained, 2)
    o.exp_converted_referral_projects = round(converted, 2)
    o.exp_future_work_hours = round(future_hrs, 2)
    o.exp_new_work_hours_per_week = round(new_work_per_week, 2)


def run_block8_labor(i: BusinessInputs, o: EngineOutputs):
    """Block 8 — Labor & Subcontractors"""
    sub_hrs = i.num_subcontractors * i.avg_sub_hours_week
    total_cap = (i.owner_total_hours_week - i.admin_hours_week) + sub_hrs
    owner_cost = i.owner_total_hours_week * i.owner_cost_rate * 4.33
    sub_cost = i.num_subcontractors * i.avg_sub_hours_week * i.avg_sub_cost_rate * 4.33
    labor_cost_mo = round(owner_cost + sub_cost, 2)
    owner_rev = (i.owner_total_hours_week - i.admin_hours_week) * i.owner_billing_rate * 4.33
    sub_rev = i.num_subcontractors * i.avg_sub_hours_week * i.avg_sub_billing_rate * 4.33
    total_rev = owner_rev + sub_rev
    margin = (total_rev - labor_cost_mo) / max(total_rev, 1)
    incoming_hrs = o.exp_new_work_hours_12w_expected / max(i.horizon_weeks, 1)
    gap = total_cap - incoming_hrs
    if gap < -30 or (i.num_subcontractors == 0 and gap < -10):
        hire_flag = "HIRE TRIGGER"
    else:
        hire_flag = "OK"
    sub_markup = (i.avg_sub_billing_rate - i.avg_sub_cost_rate) / max(i.avg_sub_billing_rate, 1)
    o.exp_team_capacity_per_week = round(total_cap, 1)
    o.exp_labor_cost_monthly = labor_cost_mo
    o.exp_gross_labor_margin = round(margin, 4)
    o.exp_capacity_gap_wk1 = round(gap, 1)
    o.exp_hire_trigger_flag = hire_flag
    o.exp_sub_markup_margin = round(sub_markup, 4)


def run_pricing(i: BusinessInputs, o: EngineOutputs):
    """Spine: Pricing & Margin Engine"""
    quality_adj = (o.exp_service_quality_score - 75) * 0.001
    effective_rate = i.base_hourly_rate * (1 + quality_adj)
    avg_value = effective_rate * i.avg_hours_per_project
    win_rate_adj = i.base_win_rate + (o.exp_service_quality_score - 75) * 0.003
    win_rate = max(0.05, min(0.85, win_rate_adj))
    closes_per_month = o.exp_qualified_leads_per_week * win_rate * 4.33
    est_monthly_rev = closes_per_month * avg_value
    labor_cost_per_hr = i.owner_cost_rate
    gross_margin = (effective_rate - labor_cost_per_hr) / max(effective_rate, 1)
    if gross_margin >= 0.55:
        margin_label = "STRONG"
    elif gross_margin >= 0.40:
        margin_label = "HEALTHY"
    elif gross_margin >= 0.25:
        margin_label = "THIN"
    else:
        margin_label = "AT RISK"
    o.exp_effective_hourly_rate = round(effective_rate, 2)
    o.exp_effective_win_rate_price = round(win_rate, 4)
    o.exp_project_gross_margin = round(gross_margin, 4)
    o.exp_avg_project_value = round(avg_value, 2)
    o.exp_est_monthly_revenue = round(est_monthly_rev, 2)
    o.exp_margin_label = margin_label


def run_qualify(i: BusinessInputs, o: EngineOutputs):
    """Spine: Qualify Engine"""
    delay_penalty = 0.0
    if o.exp_delay_days > 3:
        penalty_frac = min(1.0, (o.exp_delay_days - 3) / max(10 - 3, 1))
        delay_penalty = penalty_frac * 0.30
    qual_rate = max(0.05, 0.35 - delay_penalty)
    per_week = o.exp_total_leads_per_week * qual_rate
    o.exp_qual_rate_effective = round(qual_rate, 4)
    o.exp_qualified_leads_per_week = round(per_week, 2)
    o.exp_qualified_leads_12w = round(per_week * i.horizon_weeks, 2)
    o.exp_qualified_week1 = round(o.exp_leads_week1 * qual_rate, 2)
    o.exp_qualified_week2 = round(o.exp_leads_week2 * qual_rate, 2)
    o.exp_qualified_week3 = round(o.exp_leads_week3 * qual_rate, 2)


def run_proposal(i: BusinessInputs, o: EngineOutputs):
    """Spine: Proposal Engine"""
    base_rate = 0.75
    delay_over = max(0, o.exp_delay_days - 5)
    delay_pen = min(0.35, delay_over * 0.02)
    quality_delta = o.exp_service_quality_score - 80
    quality_bonus = min(0.20, max(-0.20, quality_delta * 0.003))
    effective_rate = max(0.10, min(0.95, base_rate - delay_pen + quality_bonus))
    proposals_pw = o.exp_qualified_leads_per_week * effective_rate
    o.exp_effective_proposal_rate = round(effective_rate, 4)
    o.exp_proposals_week1 = round(o.exp_qualified_week1 * effective_rate, 2)
    o.exp_proposals_week2 = round(o.exp_qualified_week2 * effective_rate, 2)
    o.exp_proposals_week3 = round(o.exp_qualified_week3 * effective_rate, 2)
    o.exp_proposals_12w = round(proposals_pw * i.horizon_weeks, 2)
    o.exp_proposal_hours_12w = round(o.exp_proposals_12w * 1.0, 2)
    o.exp_followup_rate = 0.9


def run_close(i: BusinessInputs, o: EngineOutputs):
    """Spine: Close Engine"""
    quality_bonus = max(0.0, (o.exp_service_quality_score - 50) * i.quality_bonus_sensitivity)
    delay_over = max(0, o.exp_delay_days - i.delay_threshold_days)
    delay_pen = min(0.30, delay_over * i.delay_penalty_sensitivity)
    win_rate = max(0.05, min(0.85, i.base_win_rate + quality_bonus - delay_pen))
    closed_pw = o.exp_proposals_week1 * win_rate
    closed_12w = o.exp_proposals_12w * win_rate
    new_hrs_12w = closed_12w * i.avg_delivery_hrs_per_project
    o.exp_effective_win_rate = round(win_rate, 4)
    o.exp_closed_week1_expected = round(o.exp_proposals_week1 * win_rate, 2)
    o.exp_closed_week2_expected = round(o.exp_proposals_week2 * win_rate, 2)
    o.exp_closed_week3_expected = round(o.exp_proposals_week3 * win_rate, 2)
    o.exp_closed_12w_expected = round(closed_12w, 2)
    o.exp_new_work_hours_12w_expected = round(new_hrs_12w, 2)


def run_deliver(i: BusinessInputs, o: EngineOutputs):
    """Spine: Deliver Engine"""
    cap = o.exp_sustainable_capacity_wk * 0.85
    invoiceable_cap = cap
    rework_mult = o.exp_delivery_hrs_multiplier
    labor_hrs_pw = min(cap, (o.exp_new_work_hours_12w_expected / i.horizon_weeks) * rework_mult)
    invoice_ready_pw = labor_hrs_pw / rework_mult
    delivered_12w = invoice_ready_pw * i.horizon_weeks
    labor_12w = labor_hrs_pw * i.horizon_weeks
    end_backlog = max(0.0, o.exp_backlog_hrs + (o.exp_new_work_hours_12w_expected - delivered_12w))
    projects_done = delivered_12w / max(i.avg_delivery_hrs_per_project, 1)
    o.exp_invoiceable_cap_per_week = round(invoiceable_cap, 2)
    o.exp_delivered_12w = round(delivered_12w, 2)
    o.exp_invoice_ready_12w = round(delivered_12w, 2)
    o.exp_labor_hours_spent_12w = round(labor_12w, 2)
    o.exp_end_backlog_week12 = round(end_backlog, 2)
    o.exp_projects_completed_12w = round(projects_done, 2)


def run_invoice(i: BusinessInputs, o: EngineOutputs):
    """Spine: Invoice Engine"""
    billable_hrs = o.exp_invoice_ready_12w * 0.95
    total_invoiced = billable_hrs * i.base_hourly_rate
    avg_per_week = total_invoiced / max(i.horizon_weeks, 1)
    effective_rate = total_invoiced / max(billable_hrs, 1)
    o.exp_total_invoiced_12w = round(total_invoiced, 2)
    o.exp_billable_hours_12w = round(billable_hrs, 2)
    o.exp_avg_invoice_per_week = round(avg_per_week, 2)
    o.exp_effective_rate = round(effective_rate, 2)


def run_getpaid(i: BusinessInputs, o: EngineOutputs):
    """Spine: GetPaid Engine"""
    total = o.exp_total_invoiced_12w
    # Apply collection lag distribution
    collected = total * i.pct_collected_eventually
    ending_ar = total - collected + i.starting_ar_balance
    cash_wk1 = o.exp_avg_invoice_per_week * i.collection_lag_same_week
    cash_wk2 = o.exp_avg_invoice_per_week * (i.collection_lag_same_week + i.collection_lag_1wk)
    cash_wk3 = o.exp_avg_invoice_per_week * (i.collection_lag_same_week + i.collection_lag_1wk + i.collection_lag_2wk)
    collection_pct = collected / max(total, 1)
    o.exp_cash_received_12w = round(collected, 2)
    o.exp_ending_ar_week12 = round(max(0, ending_ar), 2)
    o.exp_invoices_issued_12w = round(total, 2)
    o.exp_collection_pct_12w = round(collection_pct, 4)


def run_block7_expense(i: BusinessInputs, o: EngineOutputs):
    """Block 7 — Expense & Tax"""
    total_monthly = i.fixed_monthly_expenses + i.variable_monthly_expenses
    total_outflow_mo = total_monthly + i.owner_draw_monthly
    weekly_burn = total_outflow_mo / 4.33
    weekly_in = o.exp_cash_received_12w / max(i.horizon_weeks, 1)
    net_12w = (weekly_in - weekly_burn) * i.horizon_weeks
    ending_cash = i.starting_cash + net_12w
    runway = i.starting_cash / max(weekly_burn, 1) / 4.33  # months
    tax_reserve = o.exp_cash_received_12w * i.tax_reserve_rate * 0.25  # quarterly fraction
    mrr_monthly = o.exp_current_mrr
    mrr_runway = (i.starting_cash + mrr_monthly * 3) / max(weekly_burn * 4.33, 1)
    if ending_cash < 0:
        cash_status = "NEGATIVE CASH"
    elif ending_cash < i.starting_cash * 0.3:
        cash_status = "CRITICAL"
    elif ending_cash < i.starting_cash:
        cash_status = "LOW"
    else:
        cash_status = "HEALTHY"
    o.exp_monthly_expenses = round(total_monthly, 2)
    o.exp_weekly_burn = round(weekly_burn, 2)
    o.exp_net_cash_12w = round(net_12w, 2)
    o.exp_ending_cash = round(ending_cash, 2)
    o.exp_survival_runway_months = round(runway, 2)
    o.exp_tax_reserve_12w = round(tax_reserve, 2)
    o.exp_cash_health_status = cash_status
    o.exp_mrr_adjusted_runway = round(mrr_runway, 2)


def run_block9_recurring(i: BusinessInputs, o: EngineOutputs):
    """Block 9 — Recurring Revenue"""
    current_mrr = i.current_retainer_clients * i.avg_retainer_value_monthly
    # Project 12-month growth with churn
    mrr = current_mrr
    for _ in range(12):
        mrr = mrr * (1 - i.monthly_churn_rate) + i.new_retainer_conversions_per_month * i.avg_retainer_value_monthly
    mrr_month12 = mrr
    target_mrr = i.target_retainer_clients * i.avg_retainer_value_monthly
    stability = min(100.0, (current_mrr / max(target_mrr, 1)) * 100)
    total_rev_monthly = o.exp_est_monthly_revenue + current_mrr
    recurring_share = current_mrr / max(total_rev_monthly, 1)
    expense_coverage = current_mrr / max(o.exp_monthly_expenses, 1)
    if current_mrr == 0:
        churn_flag = "TOO VOLATILE"
    elif current_mrr < o.exp_monthly_expenses * 0.25:
        churn_flag = "AT RISK"
    else:
        churn_flag = "STABLE"
    o.exp_current_mrr = round(current_mrr, 2)
    o.exp_mrr_month12 = round(mrr_month12, 2)
    o.exp_mrr_stability_score = round(stability, 1)
    o.exp_recurring_share = round(recurring_share, 4)
    o.exp_churn_risk_flag = churn_flag
    o.exp_mrr_coverage_expenses = round(expense_coverage, 4)
    o.exp_retainer_clients = i.current_retainer_clients


def run_dashboard_summary(o: EngineOutputs):
    """Compute XP score, level, status banner."""
    xp = 0
    if o.exp_ending_cash > 5000:              xp += 20
    if o.exp_net_cash_12w > 0:                xp += 25
    if o.exp_capacity_stress_score < 50:      xp += 15
    if o.exp_service_quality_score >= 80:     xp += 20
    if o.exp_retainer_clients > 0:            xp += 15
    if o.exp_hire_trigger_flag == "OK":        xp += 5
    xp = min(100, xp)

    if xp >= 90:   level, title = 5, "Business Legend"
    elif xp >= 70: level, title = 4, "Running Smooth"
    elif xp >= 50: level, title = 3, "Getting Traction"
    elif xp >= 30: level, title = 2, "Finding Your Feet"
    else:          level, title = 1, "Tough Week"

    issues = []
    wins = []
    weekly_in = o.exp_cash_received_12w / 12
    weekly_out = o.exp_weekly_burn
    if weekly_in < weekly_out:
        issues.append("More money is going out than coming in each week.")
    else:
        wins.append("Money coming in beats money going out.")
    if o.exp_capacity_stress_score > 60:
        issues.append(f"You have {o.exp_backlog_hrs}h of work backed up — customers waiting {o.exp_delay_days} days.")
    else:
        wins.append("Work load is manageable right now.")
    if o.exp_service_quality_score < 70:
        issues.append("Customer satisfaction is low — delays are starting to hurt your reputation.")
    else:
        wins.append("Customers are happy.")
    if o.exp_ending_cash < 0:
        issues.append(f"You'll run out of cash in about {max(0, o.exp_survival_runway_months):.1f} months at this rate.")

    if len(issues) >= 2:
        headline = "You're in a tough spot right now."
    elif len(issues) == 1:
        headline = "Things are moving, but there's one thing to watch."
    else:
        headline = "Business is running well. Keep it up."

    o.xp_score = xp
    o.xp_level = level
    o.xp_title = title
    o.status_headline = headline
    o.status_issues = issues
    o.status_wins = wins


# ─── MAIN RUNNER ──────────────────────────────────────────────────────────────

def run_all(inputs: BusinessInputs) -> EngineOutputs:
    """
    Run the full 18-engine chain in dependency order.
    Returns a complete EngineOutputs object.
    """
    o = EngineOutputs()

    # Stage 1: Structural
    run_active_workload(inputs, o)
    run_block2_capacity(inputs, o)
    run_block3_backlog(inputs, o)

    # Stage 2: Customer loop
    run_block4_customer(inputs, o)
    run_block5_quality(inputs, o)
    run_block6_retain(inputs, o)

    # Stage 3: Lead → Pipeline chain
    run_block0_leads(inputs, o)
    run_qualify(inputs, o)
    run_pricing(inputs, o)
    run_proposal(inputs, o)
    run_close(inputs, o)

    # Stage 4: Delivery chain
    run_deliver(inputs, o)
    run_invoice(inputs, o)
    run_getpaid(inputs, o)

    # Stage 5: Financial
    run_block7_expense(inputs, o)
    run_block8_labor(inputs, o)
    run_block9_recurring(inputs, o)

    # Stage 6: Dashboard summary
    run_dashboard_summary(o)

    return o


def to_dict(outputs: EngineOutputs) -> dict:
    return asdict(outputs)
