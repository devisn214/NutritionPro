from flask import Flask, render_template, request, redirect, url_for
import os
import json
import uuid
from datetime import datetime
import pandas as pd

from pdf_working.pdf_service import process_pdf


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

# ------------------ FILE VALIDATION ------------------

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ HELPERS ------------------

def months_difference(old_date_str):
    old_date = datetime.strptime(old_date_str, "%Y-%m-%d")
    today = datetime.today()
    return (today.year - old_date.year) * 12 + (today.month - old_date.month)


def load_biomarker_units():
    df = pd.read_csv("data/biomarkers.csv")
    return dict(zip(df["name"], df["unit"]))


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


def update_gene(genes, name, variant):
    for g in genes:
        if g["name"].upper() == name.upper():
            g["variant"] = variant
            return
    genes.append({
        "name": name,
        "variant": variant
    })


def get_valid_sets():
    valid_genes = set(g.upper() for g in load_genes())
    valid_biomarkers = set(b.lower() for b in load_biomarkers())
    return valid_genes, valid_biomarkers

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/new-user")
def new_user():
    return render_template(
        "new_user.html",
        genes=load_genes(),
        biomarkers=load_biomarkers(),
        biomarker_units=load_biomarker_units()
    )


@app.route("/save-user", methods=["POST"])
def save_user():
    form = request.form
    username = form["name"].strip().lower().replace(" ", "_")
    user_id = f"{username}_{uuid.uuid4().hex[:8]}"
    today = datetime.today().strftime("%Y-%m-%d")

    valid_genes, valid_biomarkers = get_valid_sets()

    # -------- PDF PROCESSING --------
    pdf_file = request.files.get("report_pdf")
    pdf_biomarkers = []
    unknown_biomarkers = []

    print("\n--- PDF DEBUG ---")
    print("File received:", pdf_file)

    if pdf_file and pdf_file.filename != "" and allowed_file(pdf_file.filename):
        try:
            pdf_biomarkers = process_pdf(pdf_file)

            print("\n--- EXTRACTED BIOMARKERS ---")
            for b in pdf_biomarkers:
             print(b)

        except Exception as e:
            print("PDF ERROR:", e)

      

    else:
        print("No valid PDF uploaded")

    # -------- MANUAL BIOMARKERS --------
    biomarkers = []
    names = form.getlist("biomarker_name[]")
    values = form.getlist("biomarker_value[]")
    units = form.getlist("biomarker_unit[]")

    for n, v, u in zip(names, values, units):
        n = (n or "").strip().lower()
        v = (v or "").strip()

        if not v:
            continue

        if n not in valid_biomarkers:
            return f"Invalid biomarker entered: {n}", 400

        biomarkers.append({
            "name": n,
            "value": float(v),
            "unit": (u or "").strip()
        })

    # -------- PDF OVERRIDE --------
    for b in pdf_biomarkers:
        name = (b.get("name") or "").lower()
        value = b.get("value")
        unit = b.get("unit", "")

        if not name or value is None:
            continue

        if name not in valid_biomarkers:
            unknown_biomarkers.append({
                "name": name,
                "value": value
            })
            continue

        update_biomarker(biomarkers, name, float(value), unit)

    # -------- GENES --------
    genes = []
    gene_names = form.getlist("gene_name[]")
    gene_status = form.getlist("gene_status[]")
    gene_variants = form.getlist("gene_variant[]")

    for g, s, v in zip(gene_names, gene_status, gene_variants):
        g = (g or "").strip().upper()
        v = (v or "").strip()

        if not g:
            continue

        if g not in valid_genes:
            return f"Invalid gene entered: {g}", 400

        if s == "normal":
            genes.append({"name": g, "variant": "Normal"})
        else:
            if not v:
                return f"Variant required for gene {g}", 400
            genes.append({"name": g, "variant": v})

    # -------- PROFILE --------
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
        "genes": genes,
        "unknown_biomarkers": unknown_biomarkers
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
        biomarkers=load_biomarkers(),
        biomarker_units=load_biomarker_units()
    )


@app.route("/save-updated-profile/<user_id>", methods=["POST"])
def save_updated_profile(user_id):
    path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    with open(path) as f:
        user = json.load(f)

    today = datetime.today().strftime("%Y-%m-%d")
    valid_genes, valid_biomarkers = get_valid_sets()

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
        n = (n or "").strip().lower()
        v = (v or "").strip()

        if v:
            if n not in valid_biomarkers:
                return f"Invalid biomarker entered: {n}", 400
            update_biomarker(user["biomarkers"], n, float(v), u)
            biomarker_updated = True

    if biomarker_updated:
        user["last_updated"]["biomarkers"] = today

    gene_names = request.form.getlist("gene_name[]")
    gene_status = request.form.getlist("gene_status[]")
    gene_variants = request.form.getlist("gene_variant[]")

    for g, s, v in zip(gene_names, gene_status, gene_variants):
        g = g.upper()
        if s == "normal":
            update_gene(user["genes"], g, "Normal")
        elif v:
            update_gene(user["genes"], g, v)

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
        result={"plan": plan},
        rag_context=plan.get("rag_context", []),
        evidence=plan.get("evidence", []),
        unknown_biomarkers=user_profile.get("unknown_biomarkers", [])
    )


if __name__ == "__main__":
    app.run(debug=True)