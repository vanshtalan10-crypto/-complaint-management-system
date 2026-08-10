from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "complaint_management_secret_key"

DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column["name"] for column in cursor.fetchall()]

    if "student_id" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN student_id TEXT"
        )

    if "course" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN course TEXT"
        )

    if "section" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN section TEXT"
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cursor.execute("PRAGMA table_info(complaints)")
    complaint_columns = [
        column["name"] for column in cursor.fetchall()
    ]

    if "complaint_date" not in complaint_columns:
        cursor.execute(
            "ALTER TABLE complaints ADD COLUMN complaint_date TEXT"
        )

    if "complaint_time" not in complaint_columns:
        cursor.execute(
            "ALTER TABLE complaints ADD COLUMN complaint_time TEXT"
        )

    conn.commit()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        ("admin@gmail.com",)
    )

    admin = cursor.fetchone()

    if not admin:
        cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password,
                student_id,
                course,
                section
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Admin",
            "admin@gmail.com",
            "admin123",
            "ADMIN",
            "ADMIN",
            "ADMIN"
        ))

        conn.commit()

    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        course = request.form.get("course", "").strip()
        section = request.form.get("section", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not name:
            return """
            <h2>Registration Error</h2>
            <p>Student Name cannot be empty.</p>
            <a href="/register">Go Back</a>
            """

        if not student_id:
            return """
            <h2>Registration Error</h2>
            <p>Student ID cannot be empty.</p>
            <a href="/register">Go Back</a>
            """

        if not course:
            return """
            <h2>Registration Error</h2>
            <p>Course cannot be empty.</p>
            <a href="/register">Go Back</a>
            """

        if not section:
            return """
            <h2>Registration Error</h2>
            <p>Section cannot be empty.</p>
            <a href="/register">Go Back</a>
            """

        if not email:
            return """
            <h2>Registration Error</h2>
            <p>Email cannot be empty.</p>
            <a href="/register">Go Back</a>
            """

        if not password:
            return """
            <h2>Registration Error</h2>
            <p>Password cannot be empty.</p>
            <a href="/register">Go Back</a>
            """

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM users
            WHERE LOWER(student_id) = LOWER(?)
        """, (student_id,))

        if cursor.fetchone():
            conn.close()
            return """
            <h2>Registration Error</h2>
            <p>Student ID already registered.</p>
            <a href="/register">Try Again</a>
            """

        cursor.execute("""
            SELECT id
            FROM users
            WHERE LOWER(email) = LOWER(?)
        """, (email,))

        if cursor.fetchone():
            conn.close()
            return """
            <h2>Registration Error</h2>
            <p>Email already registered.</p>
            <a href="/register">Try Again</a>
            """

        try:

            cursor.execute("""
                INSERT INTO users
                (
                    name,
                    student_id,
                    course,
                    section,
                    email,
                    password
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                student_id,
                course,
                section,
                email,
                password
            ))

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.close()

            return """
            <h2>Registration Error</h2>
            <p>Email or Student ID is already registered.</p>
            <a href="/register">Try Again</a>
            """

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM users
            WHERE LOWER(email) = ?
            AND password = ?
        """, (
            email,
            password
        ))

        user = cursor.fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["student_id"] = user["student_id"] or ""
            session["course"] = user["course"] or ""
            session["section"] = user["section"] or ""

            if email == "admin@gmail.com":
                session["admin"] = True
                return redirect(url_for("admin"))

            session["admin"] = False

            return redirect(url_for("dashboard"))

        return """
        <h3>Invalid email or password.</h3>
        <a href="/login">Try Again</a>
        """

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM complaints
        WHERE email = ?
        ORDER BY id DESC
    """, (
        session["email"],
    ))

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        complaints=complaints
    )


@app.route("/complaint", methods=["GET", "POST"])
def complaint():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        subject = request.form.get("subject", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not subject:
            return """
            <h2>Complaint Error</h2>
            <p>Subject cannot be empty.</p>
            <a href="/complaint">Go Back</a>
            """

        if not category:
            return """
            <h2>Complaint Error</h2>
            <p>Category cannot be empty.</p>
            <a href="/complaint">Go Back</a>
            """

        if not description:
            return """
            <h2>Complaint Error</h2>
            <p>Description cannot be empty.</p>
            <a href="/complaint">Go Back</a>
            """

        now = datetime.now()

        complaint_date = now.strftime("%d-%m-%Y")
        complaint_time = now.strftime("%I:%M %p")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO complaints
            (
                name,
                email,
                subject,
                category,
                description,
                status,
                complaint_date,
                complaint_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["name"],
            session["email"],
            subject,
            category,
            description,
            "Pending",
            complaint_date,
            complaint_time
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("complaint.html")


@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if not session.get("admin"):
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM complaints
        ORDER BY id DESC
    """)

    complaints = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        complaints=complaints
    )


@app.route("/update_status/<int:complaint_id>", methods=["POST"])
def update_status(complaint_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if not session.get("admin"):
        return redirect(url_for("dashboard"))

    status = request.form.get(
        "status",
        "Pending"
    ).strip()

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved",
        "Rejected"
    ]

    if status not in allowed_statuses:
        status = "Pending"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE complaints
        SET status = ?
        WHERE id = ?
    """, (
        status,
        complaint_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )