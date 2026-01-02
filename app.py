from flask import Flask, render_template, request, redirect, url_for, session
from models import Worker, Role, Show
from main import generate_schedule
from datetime import datetime

app = Flask(__name__)
app.secret_key = "titkos"

USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"
USERNAME = "Szabó Szidónia"
PASSWORD = "12345"

workers_list = []
shows_list = []

# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form["username"] == USERNAME
            and request.form["password"] == PASSWORD
        ):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
    return render_template("login.html")


# ─────────────────────────────
# DASHBOARD
# ─────────────────────────────
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        workers_list.clear()
        shows_list.clear()

        # ───────── DOLGOZÓK ─────────
        num_workers = int(request.form.get("num_workers", 0))

        for i in range(num_workers):
            name = request.form.get(f"name_{i}")
            wants = request.form.get(f"wants_{i}") or None
            is_ek = request.form.get(f"ek_{i}") == "on"
            raw = request.form.get(f"unavail_{i}", "")

            worker = Worker(name, wants, is_ek)

            # 👉 CSAK: YYYY-MM-DD, YYYY-MM-DD
            if raw:
                days = [d.strip() for d in raw.split(",") if d.strip()]
                for d in days:
                    date_obj = datetime.strptime(d, "%Y-%m-%d").date()
                    worker.unavailable_dates.append(date_obj)

            workers_list.append(worker)

        # ───────── MŰSZAKOK / ELŐADÁSOK ─────────
        num_shows = int(request.form.get("num_shows", 0))

        for j in range(num_shows):
            title = request.form.get(f"title_{j}")
            dt = datetime.strptime(
                request.form.get(f"date_{j}"), "%Y-%m-%d %H:%M"
            )
            need = int(request.form.get(f"need_{j}", 10))

            roles = [
                Role("Nézőtér beülős", min(2, need)),
                Role("Nézőtér csak csipog", min(2, max(0, need - 2))),
                Role("Jolly joker", 1 if need >= 5 else 0, ek_allowed=False),
                Role("Ruhatár bal", min(2, max(0, need - 5))),
                Role("Ruhatár jobb", 1 if need >= 7 else 0),
                Role("Ruhatár erkély", 1 if need >= 8 else 0),
            ]

            roles = [r for r in roles if r.max_count > 0]
            shows_list.append(Show(title, dt, roles))

        return redirect(url_for("schedule"))

    return render_template("dashboard.html")


# ─────────────────────────────
# BEOSZTÁS
# ─────────────────────────────
@app.route("/schedule")
def schedule():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    result = generate_schedule(workers_list, shows_list)
    return render_template("schedule.html", schedule=result)


if __name__ == "__main__":
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

