from flask import Flask, render_template, request, redirect, url_for, session, Response
from models import Worker, Role, Show
from datetime import datetime
from collections import defaultdict
import random
import os
import traceback

app = Flask(__name__)
app.secret_key = "titkos"

# ─────────────────────────────
# BELÉPÉSI ADATOK
# ─────────────────────────────
USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"

# ─────────────────────────────
# ADATTÁROLÁS
# ─────────────────────────────
workers_list = []
shows_list = []

# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == USERNAME
            and request.form.get("password") == PASSWORD
        ):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
    return render_template("login.html")

# ─────────────────────────────
# DASHBOARD (csak manuális bevitel)
# ─────────────────────────────
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        workers_list.clear()
        shows_list.clear()

        # ───── DOLGOZÓK ─────
        num_workers = int(request.form.get("num_workers", 0))
        for i in range(num_workers):
            name = request.form.get(f"name_{i}")
            if not name:
                continue

            wants = request.form.get(f"wants_{i}") or None
            is_ek = f"ek_{i}" in request.form
            raw = request.form.get(f"unavail_{i}", "")

            worker = Worker(name, wants, is_ek)
            if raw:
                for d in raw.split(","):
                    try:
                        worker.unavailable_dates.append(
                            datetime.strptime(d.strip(), "%Y-%m-%d").date()
                        )
                    except ValueError:
                        pass

            workers_list.append(worker)

        # ───── ELŐADÁSOK ─────
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
# BEOSZTÁS GENERÁLÁS
# ─────────────────────────────
def generate_schedule(workers, shows):
    schedule = defaultdict(dict)
    assigned_by_date = defaultdict(list)  # dátum -> list of assigned workers
    last_assigned_dates = {w: [] for w in workers}  # dolgozó -> list of dátumok

    # Súlyozás: ÉK dolgozók ritkábban
    for worker in workers:
        worker.weight = 0.2 if worker.is_ek else 1

    shows_sorted = sorted(shows, key=lambda s: s.dt)  # időrend

    for show in shows_sorted:
        assigned_in_show = set()  # már beosztott a show-on belül

        for role in show.roles:
            # Elérhető dolgozók a dátumra, akik még nem kaptak szerepet a show-on
            available = [
                w for w in workers
                if show.dt.date() not in w.unavailable_dates
                and w not in assigned_in_show
            ]

            # Max 1 ÉK/nap
            num_ek_today = sum(1 for w in assigned_by_date[show.dt.date()] if w.is_ek)
            if num_ek_today >= 1:
                available = [w for w in available if not w.is_ek]

            # Max 3 egymás utáni nap
            filtered = []
            for w in available:
                last_dates = sorted(last_assigned_dates[w])
                if len(last_dates) < 3:
                    filtered.append(w)
                    continue
                # Ellenőrzés: utolsó 3 nap egymás után
                if (last_dates[-1] - last_dates[-2]).days == 1 and (last_dates[-2] - last_dates[-3]).days == 1:
                    continue
                filtered.append(w)
            available = filtered

            # Súlyozás: ÉK ritkábban
            weighted = []
            for w in available:
                count = max(int(w.weight * 10), 1)
                weighted.extend([w] * count)

            if not weighted:
                schedule[show.title][role.name] = []
                continue

            assign_count = min(role.max_count, len(weighted))
            assigned = random.sample(weighted, assign_count)

            # Tárolás
            schedule[show.title][role.name] = [w.name for w in assigned]
            assigned_by_date[show.dt.date()].extend(assigned)
            assigned_in_show.update(assigned)

            # Frissítjük az utolsó beosztott dátumokat
            for w in assigned:
                last_assigned_dates[w].append(show.dt.date())

    return schedule

# ─────────────────────────────
# BEOSZTÁS ROUTE
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
