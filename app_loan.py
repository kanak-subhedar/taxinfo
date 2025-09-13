from flask import Flask, request, jsonify, render_template_string
from math import pow, floor

app = Flask(__name__)

# ---------- Sample lenders (you can extend these or load from DB) ----------
LENDERS = [
    {
        "id": "bank_a",
        "name": "Bank A",
        "annual_rate_percent": 8.35,
        "max_tenure_years": 30,
        "min_credit_score": 650,
        "min_age": 21,
        "max_age": 65
    },
    {
        "id": "nbfc_x",
        "name": "NBFC X",
        "annual_rate_percent": 9.75,
        "max_tenure_years": 20,
        "min_credit_score": 600,
        "min_age": 22,
        "max_age": 62
    },
    {
        "id": "bank_b",
        "name": "Bank B",
        "annual_rate_percent": 7.9,
        "max_tenure_years": 25,
        "min_credit_score": 700,
        "min_age": 23,
        "max_age": 67
    }
]

# ---------- Utility functions ----------
def monthly_rate_from_annual(annual_percent):
    return annual_percent / 100.0 / 12.0

def emi_for_loan(principal, monthly_rate, months):
    """
    EMI formula:
      EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    Handles r = 0 case.
    """
    if months <= 0:
        return 0.0
    if monthly_rate == 0:
        return principal / months
    r = monthly_rate
    pow_val = pow(1 + r, months)
    emi = principal * r * pow_val / (pow_val - 1)
    return emi

def amortization_schedule(principal, monthly_rate, months):
    """
    Returns list of monthly entries:
    {month, payment, principal_component, interest_component, balance}
    """
    schedule = []
    balance = principal
    emi = emi_for_loan(principal, monthly_rate, months)
    for m in range(1, months + 1):
        if monthly_rate == 0:
            interest = 0.0
        else:
            interest = balance * monthly_rate
        principal_comp = emi - interest
        # Last payment adjust to avoid tiny negative balances due to rounding
        if principal_comp > balance:
            principal_comp = balance
            emi = principal_comp + interest
        balance = round(balance - principal_comp, 2)
        schedule.append({
            "month": m,
            "payment": round(emi, 2),
            "principal_component": round(principal_comp, 2),
            "interest_component": round(interest, 2),
            "balance": round(balance if balance > 0 else 0.0, 2)
        })
        if balance <= 0:
            break
    return schedule

def max_loan_from_affordable_emi(emi_affordable, monthly_rate, months):
    """
    Invert EMI formula to get maximum principal:
      P = EMI * (1 - (1+r)^-n) / r
    Handles r = 0
    """
    if months <= 0:
        return 0.0
    r = monthly_rate
    if r == 0:
        return emi_affordable * months
    pow_val = pow(1 + r, -months)
    principal = emi_affordable * (1 - pow_val) / r
    return principal

# ---------- Eligibility rules ----------
# Default allowed ratio of income that can go to EMIs (Debt-to-Income constraint)
DEFAULT_ALLOWED_INCOME_RATIO = 0.50  # 50% of monthly income can be used for EMIs (customizable)

def check_eligibility(user, lender, desired_emi):
    """
    user: dict with keys - monthly_income, existing_emi, age, employment_months, credit_score
    lender: the lender dict
    desired_emi: calculated EMI for requested principal/tenure
    Returns dict with decision, reasons, and numeric checks.
    """
    monthly_income = float(user.get("monthly_income", 0))
    existing_emi = float(user.get("existing_emi", 0))
    age = int(user.get("age", 0))
    employment_months = int(user.get("employment_months", 0))
    credit_score = int(user.get("credit_score", 0))

    allowed_emi_total = monthly_income * DEFAULT_ALLOWED_INCOME_RATIO
    remaining_capacity = allowed_emi_total - existing_emi
    can_cover = desired_emi <= max(0.0, remaining_capacity)

    reasons = []
    passed = True

    # Age checks
    if age < lender.get("min_age", 21):
        passed = False
        reasons.append(f"Applicant is younger than lender's minimum age {lender.get('min_age')}.")
    if age > lender.get("max_age", 70):
        passed = False
        reasons.append(f"Applicant is older than lender's maximum age {lender.get('max_age')}.")

    # Employment tenure: require at least 6 months for salaried, 12 months for self-employed (simple heuristic)
    if employment_months < 6:
        passed = False
        reasons.append("Employment tenure less than 6 months (many lenders require >=6 months).")

    # Credit score
    if credit_score < lender.get("min_credit_score", 600):
        passed = False
        reasons.append(f"Credit score below lender's minimum ({lender.get('min_credit_score')}).")

    # DTI / EMI capacity
    if desired_emi > remaining_capacity:
        passed = False
        reasons.append(f"Desired EMI ({round(desired_emi,2)}) exceeds allowed remaining EMI capacity ({round(remaining_capacity,2)}).")

    decision = "Eligible" if passed else "Not eligible"
    return {
        "decision": decision,
        "passed": passed,
        "reasons": reasons,
        "allowed_emi_total": round(allowed_emi_total, 2),
        "remaining_capacity": round(remaining_capacity, 2),
        "desired_emi": round(desired_emi, 2),
        "monthly_income": round(monthly_income, 2),
        "existing_emi": round(existing_emi, 2),
        "age": age,
        "employment_months": employment_months,
        "credit_score": credit_score
    }

# ---------- API endpoints ----------
@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """
    Expected JSON:
    {
      "principal": 2000000,
      "tenure_years": 20,
      "lenders": [ "bank_a", "nbfc_x" ],  # optional, otherwise uses all lenders
      "prepayment_years": 0,  # optional
      "extra_monthly_payment": 0  # optional
    }
    Response:
    {
      "comparisons": [ { lender:..., emi:..., total_payment:..., total_interest:..., schedule: [...] }, ... ],
      "notes": ...
    }
    """
    data = request.get_json() or {}
    principal = float(data.get("principal", 0))
    tenure_years = float(data.get("tenure_years", 0))
    months = int(round(tenure_years * 12))
    chosen = data.get("lenders") or [l["id"] for l in LENDERS]
    extra_monthly = float(data.get("extra_monthly_payment", 0))

    comparisons = []
    for l in LENDERS:
        if l["id"] not in chosen:
            continue
        r_monthly = monthly_rate_from_annual(l["annual_rate_percent"])
        emi = emi_for_loan(principal, r_monthly, months)
        # If extra_monthly present, compute new faster amortization schedule (not changing EMI here; we show schedule with extra payment)
        schedule = amortization_schedule_with_extra(principal, r_monthly, months, emi, extra_monthly)
        total_payment = sum([s["payment"] for s in schedule])
        total_interest = sum([s["interest_component"] for s in schedule])
        comparisons.append({
            "lender_id": l["id"],
            "lender_name": l["name"],
            "annual_rate_percent": l["annual_rate_percent"],
            "tenure_months": months,
            "emi": round(emi, 2),
            "months_paid": len(schedule),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2),
            "schedule": schedule  # careful: could be large
        })

    return jsonify({
        "principal": round(principal, 2),
        "tenure_years": tenure_years,
        "comparisons": comparisons,
        "note": "Schedule includes extra monthly payment effect if extra_monthly_payment provided."
    })

def amortization_schedule_with_extra(principal, monthly_rate, months, base_emi, extra_monthly=0.0):
    """
    Amortization schedule that simulates paying (base_emi + extra_monthly) each month
    and stops when balance is zero (early repayment).
    """
    schedule = []
    balance = principal
    month = 0
    while balance > 0 and month < months * 5:  # safety cap
        month += 1
        payment = base_emi + extra_monthly
        if monthly_rate == 0:
            interest = 0.0
        else:
            interest = balance * monthly_rate
        principal_comp = payment - interest
        if principal_comp <= 0:
            # Payment does not cover interest (unlikely with base_emi), break to avoid infinite loop
            principal_comp = 0.0
            payment = interest
        if principal_comp > balance:
            principal_comp = balance
            payment = interest + principal_comp
        balance = round(balance - principal_comp, 2)
        schedule.append({
            "month": month,
            "payment": round(payment, 2),
            "principal_component": round(principal_comp, 2),
            "interest_component": round(interest, 2),
            "balance": round(balance if balance > 0 else 0.0, 2)
        })
        if month > months and balance > 0 and extra_monthly == 0:
            # If no extra payment and we've done scheduled months, stop to avoid infinite loop
            break
    return schedule

@app.route("/api/eligibility", methods=["POST"])
def api_eligibility():
    """
    Expected JSON:
    {
      "principal": 2000000,
      "tenure_years": 20,
      "user": {
         "monthly_income": 60000,
         "existing_emi": 5000,
         "age": 30,
         "employment_months": 24,
         "credit_score": 710
      },
      "lender_id": "bank_a"  # optional, will check all lenders if omitted
    }
    """
    data = request.get_json() or {}
    principal = float(data.get("principal", 0))
    tenure_years = float(data.get("tenure_years", 0))
    months = int(round(tenure_years * 12))
    user = data.get("user", {})
    lender_id = data.get("lender_id")

    results = []
    lenders_to_check = [l for l in LENDERS if (lender_id is None or l["id"] == lender_id)]
    for l in lenders_to_check:
        r_monthly = monthly_rate_from_annual(l["annual_rate_percent"])
        emi = emi_for_loan(principal, r_monthly, months)
        # eligibility based on heuristics
        check = check_eligibility(user, l, emi)
        # Also compute maximum affordable loan based on remaining capacity
        remaining_capacity = max(0.0, user.get("monthly_income", 0) * DEFAULT_ALLOWED_INCOME_RATIO - user.get("existing_emi", 0))
        max_loan = max_loan_from_affordable_emi(remaining_capacity, r_monthly, months)
        results.append({
            "lender_id": l["id"],
            "lender_name": l["name"],
            "annual_rate_percent": l["annual_rate_percent"],
            "tenure_months": months,
            "requested_loan": round(principal, 2),
            "emi_for_requested_loan": round(emi, 2),
            "max_affordable_loan_for_user": round(max_loan, 2),
            "eligibility": check
        })
    return jsonify({
        "user": user,
        "tenure_years": tenure_years,
        "results": results
    })
