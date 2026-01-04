from flask import Flask, render_template, request, redirect, url_for, session, Response
from models import Worker, Role, Show
from datetime import datetime
from collections import defaultdict
import random
import os
import csv
import io
import traceback

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

        # ===== DOLGOZÓK CSV =====
        workers_file = request.files["workers_csv"]
        workers_data = io.StringIO(workers_file.stream.read().decode("utf-8"))
        reader = csv.DictReader(workers_data)

        for row in reader:
            name = row["name"].strip()
            wants = row.get("wants") or None
            is_ek = row.get("is_ek", "0") == "1"
            unavail_raw = row.get("unavailable", "")

            worker = Worker(name, wants, is_ek)
            for d in unavail_raw.split(","):
                try:
                    worker.unavailable_dates.append(
                        datetime.strptime(d.strip(), "%Y-%m-%d").date()
                    )
                except ValueError:
                    pass

            workers_list.append(worker)

        # ===== ELŐADÁSOK CSV =====
        shows_file = request.files["shows_csv"]
        shows_data = io.StringIO(shows_file.stream.read().decode("utf-8"))
        reader = csv.DictReader(shows_data)

        for row in reader:
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

        return redirect(url_for("schedule"))

    return render_template("dashboard.html")
