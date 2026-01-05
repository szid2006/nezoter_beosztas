from flask import Flask, render_template, request, redirect, url_for, session
from models import Worker, Role, Show
from datetime import datetime
from collections import defaultdict
import io
import csv
import os
import random

app = Flask(__name__)
app.secret_key = "titkos"

USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"

workers_list = []
shows_list = []

# ===== LOGIN =====
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
    return render_template("login.html")

# ===== DASHBOARD =====
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        workers_list.clear()
        shows_list.clear()

        # ===== WORKERS CSV =====
        workers_file = request.files.get("workers_csv")
        if workers_file:
            data = io.StringIO(workers_file.stream.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                worker = Worker(
                    name=row["name"].strip(),
                    wants_to_see=row.get("wants") or None,
                    is_ek=row.get("is_ek", "0") == "1"
                )
                unavailable = row.get("unavailable", "")
                for d in unavailable.split(","):
                    d = d.strip()
                    if d:
                        try:
                            worker.unavailable_dates.append(datetime.strptime(d, "%Y-%m-%d").date())
                        except ValueError:
                            pass
                workers_list.append(worker)

        # ===== SHOWS CSV =====
        shows_file = request.files.get("shows_csv")
        if shows_file:
            data = io.StringIO(shows_file.stream.read().decode("utf-8"))
            reader = csv.DictReader(data)
            for row in reader:
                dt = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M")
                need = int(row["need"])
                roles = [
                    Role("Nézőtér beülős", min(2, need)),
                    Role("Nézőtér csak csipog", min(2, max(0, need - 2))),
                    Role("Jolly joker", 1 if need >= 5 else 0, ek_allowed=False),
                    Role("Ruhatár bal", min(2, max(0, need - 5))),
                    Role("Ruhatár jobb", 1 if need >= 8 else 0),
                    Role("Ruhatár erkély", 1 if need >= 9 else 0),
                ]
                roles = [r for r in roles if r.max_count > 0]
                shows_list.append(Show(row["title"], dt, roles))

        return redirect(url_for("schedule"))

    return render_template("dashboard.html")

# ===== GENERATE SCHEDULE =====
def generate_schedule(workers, shows):
    schedule_result = defaultdict(lambda: defaultdict(list))

    for show in sorted(shows, key=lambda s: s.start):
        used_today = set()
        ek_assigned = False
        assigned_total = 0
        need_total = sum(role.max_count for role in show.roles)

        # Lapított szereplista, hogy könnyebb legyen kiosztani
        role_slots = []
        for role in show.roles:
            for _ in range(role.max_count):
                role_slots.append(role)

        random.shuffle(role_slots)  # rotáció miatt

        for role in role_slots:
            if assigned_total >= need_total:
                break

            # Eligible dolgozók kiválasztása
            eligible = []
            for w in workers:
                if w.name in used_today:
                    continue
                if w.is_ek and ek_assigned:
                    continue  # csak 1 ÉK a műszakban
                if show.start.date() in w.unavailable_dates:
                    continue
                recent = getattr(w, "previous_roles", [])
                if recent and (show.start.date() - max(recent, default=show.start.date())).days < 3:
                    continue
                eligible.append(w)

            if not eligible:
                continue

            # Prefer non-ÉK, kevesebbet beosztott dolgozók először
            eligible.sort(key=lambda w: (w.is_ek, getattr(w, "assigned_count", 0)))
            chosen = eligible[0]

            # Beosztás
            name_display = f"{chosen.name} (ÉK)" if chosen.is_ek else chosen.name
            schedule_result[show.title][role.name].append(name_display)

            # Frissítés
            used_today.add(chosen.name)
            assigned_total += 1
            if chosen.is_ek:
                ek_assigned = True
            if not hasattr(chosen, "assigned_count"):
                chosen.assigned_count = 0
            chosen.assigned_count += 1
            if not hasattr(chosen, "previous_roles"):
                chosen.previous_roles = []
            chosen.previous_roles.append(show.start.date())

    return schedule_result

# ===== SCHEDULE ROUTE =====
@app.route("/schedule")
def schedule():
    schedule_dict = generate_schedule(workers_list, shows_list)
    return render_template("schedule.html", schedule=schedule_dict)

# ===== EXPORT CSV =====
@app.route("/export_csv")
def export_csv():
    return "CSV export még nincs implementálva, de a schedule oldal működik."

# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
