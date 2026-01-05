from flask import Flask, render_template, request, redirect, url_for, session
from models import Worker, Role, Show
from datetime import datetime
from collections import defaultdict
import csv, io, os

app = Flask(__name__)
app.secret_key = "titkos"

USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"

workers_list = []
shows_list = []

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        workers_list.clear()
        shows_list.clear()

        # ---------- WORKERS ----------
        wf = request.files["workers_csv"]
        data = io.StringIO(wf.stream.read().decode("utf-8"))
        for row in csv.DictReader(data):
            w = Worker(
                name=row["name"].strip(),
                wants_to_see=row.get("wants") or None,
                is_ek=row.get("is_ek", "0") == "1"
            )
            for d in row.get("unavailable", "").split(","):
                if d.strip():
                    w.unavailable_dates.append(
                        datetime.strptime(d.strip(), "%Y-%m-%d").date()
                    )
            workers_list.append(w)

        # ---------- SHOWS ----------
        sf = request.files["shows_csv"]
        data = io.StringIO(sf.stream.read().decode("utf-8"))
        for row in csv.DictReader(data):
            dt = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M")
            need = int(row["need"])

            roles = []
            roles += [Role("Nézőtér beülős", 1) for _ in range(min(2, need))]
            roles += [Role("Nézőtér csak csipog", 1) for _ in range(min(2, max(0, need-2)))]
            if need >= 5:
                roles.append(Role("Jolly joker", 1, ek_allowed=False))
            roles += [Role("Ruhatár bal", 1) for _ in range(min(2, max(0, need-5)))]
            if need >= 8:
                roles.append(Role("Ruhatár jobb", 1))
            if need >= 9:
                roles.append(Role("Ruhatár erkély", 1))

            shows_list.append(Show(row["title"], dt, roles[:need]))

        return redirect(url_for("schedule"))

    return render_template("dashboard.html")

# ================= SCHEDULER =================
def generate_schedule(workers, shows):
    result = defaultdict(lambda: defaultdict(list))

    for show in sorted(shows, key=lambda s: s.start):
        assigned = set()
        ek_used = False
        assigned_count = 0
        need = len(show.roles)

        for role in show.roles:
            if assigned_count >= need:
                break  # 🔴 KRITIKUS STOP

            eligible = []
            for w in workers:
                if w.name in assigned:
                    continue
                if show.start.date() in w.unavailable_dates:
                    continue
                if w.is_ek and ek_used:
                    continue
                eligible.append(w)

            if not eligible:
                continue

            # nem ÉK előnyben + rotáció
            eligible.sort(key=lambda w: (w.is_ek, w.assigned_count))
            chosen = eligible[0]

            name = chosen.name + (" (ÉK)" if chosen.is_ek else "")
            result[show.title][role.name].append(name)

            assigned.add(chosen.name)
            assigned_count += 1
            chosen.assigned_count += 1

            if chosen.is_ek:
                ek_used = True

        # 🔒 VÉGSŐ BIZTOSÍTÉK
        assert assigned_count <= need

    return result

# ================= ROUTES =================
@app.route("/schedule")
def schedule():
    return render_template(
        "schedule.html",
        schedule=generate_schedule(workers_list, shows_list)
    )

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
