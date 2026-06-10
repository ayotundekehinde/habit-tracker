"""Habit Tracker API with user accounts."""

import os
import sqlite3
import uuid
from datetime import UTC, date, datetime, timedelta
from functools import wraps
from pathlib import Path

import jwt
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "dev-secret-change-in-production-use-32-chars-min"
)
DB_PATH = Path(__file__).parent / "habit_tracker.db"
TOKEN_HOURS = 24 * 7

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS completions (
                habit_id TEXT NOT NULL,
                completed_date TEXT NOT NULL,
                PRIMARY KEY (habit_id, completed_date),
                FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                theme TEXT NOT NULL DEFAULT 'light',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def create_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(UTC) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401
        payload = decode_token(auth[7:])
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.user_id = payload["sub"]
        request.username = payload["username"]
        return f(*args, **kwargs)

    return wrapper


def habit_to_dict(row: sqlite3.Row, completed_dates: list[str]) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "completedDates": completed_dates,
    }


def fetch_user_habits(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    habits = conn.execute(
        "SELECT id, name, category FROM habits WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    ).fetchall()

    result = []
    for habit in habits:
        dates = conn.execute(
            "SELECT completed_date FROM completions WHERE habit_id = ? ORDER BY completed_date",
            (habit["id"],),
        ).fetchall()
        result.append(
            habit_to_dict(habit, [row["completed_date"] for row in dates])
        )
    return result


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(".", path)


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    created_at = datetime.now(UTC).isoformat()

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user_id, username, password_hash, created_at),
            )
            conn.execute(
                "INSERT INTO user_preferences (user_id, theme) VALUES (?, ?)",
                (user_id, "light"),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already taken"}), 409

    token = create_token(user_id, username)
    return jsonify({"token": token, "username": username, "theme": "light"}), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid username or password"}), 401

        prefs = conn.execute(
            "SELECT theme FROM user_preferences WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        theme = prefs["theme"] if prefs else "light"

    token = create_token(user["id"], user["username"])
    return jsonify({"token": token, "username": user["username"], "theme": theme})


@app.get("/api/me")
@require_auth
def me():
    with get_db() as conn:
        prefs = conn.execute(
            "SELECT theme FROM user_preferences WHERE user_id = ?",
            (request.user_id,),
        ).fetchone()
    return jsonify({
        "username": request.username,
        "theme": prefs["theme"] if prefs else "light",
    })


@app.get("/api/habits")
@require_auth
def list_habits():
    with get_db() as conn:
        habits = fetch_user_habits(conn, request.user_id)
    return jsonify({"habits": habits})


@app.post("/api/habits")
@require_auth
def create_habit():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "other").strip()

    if not name:
        return jsonify({"error": "Habit name is required"}), 400

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM habits WHERE user_id = ? AND LOWER(name) = LOWER(?)",
            (request.user_id, name),
        ).fetchone()
        if existing:
            return jsonify({"error": "Habit already exists"}), 409

        habit_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO habits (id, user_id, name, category, created_at) VALUES (?, ?, ?, ?, ?)",
            (habit_id, request.user_id, name, category, datetime.now(UTC).isoformat()),
        )
        conn.commit()
        habit = conn.execute(
            "SELECT id, name, category FROM habits WHERE id = ?",
            (habit_id,),
        ).fetchone()

    return jsonify(habit_to_dict(habit, [])), 201


@app.post("/api/habits/<habit_id>/toggle")
@require_auth
def toggle_habit(habit_id: str):
    today = date.today().isoformat()

    with get_db() as conn:
        habit = conn.execute(
            "SELECT id, name, category FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, request.user_id),
        ).fetchone()
        if not habit:
            return jsonify({"error": "Habit not found"}), 404

        existing = conn.execute(
            "SELECT completed_date FROM completions WHERE habit_id = ? AND completed_date = ?",
            (habit_id, today),
        ).fetchone()

        if existing:
            conn.execute(
                "DELETE FROM completions WHERE habit_id = ? AND completed_date = ?",
                (habit_id, today),
            )
        else:
            conn.execute(
                "INSERT INTO completions (habit_id, completed_date) VALUES (?, ?)",
                (habit_id, today),
            )
        conn.commit()

        dates = conn.execute(
            "SELECT completed_date FROM completions WHERE habit_id = ? ORDER BY completed_date",
            (habit_id,),
        ).fetchall()

    return jsonify(habit_to_dict(habit, [row["completed_date"] for row in dates]))


@app.delete("/api/habits/<habit_id>")
@require_auth
def delete_habit(habit_id: str):
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, request.user_id),
        )
        conn.commit()
        if result.rowcount == 0:
            return jsonify({"error": "Habit not found"}), 404
    return jsonify({"ok": True})


@app.post("/api/habits/import")
@require_auth
def import_habits():
    data = request.get_json(silent=True) or {}
    habits = data.get("habits") or []
    if not isinstance(habits, list):
        return jsonify({"error": "Invalid habits data"}), 400

    imported = 0
    with get_db() as conn:
        for item in habits:
            name = (item.get("name") or "").strip()
            category = (item.get("category") or "other").strip()
            if not name:
                continue

            existing = conn.execute(
                "SELECT id FROM habits WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                (request.user_id, name),
            ).fetchone()
            if existing:
                continue

            habit_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO habits (id, user_id, name, category, created_at) VALUES (?, ?, ?, ?, ?)",
                (habit_id, request.user_id, name, category, datetime.now(UTC).isoformat()),
            )

            for completed in item.get("completedDates") or []:
                if isinstance(completed, str) and len(completed) == 10:
                    conn.execute(
                        "INSERT OR IGNORE INTO completions (habit_id, completed_date) VALUES (?, ?)",
                        (habit_id, completed),
                    )
            imported += 1

        conn.commit()
        all_habits = fetch_user_habits(conn, request.user_id)

    return jsonify({"imported": imported, "habits": all_habits})


@app.put("/api/preferences")
@require_auth
def update_preferences():
    data = request.get_json(silent=True) or {}
    theme = data.get("theme", "light")
    if theme not in ("light", "dark"):
        theme = "light"

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (user_id, theme) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET theme = excluded.theme
            """,
            (request.user_id, theme),
        )
        conn.commit()

    return jsonify({"theme": theme})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
