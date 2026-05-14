from flask import Flask, render_template, request, redirect, url_for,send_file
import os
from html_report import generate_html_pdf
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
def json_converter(obj):
        try:
            return int(obj)
        except:
            try:
                return float(obj)
            except:
                return str(obj)


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ------------------ HELPERS ------------------


def months_difference(old_date_str):
    old_date = datetime.strptime(old_date_str, "%Y-%m-%d")
    today = datetime.today()

    return (
        (today.year - old_date.year) * 12 +
        (today.month - old_date.month)
    )


def load_biomarker_units():
    df = pd.read_csv("data/biomarkers.csv")

    return dict(zip(df["name"], df["unit"]))


def load_rsid_genotypes():

    df = pd.read_csv("data/genenutrient.csv")

    rsid_map = {}

    for _, row in df.iterrows():

        rsid = str(row["rsid"]).strip()
        genotype = str(row["genotype"]).strip()
        gene = str(row["gene_symbol"]).strip().upper()

        if rsid not in rsid_map:
            rsid_map[rsid] = {
                "gene": gene,
                "genotypes": []
            }

        if genotype not in rsid_map[rsid]["genotypes"]:
            rsid_map[rsid]["genotypes"].append(genotype)

    return rsid_map


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


def update_gene(genes, gene, rsid, genotype):

    for g in genes:

        if g["rsid"] == rsid:
            g["gene"] = gene
            g["genotype"] = genotype
            return

    genes.append({
        "gene": gene,
        "rsid": rsid,
        "genotype": genotype
    })


def get_valid_sets():

    valid_genes = set(g.upper() for g in load_genes())
    valid_biomarkers = set(
        b.lower() for b in load_biomarkers()
    )

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
        biomarker_units=load_biomarker_units(),
        gene_variants=load_rsid_genotypes()
    )


@app.route("/save-user", methods=["POST"])
def save_user():

    form = request.form

    username = (
        form["name"]
        .strip()
        .lower()
        .replace(" ", "_")
    )

    user_id = f"{username}_{uuid.uuid4().hex[:8]}"

    today = datetime.today().strftime("%Y-%m-%d")

    valid_genes, valid_biomarkers = get_valid_sets()

    # ---------------- PDF PROCESSING ----------------

    pdf_file = request.files.get("report_pdf")

    pdf_biomarkers = []
    unknown_biomarkers = []

    print("\n--- PDF DEBUG ---")
    print("File received:", pdf_file)

    if (
        pdf_file and
        pdf_file.filename != "" and
        allowed_file(pdf_file.filename)
    ):

        try:

            pdf_biomarkers = process_pdf(pdf_file)

            print("\n--- EXTRACTED BIOMARKERS ---")

            for b in pdf_biomarkers:
                print(b)

        except Exception as e:
            print("PDF ERROR:", e)

    else:
        print("No valid PDF uploaded")

    # ---------------- MANUAL BIOMARKERS ----------------

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

    # ---------------- PDF OVERRIDE ----------------

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

        update_biomarker(
            biomarkers,
            name,
            float(value),
            unit
        )

    # ---------------- GENES ----------------

    genes = []

    gene_rsids = form.getlist("gene_rsid[]")
    gene_genotypes = form.getlist("gene_genotype[]")

    df_gene = pd.read_csv("data/genenutrient.csv")

    for rsid, genotype in zip(
        gene_rsids,
        gene_genotypes
    ):

        rsid = (rsid or "").strip()
        genotype = (
            genotype or ""
        ).strip().upper()

        if not rsid:
            continue

        if not genotype:
            return f"Genotype required for {rsid}", 400

        match = df_gene[
            df_gene["rsid"]
            .astype(str)
            .str.strip() == rsid
        ]

        if match.empty:
            return f"Invalid rsid entered: {rsid}", 400

        gene_symbol = match.iloc[0]["gene_symbol"]

        genes.append({
            "gene": gene_symbol,
            "rsid": rsid,
            "genotype": genotype
        })

    # ---------------- PROFILE ----------------

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

    profile_path = os.path.join(
        PROFILE_DIR,
        f"{user_id}.json"
    )

    with open(profile_path, "w") as f:
        json.dump(user_profile, f, indent=4)

    with open(USERS_INDEX, "r") as f:
        users = json.load(f)

    if user_id not in users:
        users.append(user_id)

    with open(USERS_INDEX, "w") as f:
        json.dump(users, f, indent=4)

    return render_template(
        "after_save.html",
        user_id=user_id
    )


@app.route("/existing-user")
def existing_user():

    with open(USERS_INDEX, "r") as f:
        users = json.load(f)

    return render_template(
        "existing_user.html",
        users=users
    )


@app.route("/load-user", methods=["POST"])
def load_user():

    return redirect(
        url_for(
            "check_profile",
            user_id=request.form["user_id"]
        )
    )


@app.route("/check-profile/<user_id>")
def check_profile(user_id):

    path = os.path.join(
        PROFILE_DIR,
        f"{user_id}.json"
    )

    with open(path) as f:
        user = json.load(f)

    updates_needed = []

    if months_difference(
        user["last_updated"]["weight"]
    ) >= 1:

        updates_needed.append(
            "Weight (monthly update recommended)"
        )

    if months_difference(
        user["last_updated"]["height"]
    ) >= 6:

        updates_needed.append(
            "Height (6-month update recommended)"
        )

    if months_difference(
        user["last_updated"]["biomarkers"]
    ) >= 6:

        updates_needed.append(
            "Biomarkers (6-month update recommended)"
        )

    if updates_needed:

        message = (
            "Based on your profile history, "
            "the following updates are recommended:<br><br>"
            + "<br>".join(updates_needed)
        )

    else:
        message = (
            "Your profile is up to date. "
            "You may proceed."
        )

    return render_template(
        "profile_check.html",
        user_id=user_id,
        message=message
    )


@app.route("/update-profile/<user_id>")
def update_profile(user_id):

    path = os.path.join(
        PROFILE_DIR,
        f"{user_id}.json"
    )

    with open(path) as f:
        user = json.load(f)

    return render_template(
        "update_user.html",
        user=user,
        genes=load_genes(),
        biomarkers=load_biomarkers(),
        biomarker_units=load_biomarker_units(),
        gene_variants=load_rsid_genotypes()
    )


@app.route(
    "/save-updated-profile/<user_id>",
    methods=["POST"]
)
def save_updated_profile(user_id):

    path = os.path.join(
        PROFILE_DIR,
        f"{user_id}.json"
    )

    with open(path) as f:
        user = json.load(f)

    today = datetime.today().strftime("%Y-%m-%d")

    valid_genes, valid_biomarkers = get_valid_sets()

    # ---------------- PDF UPDATE ----------------

    pdf_file = request.files.get("report_pdf")

    if (
        pdf_file and
        pdf_file.filename != "" and
        allowed_file(pdf_file.filename)
    ):

        try:

            pdf_biomarkers = process_pdf(pdf_file)

            for b in pdf_biomarkers:

                name = (
                    b.get("name") or ""
                ).lower()

                value = b.get("value")
                unit = b.get("unit", "")

                if (
                    name in valid_biomarkers and
                    value is not None
                ):

                    update_biomarker(
                        user["biomarkers"],
                        name,
                        float(value),
                        unit
                    )

            user["last_updated"]["biomarkers"] = today

        except Exception as e:
            print("PDF UPDATE ERROR:", e)

    # ---------------- HEIGHT / WEIGHT ----------------

    if request.form.get("height"):

        user["height_cm"] = float(
            request.form["height"]
        )

        user["last_updated"]["height"] = today

    if request.form.get("weight"):

        user["weight_kg"] = float(
            request.form["weight"]
        )

        user["last_updated"]["weight"] = today

    # ---------------- MANUAL BIOMARKER UPDATE ----------------

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

            update_biomarker(
                user["biomarkers"],
                n,
                float(v),
                u
            )

            biomarker_updated = True

    if biomarker_updated:
        user["last_updated"]["biomarkers"] = today

    # ---------------- GENE UPDATE ----------------

    gene_rsids = request.form.getlist("gene_rsid[]")
    gene_genotypes = request.form.getlist("gene_genotype[]")

    df_gene = pd.read_csv("data/genenutrient.csv")

    for rsid, genotype in zip(
        gene_rsids,
        gene_genotypes
    ):

        rsid = (rsid or "").strip()

        genotype = (
            genotype or ""
        ).strip().upper()

        if not rsid or not genotype:
            continue

        match = df_gene[
            df_gene["rsid"]
            .astype(str)
            .str.strip() == rsid
        ]

        if match.empty:
            continue

        gene_symbol = match.iloc[0]["gene_symbol"]

        update_gene(
            user["genes"],
            gene_symbol,
            rsid,
            genotype
        )

    user["last_updated"]["genes"] = today

    

    with open(path, "w") as f:
        json.dump(user, f, indent=4, default=json_converter)

    return redirect(
        url_for(
            "after_save",
            user_id=user_id
        )
    )


@app.route("/after-save/<user_id>")
def after_save(user_id):

    return render_template(
        "after_save.html",
        user_id=user_id
    )
     
@app.route("/download-report/<user_id>")
def download_report(user_id):

        profile_path = os.path.join(PROFILE_DIR,f"{user_id}.json")

        plan_path = os.path.join(
        PROFILE_DIR,
        f"{user_id}_latest_plan.json"
    )

        if not os.path.exists(profile_path):
            return "User profile not found", 404

        if not os.path.exists(plan_path):
            return "Generate meal plan first", 400

        with open(profile_path) as f:
            user_profile = json.load(f)

        with open(plan_path) as f:
            plan = json.load(f)

        pdf_path = generate_html_pdf(app,user_profile,plan,user_id)

        return send_file(pdf_path,as_attachment=True)


@app.route("/generate-meal/<user_id>")
def generate_meal(user_id):

    path = os.path.join(
        PROFILE_DIR,
        f"{user_id}.json"
    )

    with open(path) as f:
        user_profile = json.load(f)

    plan = generate_nutrition_plan(user_profile)
    latest_plan_path = os.path.join(PROFILE_DIR,f"{user_id}_latest_plan.json")

    with open(latest_plan_path, "w") as f:
        json.dump(plan, f, indent=4, default=json_converter)

    return render_template(
        "result.html",
        result={"plan": plan},
        rag_context=plan.get("rag_context", []),
        evidence=plan.get("evidence", []),
        unknown_biomarkers=user_profile.get(
            "unknown_biomarkers",
            []
        ),
        user_id=user_id
    )
    



# ------------------ MAIN ------------------

if __name__ == "__main__":
    app.run(debug=True)