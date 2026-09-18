from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
import joblib


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)

# Secret key for session management
app.secret_key = "ai_finance_assistant_secret_key"


# ==================================================
# LOAD AI MODEL
# ==================================================

model = joblib.load("expense_model.pkl")
vectorizer = joblib.load("vectorizer.pkl")


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():

    return render_template("home.html")


# ==================================================
# REGISTER
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password_hash)
                VALUES (%s, %s, %s)
                """,
                (name, email, password_hash)
            )

            connection.commit()

        except Exception as e:

            connection.rollback()

            cursor.close()
            connection.close()

            return f"Registration failed: {e}"

        cursor.close()
        connection.close()

        return redirect("/login")

    return render_template("register.html")


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(
            user["password_hash"],
            password
        ):

            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]

            return redirect("/dashboard")

        return "Invalid email or password"

    return render_template("login.html")


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    # Check login
    if "user_id" not in session:

        return redirect("/login")

    user_id = session["user_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ==================================================
    # TOTAL INCOME
    # ==================================================

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total_income
        FROM transactions
        WHERE user_id = %s
        AND type = 'Income'
        """,
        (user_id,)
    )

    income_result = cursor.fetchone()

    total_income = float(
        income_result["total_income"]
    )


    # ==================================================
    # TOTAL EXPENSES
    # ==================================================

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total_expenses
        FROM transactions
        WHERE user_id = %s
        AND type = 'Expense'
        """,
        (user_id,)
    )

    expense_result = cursor.fetchone()

    total_expenses = float(
        expense_result["total_expenses"]
    )


    # ==================================================
    # BALANCE
    # ==================================================

    balance = total_income - total_expenses


    # ==================================================
    # CATEGORY-WISE EXPENSES
    # ==================================================

    category_query = """
    SELECT
        category,
        SUM(amount) AS total
    FROM transactions
    WHERE user_id = %s
    AND type = 'Expense'
    GROUP BY category
    ORDER BY total DESC
    """

    cursor.execute(
        category_query,
        (user_id,)
    )

    category_expenses = cursor.fetchall()


    # ==================================================
    # MONTHLY EXPENSES
    # ==================================================

    monthly_query = """
    SELECT
        DATE_FORMAT(date, '%Y-%m') AS month,
        SUM(amount) AS total
    FROM transactions
    WHERE user_id = %s
    AND type = 'Expense'
    GROUP BY DATE_FORMAT(date, '%Y-%m')
    ORDER BY month ASC
    """

    cursor.execute(
        monthly_query,
        (user_id,)
    )

    monthly_expenses = cursor.fetchall()


    # ==================================================
    # BUDGET MONITORING
    # ==================================================

    cursor.execute(
        """
        SELECT
            budget_id,
            month,
            category,
            limit_amount
        FROM budgets
        WHERE user_id = %s
        ORDER BY month DESC
        """,
        (user_id,)
    )

    budgets = cursor.fetchall()

    budget_monitoring = []


    for budget in budgets:

        month = budget["month"]
        category = budget["category"]
        limit_amount = float(
            budget["limit_amount"]
        )

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS spent
            FROM transactions
            WHERE user_id = %s
            AND type = 'Expense'
            AND category = %s
            AND DATE_FORMAT(date, '%Y-%m') = %s
            """,
            (
                user_id,
                category,
                month
            )
        )

        spent_result = cursor.fetchone()

        spent = float(
            spent_result["spent"]
        )


        # Determine budget status

        if spent > limit_amount:

            status = "Exceeded"

        elif spent == limit_amount:

            status = "Limit Reached"

        else:

            status = "Within Budget"


        budget_monitoring.append(
            {
                "month": month,
                "category": category,
                "limit_amount": limit_amount,
                "spent": spent,
                "status": status
            }
        )


    cursor.close()
    connection.close()


    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        category_expenses=category_expenses,
        monthly_expenses=monthly_expenses,
        budget_monitoring=budget_monitoring
    )


# ==================================================
# TRANSACTIONS
# ==================================================

@app.route("/transactions")
def transactions():

    if "user_id" not in session:

        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # Get transactions and AI predictions

    query = """
    SELECT
        t.transaction_id,
        t.date,
        t.description,
        t.amount,
        t.type,
        t.category,
        p.predicted_category,
        p.confidence
    FROM transactions t
    LEFT JOIN predictions p
        ON t.transaction_id = p.transaction_id
    WHERE t.user_id = %s
    ORDER BY t.date DESC
    """

    cursor.execute(
        query,
        (session["user_id"],)
    )

    transaction_list = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "transactions.html",
        transactions=transaction_list
    )


# ==================================================
# ADD TRANSACTION
# ==================================================

@app.route(
    "/add-transaction",
    methods=["GET", "POST"]
)
def add_transaction():

    if "user_id" not in session:

        return redirect("/login")


    if request.method == "POST":

        date = request.form["date"]
        description = request.form["description"]
        amount = request.form["amount"]
        transaction_type = request.form["type"]
        category = request.form["category"]


        # Validate amount

        try:

            amount = float(amount)

            if amount <= 0:

                return "Amount must be greater than zero."

        except ValueError:

            return "Invalid amount."


        connection = get_db_connection()
        cursor = connection.cursor()


        # Insert transaction

        cursor.execute(
            """
            INSERT INTO transactions
            (
                user_id,
                date,
                description,
                amount,
                type,
                category
            )
            VALUES
            (%s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                date,
                description,
                amount,
                transaction_type,
                category
            )
        )


        transaction_id = cursor.lastrowid


        # ==================================================
        # AI PREDICTION
        # ==================================================

        predicted_category = category
        confidence = 0.0


        if transaction_type == "Expense":

            description_vector = vectorizer.transform(
                [description]
            )

            predicted_category = model.predict(
                description_vector
            )[0]

            probabilities = model.predict_proba(
                description_vector
            )[0]

            confidence = float(
                max(probabilities) * 100
            )


            # Save AI prediction

            cursor.execute(
                """
                INSERT INTO predictions
                (
                    transaction_id,
                    predicted_category,
                    confidence
                )
                VALUES
                (%s, %s, %s)
                """,
                (
                    transaction_id,
                    predicted_category,
                    confidence
                )
            )


        connection.commit()

        cursor.close()
        connection.close()


        return redirect("/transactions")


    return render_template(
        "add_transaction.html"
    )


# ==================================================
# EDIT TRANSACTION
# ==================================================

@app.route(
    "/edit-transaction/<int:transaction_id>",
    methods=["GET", "POST"]
)
def edit_transaction(transaction_id):

    if "user_id" not in session:

        return redirect("/login")


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # Get transaction belonging to current user

    cursor.execute(
        """
        SELECT *
        FROM transactions
        WHERE transaction_id = %s
        AND user_id = %s
        """,
        (
            transaction_id,
            session["user_id"]
        )
    )

    transaction = cursor.fetchone()


    if not transaction:

        cursor.close()
        connection.close()

        return "Transaction not found."


    # ==================================================
    # UPDATE TRANSACTION
    # ==================================================

    if request.method == "POST":

        date = request.form["date"]
        description = request.form["description"]
        amount = request.form["amount"]
        transaction_type = request.form["type"]
        category = request.form["category"]


        # Validate amount

        try:

            amount = float(amount)

            if amount <= 0:

                return "Amount must be greater than zero."

        except ValueError:

            return "Invalid amount."


        # Update transaction

        cursor.execute(
            """
            UPDATE transactions
            SET
                date = %s,
                description = %s,
                amount = %s,
                type = %s,
                category = %s
            WHERE transaction_id = %s
            AND user_id = %s
            """,
            (
                date,
                description,
                amount,
                transaction_type,
                category,
                transaction_id,
                session["user_id"]
            )
        )


        # ==================================================
        # DELETE OLD AI PREDICTION
        # ==================================================

        cursor.execute(
            """
            DELETE FROM predictions
            WHERE transaction_id = %s
            """,
            (transaction_id,)
        )


        # ==================================================
        # CREATE NEW AI PREDICTION
        # ==================================================

        if transaction_type == "Expense":

            description_vector = vectorizer.transform(
                [description]
            )

            predicted_category = model.predict(
                description_vector
            )[0]

            probabilities = model.predict_proba(
                description_vector
            )[0]

            confidence = float(
                max(probabilities) * 100
            )


            cursor.execute(
                """
                INSERT INTO predictions
                (
                    transaction_id,
                    predicted_category,
                    confidence
                )
                VALUES
                (%s, %s, %s)
                """,
                (
                    transaction_id,
                    predicted_category,
                    confidence
                )
            )


        connection.commit()

        cursor.close()
        connection.close()


        return redirect("/transactions")


    cursor.close()
    connection.close()


    return render_template(
        "edit_transaction.html",
        transaction=transaction
    )


# ==================================================
# DELETE TRANSACTION
# ==================================================

@app.route(
    "/delete-transaction/<int:transaction_id>"
)
def delete_transaction(transaction_id):

    if "user_id" not in session:

        return redirect("/login")


    connection = get_db_connection()
    cursor = connection.cursor()


    # Delete AI prediction first

    cursor.execute(
        """
        DELETE FROM predictions
        WHERE transaction_id = %s
        AND transaction_id IN
        (
            SELECT transaction_id
            FROM transactions
            WHERE transaction_id = %s
            AND user_id = %s
        )
        """,
        (
            transaction_id,
            transaction_id,
            session["user_id"]
        )
    )


    # Delete transaction

    cursor.execute(
        """
        DELETE FROM transactions
        WHERE transaction_id = %s
        AND user_id = %s
        """,
        (
            transaction_id,
            session["user_id"]
        )
    )


    connection.commit()

    cursor.close()
    connection.close()


    return redirect("/transactions")


# ==================================================
# BUDGET
# ==================================================

@app.route(
    "/budget",
    methods=["GET", "POST"]
)
def budget():

    if "user_id" not in session:

        return redirect("/login")


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ==================================================
    # SAVE BUDGET
    # ==================================================

    if request.method == "POST":

        month = request.form["month"]
        category = request.form["category"]
        limit_amount = request.form["limit_amount"]


        # Validate budget amount

        try:

            limit_amount = float(limit_amount)

            if limit_amount <= 0:

                return "Budget amount must be greater than zero."

        except ValueError:

            return "Invalid budget amount."


        cursor.execute(
            """
            INSERT INTO budgets
            (
                user_id,
                month,
                category,
                limit_amount
            )
            VALUES
            (%s, %s, %s, %s)
            """,
            (
                session["user_id"],
                month,
                category,
                limit_amount
            )
        )


        connection.commit()


    # ==================================================
    # GET SAVED BUDGETS
    # ==================================================

    cursor.execute(
        """
        SELECT
            budget_id,
            month,
            category,
            limit_amount
        FROM budgets
        WHERE user_id = %s
        ORDER BY month DESC
        """,
        (session["user_id"],)
    )

    budgets = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "budget.html",
        budgets=budgets
    )


# ==================================================
# AI FINANCIAL INSIGHTS
# ==================================================

@app.route("/insights")
def insights():

    # Check whether user is logged in

    if "user_id" not in session:

        return redirect("/login")


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    user_id = session["user_id"]


    # ==================================================
    # TOTAL INCOME
    # ==================================================

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total_income
        FROM transactions
        WHERE user_id = %s
        AND type = 'Income'
        """,
        (user_id,)
    )

    income_result = cursor.fetchone()

    total_income = float(
        income_result["total_income"]
    )


    # ==================================================
    # TOTAL EXPENSES
    # ==================================================

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(amount), 0) AS total_expenses
        FROM transactions
        WHERE user_id = %s
        AND type = 'Expense'
        """,
        (user_id,)
    )

    expense_result = cursor.fetchone()

    total_expenses = float(
        expense_result["total_expenses"]
    )


    # ==================================================
    # BALANCE
    # ==================================================

    balance = total_income - total_expenses


    # ==================================================
    # HIGHEST SPENDING CATEGORY
    # ==================================================

    cursor.execute(
        """
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE user_id = %s
        AND type = 'Expense'
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
        """,
        (user_id,)
    )

    highest_category = cursor.fetchone()


    # ==================================================
    # CREATE INSIGHTS
    # ==================================================

    insight_list = []


    # Highest spending category insight

    if highest_category:

        category_name = highest_category["category"]

        category_amount = float(
            highest_category["total"]
        )

        insight_list.append(
            f"Your highest spending category is "
            f"{category_name}, with total spending of "
            f"₹{category_amount:.2f}."
        )


    # Expense percentage insight

    if total_income > 0:

        expense_percentage = (
            total_expenses / total_income
        ) * 100


        if expense_percentage >= 80:

            insight_list.append(
                "Your expenses are more than 80% "
                "of your income. Try to reduce "
                "unnecessary spending."
            )


        elif expense_percentage >= 50:

            insight_list.append(
                "Your expenses are more than 50% "
                "of your income. Keep monitoring "
                "your spending carefully."
            )


        else:

            insight_list.append(
                "Your expenses are below 50% "
                "of your income. You are "
                "maintaining a good saving level."
            )


    # Balance insight

    if balance < 0:

        insight_list.append(
            "Your expenses are higher than your "
            "income. Review your expenses and budget."
        )


    elif balance == 0 and total_income > 0:

        insight_list.append(
            "Your income and expenses are equal. "
            "Try to save some amount for future needs."
        )


    elif balance > 0:

        insight_list.append(
            f"Your current balance is "
            f"₹{balance:.2f}."
        )


    # ==================================================
    # SAVE INSIGHTS IN DATABASE
    # ==================================================

    cursor.execute(
        """
        DELETE FROM insights
        WHERE user_id = %s
        """,
        (user_id,)
    )


    for insight_text in insight_list:

        cursor.execute(
            """
            INSERT INTO insights
            (
                user_id,
                insight_text
            )
            VALUES
            (%s, %s)
            """,
            (
                user_id,
                insight_text
            )
        )


    connection.commit()


    # ==================================================
    # GET SAVED INSIGHTS
    # ==================================================

    cursor.execute(
        """
        SELECT
            insight_text,
            created_at
        FROM insights
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    insights_data = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "insights.html",
        insights=insights_data,
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance
    )


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    app.run(debug=True)