def calculate_totals(income_sources: dict, expenses: dict) -> dict:
  
    
    total_income   = sum(income_sources.values())
    total_spent    = sum(expenses.values())
    amount_left    = total_income - total_spent
    actual_savings = total_income - total_spent

    return {
        "total_income":   total_income,
        "total_spent":    total_spent,
        "amount_left":    amount_left,
        "actual_savings": actual_savings,
    }


def get_budget_status(total_spent: float, monthly_budget: float) -> dict:
  
    if monthly_budget <= 0:
        return {"message": "No budget set.", "over": False, "budget_left": 0}

    budget_left = monthly_budget - total_spent

    if total_spent > monthly_budget:
        return {
            "message":    f" Over budget by ₹{abs(budget_left):.2f}!",
            "over":       True,
            "budget_left": budget_left,
        }
    elif total_spent == monthly_budget:
        return {
            "message":    " Spent exactly your budget.",
            "over":       False,
            "budget_left": 0,
        }
    else:
        return {
            "message":    f" Within budget! ₹{budget_left:.2f} left to spend.",
            "over":       False,
            "budget_left": budget_left,
        }


def get_savings_status(actual_savings: float, savings_goal: float) -> dict:
  
    if savings_goal <= 0:
        return {"message": "No savings goal set.", "met": False}

    if actual_savings >= savings_goal:
        extra = actual_savings - savings_goal
        return {
            "message": f" Goal met! Saved ₹{actual_savings:.2f} (₹{extra:.2f} extra)",
            "met":     True,
        }
    else:
        short = savings_goal - actual_savings
        return {
            "message": f" Goal missed. ₹{short:.2f} short of ₹{savings_goal:.2f} goal.",
            "met":     False,
        }


def get_top_expense(expenses: dict) -> dict:
   
    if not expenses:
        return {}

    top_category = max(expenses, key=expenses.get)
    top_amount   = expenses[top_category]
    saving_tip   = top_amount * 0.10

    return {
        "category":   top_category,
        "amount":     top_amount,
        "saving_tip": saving_tip,
    }


def get_income_percentages(income_sources: dict, total_income: float) -> list:
  
    result = []
    for source, amount in income_sources.items():
        pct = (amount / total_income * 100) if total_income > 0 else 0
        result.append({"source": source, "amount": amount, "pct": round(pct, 1)})
    return result


def get_expense_percentages(expenses: dict, total_income: float) -> list:
   
    result = []
    for category, amount in expenses.items():
        pct = (amount / total_income * 100) if total_income > 0 else 0
        result.append({"category": category, "amount": amount, "pct": round(pct, 1)})
    return result


def validate_amount(value) -> tuple:
   
    try:
        amount = float(value)
        if amount <= 0:
            return False, "Amount must be greater than 0."
        return True, amount
    except (ValueError, TypeError):
        return False, "Please enter a valid number."
