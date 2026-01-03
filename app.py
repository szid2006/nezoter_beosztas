from flask import Flask, render_template, request, redirect, url_for, session, Response
from models import Worker, Role, Show
from main import generate_schedule
from datetime import datetime
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
                        pass  # rossz dátum kihagyva

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
# BEOSZTÁS
# ─────────────────────────────
@app.route("/schedule")
def schedule():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    try:
        # ─── Súlyozott beosztás: ÉK dolgozók ritkábban ───
        for worker in workers_list:
            # weight=1 a normál dolgozó, weight=0.5 az ÉK dolgozó
            worker.weight = 0.5 if worker.is_ek else 1

        # generate_schedule használja a weight attribútumot
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
