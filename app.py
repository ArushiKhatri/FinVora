
from flask import Flask, render_template, request, jsonify
import logic

app = Flask(__name__)


@app.route("/")
def home():
    """Serve the main HTML page."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Budget Tracker API is running."})


@app.route("/calculate", methods=["POST"])
def calculate():
    """
    Receives JSON from the HTML page's JavaScript fetch() call.
    Calls logic.py, returns full summary as JSON.
    """
    data = request.get_json()

    income_sources = data.get("income_sources", {})
    expenses       = data.get("expenses", {})
    monthly_budget = float(data.get("monthly_budget", 0))
    savings_goal   = float(data.get("savings_goal", 0))

    if not income_sources:
        return jsonify({"error": "Please add at least one income source."}), 400

    totals         = logic.calculate_totals(income_sources, expenses)
    budget_status  = logic.get_budget_status(totals["total_spent"], monthly_budget)
    savings_status = logic.get_savings_status(totals["actual_savings"], savings_goal)
    top_expense    = logic.get_top_expense(expenses)
    income_pct     = logic.get_income_percentages(income_sources, totals["total_income"])
    expense_pct    = logic.get_expense_percentages(expenses, totals["total_income"])

    return jsonify({
        "totals":         totals,
        "budget_status":  budget_status,
        "savings_status": savings_status,
        "top_expense":    top_expense,
        "income_pct":     income_pct,
        "expense_pct":    expense_pct,
        "monthly_budget": monthly_budget,
        "savings_goal":   savings_goal,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5050)
