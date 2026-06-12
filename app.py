from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from models import db, User, MonthlyRecord
import logic
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "my_budget_tracker_secret_123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finvora.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


def is_logged_in():
    return "username" in session


def get_or_create_record(user_id, current_month):
    """Helper: fetch existing MonthlyRecord or create a blank one."""
    record = MonthlyRecord.query.filter_by(user_id=user_id, month=current_month).first()
    if not record:
        record = MonthlyRecord(
            user_id=user_id,
            month=current_month,
            income_sources=json.dumps({}),
            expenses=json.dumps({}),
            monthly_budget=0,
            savings_goal=0
        )
        db.session.add(record)
        db.session.commit()
    return record


# ─── HOME ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("home.html", username=session["username"])


# ─── BUDGET ──────────────────────────────────────────────────────────────────

@app.route("/budget")
@app.route("/index")
@app.route("/index.html")
def budget():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("index.html", username=session["username"])


# ─── LOAD CURRENT MONTH ENTRIES (new) ────────────────────────────────────────

@app.route("/load-entries", methods=["GET"])
def load_entries():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    record = MonthlyRecord.query.filter_by(user_id=user_id, month=current_month).first()

    if not record:
        return jsonify({
            "income_sources": {},
            "expenses": {},
            "monthly_budget": 0,
            "savings_goal": 0
        })

    return jsonify({
        "income_sources": json.loads(record.income_sources or "{}"),
        "expenses": json.loads(record.expenses or "{}"),
        "monthly_budget": record.monthly_budget or 0,
        "savings_goal": record.savings_goal or 0
    })


# ─── SAVE SINGLE ENTRY (new) ─────────────────────────────────────────────────
# Called immediately whenever the user adds/edits/removes an income or expense,
# or changes the budget / savings goal fields.
#
# Body (JSON):
#   type          : "income" | "expense" | "limits"
#   key           : source name / category  (not needed for "limits")
#   amount        : float
#   old_key       : (optional) original key when renaming an income source
#   action        : "add" | "delete"
#   monthly_budget: (only for type="limits")
#   savings_goal  : (only for type="limits")

@app.route("/save-entry", methods=["POST"])
def save_entry():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")

    record = get_or_create_record(user_id, current_month)

    entry_type = data.get("type")        # "income" | "expense" | "limits"
    action     = data.get("action", "add")  # "add" | "delete"

    if entry_type == "limits":
        record.monthly_budget = float(data.get("monthly_budget", 0))
        record.savings_goal   = float(data.get("savings_goal", 0))

    elif entry_type == "income":
        incomes = json.loads(record.income_sources or "{}")
        old_key = data.get("old_key")   # present when renaming
        key     = data.get("key", "").strip()
        amount  = float(data.get("amount", 0))

        if action == "delete":
            incomes.pop(key, None)
        else:
            # If renaming (old_key differs from new key), remove old entry first
            if old_key and old_key != key:
                incomes.pop(old_key, None)
            incomes[key] = amount

        record.income_sources = json.dumps(incomes)

    elif entry_type == "expense":
        expenses = json.loads(record.expenses or "{}")
        key    = data.get("key", "").strip()
        amount = float(data.get("amount", 0))

        if action == "delete":
            expenses.pop(key, None)
        else:
            expenses[key] = amount

        record.expenses = json.dumps(expenses)

    else:
        return jsonify({"error": "Unknown entry type"}), 400

    db.session.commit()
    return jsonify({"ok": True})


# ─── CALCULATE ────────────────────────────────────────────────────────────────

@app.route("/calculate", methods=["POST"])
def calculate():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    data = request.get_json()

    income_sources = data.get("income_sources", {})
    expenses       = data.get("expenses", {})
    monthly_budget = float(data.get("monthly_budget", 0))
    savings_goal   = float(data.get("savings_goal", 0))

    if not income_sources:
        return jsonify({"error": "Please add at least one income source."}), 400

    # Also persist the latest snapshot (in case user edited limits without triggering save-entry)
    current_month = datetime.now().strftime("%Y-%m")
    user_id = session["user_id"]
    record = get_or_create_record(user_id, current_month)
    record.income_sources = json.dumps(income_sources)
    record.expenses       = json.dumps(expenses)
    record.monthly_budget = monthly_budget
    record.savings_goal   = savings_goal
    db.session.commit()

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
        "savings_goal":   savings_goal
    })


# ─── HISTORY ──────────────────────────────────────────────────────────────────

@app.route("/history")
@app.route("/history.html")
def history():
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    records = MonthlyRecord.query.filter_by(user_id=user_id).order_by(MonthlyRecord.month.desc()).all()

    history_list = []
    for r in records:
        income_sources = json.loads(r.income_sources) if r.income_sources else {}
        expenses       = json.loads(r.expenses)       if r.expenses       else {}
        totals         = logic.calculate_totals(income_sources, expenses)

        history_list.append({
            "month":          r.month,
            "total_income":   totals["total_income"],
            "total_spent":    totals["total_spent"],
            "actual_savings": totals["actual_savings"],
            "savings_goal":   r.savings_goal or 0,
            "monthly_budget": r.monthly_budget or 0
        })

    return render_template("history.html", history=history_list, username=session["username"])


# ─── SIGNUP ───────────────────────────────────────────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup.html", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("signup.html", error="Both fields are required.")
        if len(username) < 3:
            return render_template("signup.html", error="Username must be at least 3 characters.")
        if len(password) < 4:
            return render_template("signup.html", error="Password must be at least 4 characters.")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template("signup.html", error="Username already taken.")

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login", success="Account created! Please log in."))

    return render_template("signup.html")


# ─── LOGIN ────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
@app.route("/login.html", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="Both fields are required.")

        user = User.query.filter_by(username=username, password=password).first()
        if not user:
            return render_template("login.html", error="Invalid username or password.")

        session["username"] = username
        session["user_id"]  = user.id
        return redirect(url_for("home"))

    success = request.args.get("success", "")
    return render_template("login.html", success=success)


# ─── LOGOUT ───────────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── 404 ──────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    if is_logged_in():
        return redirect(url_for("home"))
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
