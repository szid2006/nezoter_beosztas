from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import csv
import io
import traceback

# ====== APP ======
app = Flask(__name__)
app.secret_key = "titkos"

# ====== LOGIN ======
USERNAME = "Szakács Zsuzsi"
PASSWORD = "1234"

# ====== DATA ======
workers_list = []
shows_list = []

# ====== MODELS (ha nincs külön models.py, itt legyenek) ======
class Worker:
    def __init__(self, name, wants=None, is_ek=False):
        self.name = name
        self.wants = wants
        self.is_ek = is_ek
        self.unavailable_dates = []

class Role:
    def __init__(self, name, max_count, ek_allowed=True):
        self.name = name
        self.max_count = max_count
        self.ek_allowed = ek_allowed

class Show:
    def __init__(self, title, datetime_, roles):
        self.title = title
        self.datetime = datetime_
        self.roles = roles

# ====== ROUTES ======

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


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            workers_list.clear()
            shows_list.clear()

            # ========= WORKERS CSV =========
            workers_file = request.files.get("workers_csv")
            if not workers_file:
                return "Hiányzik a workers CSV", 400

            workers_data = io.StringIO(workers_file.stream.read().decode("utf-8"))
            reader = csv.DictReader(workers_data)

            for row in reader:
                try:
                    name = row["name"].strip()
                    wants = row.get("wants") or None
                    is_ek = row.get("is_ek", "0") == "1"
                    unavailable = row.get("unavailable", "")

                    w = Worker(name, wants, is_ek)

                    for d in unavailable.split(","):
                        d = d.strip()
                        if d:
                            w.unavailable_dates.append(
                                datetime.strptime(d, "%Y-%m-%d").date()
                            )

                    workers_list.append(w)
                except Exception:
                    continue  # hibás sor kihagyása

            # ========= SHOWS CSV =========
            shows_file = request.files.get("shows_csv")
            if not shows_file:
                return "Hiányzik a shows CSV", 400

            shows_data = io.StringIO(shows_file.stream.read().decode("utf-8"))
            reader = csv.DictReader(shows_data)

            for row in reader:
                try:
                    title = row["title"]
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
                    shows_list.append(Show(title, dt, roles))
                except Exception:
                    continue

            return redirect(url_for("schedule"))

        except Exception:
            traceback.print_exc()
            return "Hiba történt CSV feldolgozás közben", 500

    return render_template("dashboard.html")


@app.route("/schedule")
def schedule():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template(
        "schedule.html",
        workers=workers_list,
        shows=shows_list
    )


# ====== START ======
if __name__ == "__main__":
    app.run(debug=True)
