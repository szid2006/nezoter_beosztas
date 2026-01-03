from flask import Flask, render_template, request, redirect, url_for, session, Response
from datetime import datetime
import os
import traceback
import random
from collections import defaultdict

# ─────────────────────────────
# MODELLEK
# ─────────────────────────────
class Worker:
    def __init__(self, name, wants_to_see=None, is_ek=False):
        self.name = name
        self.wants_to_see = wants_to_see
        self.is_ek = is_ek
        self.unavailable_dates = []
        self.weight = 1  # alap: normál dolgozó

class Role:
    def __init__(self, name, max_count, ek_allowed=True):
        self.name = name
        self.max_count = max_count
        self.ek_allowed = ek_allowed

class Show:
    def __init__(self, title, date, roles):
        self.title = title
        self.date = date
        self.roles = roles

# ─────────────────────────────
# GENERATE SCHEDULE
# ─────────────────────────────
def generate_schedule(workers, shows):
    schedule = defaultdict(dict)
    assigned_by_date = defaultdict(list)  # dátum -> list of assigned workers

    for show in shows:
        for role in show.roles:
            # Elérhető dolgozók a dátumra
            available = [w for w in workers if show.date.date() not in w.unavailable_dates]

            # Max 1 ÉK/nap
            num_ek_today = sum(1 for w in assigned_by_date[show.date.date()] if w.is_ek)
            if num_ek_today >= 1:
                available = [w for w in available if not w.is_ek]

            # Súlyozás: ÉK ritkábban
            weighted = []
            for w in available:
                count = max(int(w.weight * 10), 1)  # weight 1->10, 0.2->2
                weighted.extend([w] * count)

            if not weighted:
                schedule[show.title][role.name] = []
                continue

            assign_count = min(role.max_count, len(weighted))
            assigned = random.sample(weighted, assign_count)

            schedule[show.title][role.name] = [w.name for w in assigned]
            assigned_by_date[show.date.date()].extend(assigned)

    return schedule

# ─────────────────────────────
# FLASK APP
# ─────────────────────────────
app = Flask(__name__)
app.secret_key = "titkos"

USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"

workers_list = []
shows_list = []

# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
    return render_template("login.html")

# ─────────────────────────────
# DASHBOARD (manuális bevitel)
# ─────────────────────────────
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        workers_list.clear()
        shows_list.clear()

        # Dolgozók
        num_workers = int(request.form.get("num_workers", 0))
        for i in range(num_workers):
            name = request.form.get(f"name_{i}")
            if not name:
                continue

            wants = request.form.get(f"wants_{i}") or None
            is_ek = f"ek_{i}" in request.form
            raw = request.form.get(f"unavail_{i}", "")

            worker = Worker(name, wants, is_ek)
            worker.weight = 0.2 if is_ek else 1

            if raw:
                for d in raw.split(","):
                    try:
                        worker.unavailable_dates.append(datetime.strptime(d.strip(), "%Y-%m-%d").date())
                    except ValueError:
                        pass

            workers_list.append(worker)

        # Előadások
        num_shows = int(request.form.get("num_shows", 0))
        for j in range(num_shows):
            title = request.form.get(f"title_{j}")
            raw_dt = request.form.get(f"date_{j}")
            try:
                dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M")
            except Exception:
                continue

            need = int(request.form.get(f"need_{j}", 10))
            roles = [
                Role("Nézőtér beülős", min(2, need)),
                Role("Nézőtér csak csipog", min(2, max(0, need - 2))),
                Role("Jolly joker", 1 if need >= 5 else 0, ek_allowed=False),
                Role("Ruhatár bal", min(2, max(0, need - 5))),
                Role("Ruhatár jobb", 1 if need >= 8 else 0),
                Role("Ruhatár erkély", 1 if need >= 9 else 0),
            ]
            roles = [r for r in roles if r.max_count > 0]
            shows_list.append(Show(title, dt, roles))

        return redirect(url_for("schedule"))

    return render_template("dashboard.html")

# ─────────────────────────────
# SCHEDULE
# ─────────────────────────────
@app.route("/schedule")
def schedule():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    try:
        result = generate_schedule(workers_list, shows_list)
        return render_template("schedule.html", schedule=result)
    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>", 500

# ─────────────────────────────
# CSV EXPORT
# ─────────────────────────────
@app.route("/export/csv")
def export_csv():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    result = generate_schedule(workers_list, shows_list)

    def generate():
        yield "Előadás;Szerep;Dolgozók\n"
        for show_title, roles in result.items():
            for role, names in roles.items():
                yield f"{show_title};{role};{', '.join(names)}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=beosztas.csv"}
    )

# ─────────────────────────────
# START
# ─────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
