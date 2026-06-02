from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import logic

app = Flask(__name__)


app.secret_key = "my_budget_tracker_secret_123"


users = {}


# ── Helper ────────────────────────────────────
def is_logged_in():
    """Returns True if a user is currently logged in (session has 'username')."""
    return "username" in session


# ── Auth Routes ───────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    GET  → show the signup form (signup.html)
    POST → read form data, validate, store user, redirect to login
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Basic validation
        if not username or not password:
            return render_template("signup.html", error="Both fields are required.")

        if len(username) < 3:
            return render_template("signup.html", error="Username must be at least 3 characters.")

        if len(password) < 4:
            return render_template("signup.html", error="Password must be at least 4 characters.")

        if username in users:
            return render_template("signup.html", error="Username already taken. Try another.")

        # Save the new user
        users[username] = password
        # Redirect to login with a success message
        return redirect(url_for("login", success="Account created! Please log in."))

    # GET request — just show the empty signup form
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    GET  → show the login form (login.html)
    POST → check credentials, set session, redirect to home
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="Both fields are required.")

        # Check if user exists AND password matches
        if users.get(username) != password:
            return render_template("login.html", error="Invalid username or password.")

      
      
        session["username"] = username
        return redirect(url_for("home"))

    # GET request — check for optional success message from signup redirect
    success = request.args.get("success", "")
    return render_template("login.html", success=success)


@app.route("/logout")
def logout():
    """Clear the session (log the user out) and send them to login."""
    session.clear()
    return redirect(url_for("login"))


# ── Protected Routes ──────────────────────────

@app.route("/")
def home():
    """
    Only logged-in users can see the budget tracker.
    If not logged in, redirect to /login.
    """
    if not is_logged_in():
        return redirect(url_for("login"))

    # Pass username to the template so we can show "Hello, <name>"
    return render_template("index.html", username=session["username"])


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Budget Tracker API is running."})


@app.route("/calculate", methods=["POST"])
def calculate():
    """
    Protected API endpoint — only works when logged in.
    Receives JSON from the frontend's fetch() call.
    """
    if not is_logged_in():
        return jsonify({"error": "Unauthorized. Please log in."}), 401

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
