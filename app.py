from flask import Flask, render_template, request, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
EMAIL_ADDRESS = "sairakshivinju@gmail.com"
EMAIL_PASSWORD = "hello"

app = Flask(__name__)
app.secret_key = "todo_secret"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------- DATABASE ----------------
def get_db():
    db_path = app.config.get("DATABASE", "todo.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_users_table():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except:
        pass  # column already exists

    conn.commit()
    conn.close()


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            status TEXT,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()
def migrate_tasks_table():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
    except:
        pass  # column may already exist

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'Medium'")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN reminder_sent INTEGER DEFAULT 0")
    except:
        pass

    conn.commit()
    conn.close()

init_db()
migrate_tasks_table()
migrate_users_table()


# ---------------- LOGIN ----------------
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user["id"], user["username"], user["password"])
    return None


def send_email(to_email, task_title, due_date):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = "⏰ Task Overdue Reminder"

    body = f"""
    Hello,

    Your task "{task_title}" was due on {due_date}
    and is still marked as pending.

    Please complete it as soon as possible.

    — To-Do Application
    """
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
def check_overdue_tasks():
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d")

    tasks = conn.execute("""
        SELECT tasks.id, tasks.title, tasks.due_date, users.email
        FROM tasks
        JOIN users ON tasks.user_id = users.id
        WHERE tasks.status='Pending'
        AND tasks.due_date < ?
        AND tasks.reminder_sent = 0
    """, (now,)).fetchall()

    for task in tasks:
        send_email(task["email"], task["title"], task["due_date"])
        conn.execute(
            "UPDATE tasks SET reminder_sent = 1 WHERE id = ?",
            (task["id"],)
        )

    conn.commit()
    conn.close()
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(check_overdue_tasks, 'interval', minutes=1)
if not app.config.get("TESTING"):
    scheduler.start()


# ---------------- ROUTES ----------------
@app.route("/")
@login_required
def index():
    status = request.args.get("status")
    priority = request.args.get("priority")
    overdue = request.args.get("overdue")

    query = "SELECT * FROM tasks WHERE user_id=?"
    params = [current_user.id]

    if status:
        query += " AND status=?"
        params.append(status)

    if priority:
        query += " AND priority=?"
        params.append(priority)

    if overdue == "yes":
        today = datetime.now().strftime("%Y-%m-%d")
        query += " AND due_date < ? AND status='Pending'"
        params.append(today)

    conn = get_db()
    tasks = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("index.html", tasks=tasks)
@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form["title"]
    conn = get_db()
    conn.execute(
        "INSERT INTO tasks (title, status, user_id) VALUES (?, ?, ?)",
        (title, "Pending", current_user.id),
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    conn = get_db()
    if request.method == "POST":
        status = request.form["status"]
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, id))
        conn.commit()
        conn.close()
        return redirect("/")
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("edit_task.html", task=task)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        conn = get_db()
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        flash("Registered successfully")
        return redirect("/login")
    return render_template("register.html")

@app.route("/analytics")
@login_required
def analytics():
    conn = get_db()

    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='Completed' AND user_id=?",
        (current_user.id,)
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='Pending' AND user_id=?",
        (current_user.id,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "analytics.html",
        completed=completed,
        pending=pending
    )




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            login_user(User(user["id"], user["username"], user["password"]))
            return redirect("/")
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id=?",
        (current_user.id,)
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='Completed' AND user_id=?",
        (current_user.id,)
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='Pending' AND user_id=?",
        (current_user.id,)
    ).fetchone()[0]

    conn.close()

    completion_rate = 0
    if total > 0:
        completion_rate = int((completed / total) * 100)

    return render_template(
        "dashboard.html",
        total=total,
        completed=completed,
        pending=pending,
        completion_rate=completion_rate
    )


if __name__ == "__main__":
    app.run(debug=True)
