from flask import Flask, render_template, request, redirect, url_for
import os
import json
import uuid
from datetime import datetime

from nutrition_engine.engine import generate_nutrition_plan
from nutrition_engine.data_loader import load_genes, load_biomarkers


app = Flask(__name__, template_folder="ui/templates", static_folder="ui/static")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
PROFILE_DIR = os.path.join(USER_DATA_DIR, "profiles")
USERS_INDEX = os.path.join(USER_DATA_DIR, "users_index.json")

os.makedirs(PROFILE_DIR, exist_ok=True)

if not os.path.exists(USERS_INDEX):
    with open(USERS_INDEX, "w") as f:
        json.dump([], f, indent=4)

def months_difference(old_date_str):
    old_date = datetime.strptime(old_date_str, "%Y-%m-%d")
    today = datetime.today()
    return (today.year - old_date.year) * 12 + (today.month - old_date.month)

def update_biomarker(biomarkers, name, value, unit=""):
    for b in biomarkers:
        if b["name"] == name:
            b["value"] = value
            b["unit"] = unit
            return
    biomarkers.append({
        "name": name,
        "value": value,
        "unit": unit
    })

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/new-user")
def new_user():
    return render_template(
    "new_user.html",
    genes=load_genes(),
    biomarkers=load_biomarkers()
)


@app.route("/save-user", methods=["POST"])
def save_user():
    form = request.form
    username = form["name"].strip().lower().replace(" ", "_")
    user_id = f"{username}_{uuid.uuid4().hex[:8]}"
    today = datetime.today().strftime("%Y-%m-%d")

    biomarkers = []
    names = form.getlist("biomarker_name[]")
    values = form.getlist("biomarker_value[]")
    units = form.getlist("biomarker_unit[]")

    for n, v, u in zip(names, values, units):
        if v.strip():
            biomarkers.append({
                "name": n.lower(),
                "value": float(v),
                "unit": u or ""
            })

    genes = []
    gene_names = form.getlist("gene_name[]")
    gene_eff = form.getlist("gene_efficiency[]")

    for g, e in zip(gene_names, gene_eff):
        if e.strip():
            genes.append({
                "name": g.upper(),
                "efficiency": int(e)
            })

    user_profile = {
        "user_id": user_id,
        "name": form["name"],
        "age": int(form["age"]),
        "gender": form["gender"],
        "height_cm": float(form["height"]),
        "weight_kg": float(form["weight"]),
        "activity_level": form["activity_level"],
        "diet_preference": form["diet"],
        "created_at": today,
        "last_updated": {
            "weight": today,
            "height": today,
            "biomarkers": today,
            "genes": today
        },
        "biomarkers": biomarkers,
        "genes": genes
    }

    with open(os.path.join(PROFILE_DIR, f"{user_id}.json"), "w") as f:
        json.dump(user_profile, f, indent=4)

    with open(USERS_INDEX, "r") as f:
        users = json.load(f)

    users.append(user_id)

    with open(USERS_INDEX, "w") as f:
        json.dump(users, f, indent=4)

    return render_template("after_save.html", user_id=user_id)

@app.route("/existing-user")
def existing_user():
    with open(USERS_INDEX, "r") as f:
        users = json.load(f)
    return render_template("existing_user.html", users=users)

@app.route("/load-user", methods=["POST"])
def load_user():
    return redirect(url_for("check_profile", user_id=request.form["user_id"]))

@app.route("/check-profile/<user_id>")
def check_profile(user_id):
    with open(os.path.join(PROFILE_DIR, f"{user_id}.json")) as f:
        user = json.load(f)

    updates_needed = []

    if months_difference(user["last_updated"]["weight"]) >= 1:
        updates_needed.append("Weight (monthly update recommended)")

    if months_difference(user["last_updated"]["height"]) >= 6:
        updates_needed.append("Height (6-month update recommended)")

    if months_difference(user["last_updated"]["biomarkers"]) >= 6:
        updates_needed.append("Biomarkers (6-month update recommended)")

    message = (
        "Based on your profile history, the following updates are recommended:<br><br>"
        + "<br>".join(updates_needed)
        if updates_needed
        else "Your profile is up to date. You may proceed."
    )

    return render_template("profile_check.html", user_id=user_id, message=message)

@app.route("/update-profile/<user_id>")
def update_profile(user_id):
    with open(os.path.join(PROFILE_DIR, f"{user_id}.json")) as f:
        user = json.load(f)
    return render_template(
    "update_user.html",
    user=user,
    genes=load_genes(),
    biomarkers=load_biomarkers()
)


@app.route("/save-updated-profile/<user_id>", methods=["POST"])
def save_updated_profile(user_id):
    path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    with open(path) as f:
        user = json.load(f)

    today = datetime.today().strftime("%Y-%m-%d")

    if request.form.get("height"):
        user["height_cm"] = float(request.form["height"])
        user["last_updated"]["height"] = today

    if request.form.get("weight"):
        user["weight_kg"] = float(request.form["weight"])
        user["last_updated"]["weight"] = today

    names = request.form.getlist("biomarker_name[]")
    values = request.form.getlist("biomarker_value[]")
    units = request.form.getlist("biomarker_unit[]")

    biomarker_updated = False
    for n, v, u in zip(names, values, units):
        if v.strip():
            update_biomarker(user["biomarkers"], n.lower(), float(v), u)
            biomarker_updated = True

    if biomarker_updated:
        user["last_updated"]["biomarkers"] = today

    with open(path, "w") as f:
        json.dump(user, f, indent=4)

    return redirect(url_for("after_save", user_id=user_id))

@app.route("/after-save/<user_id>")
def after_save(user_id):
    return render_template("after_save.html", user_id=user_id)

@app.route("/generate-meal/<user_id>")
def generate_meal(user_id):
    with open(os.path.join(PROFILE_DIR, f"{user_id}.json")) as f:
        user_profile = json.load(f)

    plan = generate_nutrition_plan(user_profile)

    return render_template(
        "result.html",
        result={
            "plan": plan
        }
    )

if __name__ == "__main__":
    app.run(debug=True)
