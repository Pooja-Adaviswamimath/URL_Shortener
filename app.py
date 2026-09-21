
from flask import Flask, render_template, request, redirect, abort, url_for
import string
import random
import sqlite3

app = Flask(__name__)

def generate_short_code():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k = 6))

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            short_code TEXT UNIQUE NOT NULL
        )
    """)

    columns = conn.execute("PRAGMA table_info(urls)").fetchall()
    column_names = [column["name"] for column in columns]

    if "clicks" not in column_names:
        conn.execute(
            "ALTER TABLE urls ADD COLUMN clicks INTEGER DEFAULT 0"
        )

    conn.commit()
    conn.close()



@app.route("/", methods = ["GET", "POST"])
def home():

    short_url = None

    if request.method == "POST":
        long_url = request.form["long_url"].strip()

        if not long_url.startswith(("http://", "https://")):
            return render_template(
                "index.html",
                error = "Please enter a valid URL starting eith http:// or https://",
                long_url=long_url
            )
        custom_code = request.form.get("custom_code", "").strip()

        if custom_code:
            short_code = custom_code

            conn = get_db_connection()

            existing_url = conn.execute(
                "SELECT id FROM urls WHERE short_code = ?",
                (short_code,)
            ).fetchone()

            if existing_url:
                conn.close()

                return render_template(
                    "index.html",
                    error = "This short code is already taken. Please choose another one.",
                    long_url = long_url,
                    custom_code = custom_code
                )
        else:
            short_code = generate_short_code()

            conn = get_db_connection()

        conn.execute(
            "INSERT INTO urls (original_url, short_code) VALUES (?, ?)",
            (long_url, short_code)
        )

        conn.commit()
        conn.close()

        short_url = url_for(
            "redirect_url",
            short_code = short_code,
            _external = True
        )


    return render_template(
        "index.html", 
        short_url = short_url
    )

@app.route("/history")
def history():

    conn = get_db_connection()

    urls = conn.execute(
        "SELECT * FROM urls ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "history.html", 
        urls = urls
    )

@app.route("/delete/<short_code>", methods = ["POST"])
def delete_url(short_code):

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM urls WHERE short_code = ?",
        (short_code,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()

    total_urls = conn.execute(
        "SELECT COUNT(*) FROM urls"
    ).fetchone()[0]

    total_clicks = conn.execute(
        "SELECT SUM(clicks) FROM urls"
    ).fetchone()[0]

    most_clicked = conn.execute(
        "SELECT * FROM urls ORDER BY clicks DESC LIMIT 1"
    ).fetchone()

    all_urls = conn.execute(
        "SELECT * FROM urls ORDER BY clicks DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_urls = total_urls,
        total_clicks = total_clicks or 0,
        most_clicked = most_clicked,
        all_urls=all_urls

    )

@app.route("/<short_code>")
def redirect_url(short_code):
    conn = get_db_connection()

    url = conn.execute(
        "SELECT * FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()

    if url is None:
        conn.close()
        abort(404)

    conn.execute(
        "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?",
        (short_code,)
    )

    conn.commit()
    conn.close()

    return redirect(url["original_url"])

def update_database():
    conn = get_db_connection()

    conn.execute(
        "ALTER TABLE urls ADD COLUMN clicks INTEGER DEFAULT 0"

    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    app.run(debug = True)