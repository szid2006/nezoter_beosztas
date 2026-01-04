from flask import Flask, render_template, request, redirect, url_for, session
from models import Worker, Role, Show
from datetime import datetime, timedelta
from collections import defaultdict
import csv
import io
import os
import random

app = Flask(__name__)
app.secret_key = "titkos"

USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"

workers_list = []
shows_list = []


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
    return render_template("login.html")


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
                    wants=row.get("wants") or None,
                    is_ek=row.get("is_ek", "0") == "1"
                )

                unavailable = row.get("unavailable", "")
                for d in unavailable.split(","):
                    d = d.strip()
                    if d:
                        try:
                            worker.unavailable_dates.append(
                                datetime.strptime(d, "%Y-%m-%d").date()
                            )
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


def generate_schedule(workers, shows):
    result = defaultdict(lambda: defaultdict(list))
    assignment_count = defaultdict(int)
    last_assigned = defaultdict(list)

    shows_sorted = sorted(shows, key=lambda s: s.start)

    for show in shows_sorted:
        used_today = set()
        ek_used = 0

        for role in show.roles:
            eligible = []

            for w in workers:
                if w.name in used_today:
                    continue
                if w.is_ek and ek_used >= 1:
                    continue
                if not role.ek_allowed and w.is_ek:
                    continue
                if show.start.date() in w.unavailable_dates:
                    continue

                recent = last_assigned[w.name]
                if recent and (show.start.date() - max(recent)).days < 3:
                    continue

                eligible.append(w)

            eligible.sort(key=lambda w: (w.is_ek, assignment_count[w.name]))
            chosen = eligible[:role.max_count]

            for w in chosen:
                result[show.title][role.name].append(w.name)
                assignment_count[w.name] += 1
                used_today.add(w.name)
                last_assigned[w.name].append(show.start.date())
                if w.is_ek:
                    ek_used += 1

    return result


@app.route("/schedule")
def schedule():
    schedule = generate_schedule(workers_list, shows_list)
    return render_template("schedule.html", schedule=schedule)


# ===== RENDER KOMPATIBILIS INDÍTÁS =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
