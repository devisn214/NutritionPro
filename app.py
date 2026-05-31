#app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import os
from html_report import generate_html_pdf
import json
import uuid
import hashlib
from datetime import datetime
import pandas as pd

from new.adaptive_engine import AdaptiveEngine
from new.feedback_manager import FeedbackManager
from llm_evaluator import LLMMealEvaluator
from pdf_working.pdf_service import process_pdf
from nutrition_engine.engine import generate_nutrition_plan
from nutrition_engine.data_loader import load_genes, load_biomarkers
from pdf_working.genome_parser import GenomeParser

app = Flask(__name__, template_folder="ui/templates", static_folder="ui/static")

app.secret_key = "nutritionpro123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
PROFILE_DIR = os.path.join(USER_DATA_DIR, "profiles")
PROFILE_RESULTS_DIR = os.path.join(USER_DATA_DIR, "results")
USERS_INDEX = os.path.join(USER_DATA_DIR, "users_index.json")
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(PROFILE_RESULTS_DIR, exist_ok=True)

if not os.path.exists(USERS_INDEX):
    with open(USERS_INDEX, "w") as f:
        json.dump([], f, indent=4)

ALLOWED_EXTENSIONS = {"pdf", "txt", "csv"}


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
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def allowed_genome_file(filename):
    allowed = {"txt", "csv"}
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed
    )


def months_difference(old_date_str):
    old_date = datetime.strptime(old_date_str, "%Y-%m-%d")
    today = datetime.today()
    return ((today.year - old_date.year) * 12 + (today.month - old_date.month))


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
    valid_biomarkers = set(b.lower() for b in load_biomarkers())
    return (valid_genes, valid_biomarkers)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    with open(USERS_INDEX, "r") as f:
        users = json.load(f)

    for user_id in users:
        profile_path = os.path.join(PROFILE_DIR, f"{user_id}.json")
        if not os.path.exists(profile_path):
            continue

        with open(profile_path) as pf:
            user = json.load(pf)

        if user.get("username") == username and user.get("password") == password:
            session["user_id"] = user_id
            return redirect(url_for("dashboard", user_id=user_id))

    return render_template("login.html", error_message="Invalid username or password")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------feedback route for adaptive engine-----------------------

@app.route("/food-feedback", methods=["POST"])
def food_feedback():
    user_id = request.form.get("user_id")
    food_name = request.form.get("food")
    feedback = int(request.form.get("feedback"))

    adaptive_engine = AdaptiveEngine()
    adaptive_engine.update_feedback(user_id, food_name, feedback)

    return jsonify({"status": "success"})


@app.route("/meal-feedback", methods=["POST"])
def meal_feedback():
    user_id = request.form.get("user_id")
    foods = request.form.getlist("foods[]")
    feedback = int(request.form.get("feedback"))
    confidence_score = float(request.form.get("confidence_score", 0))

    adaptive_engine = AdaptiveEngine()
    adaptive_engine.update_meal_feedback(user_id, foods, feedback)

    feedback_manager = FeedbackManager()
    feedback_manager.save_feedback(
        user_id=user_id,
        meal_type="meal",
        foods=foods,
        rating=feedback,
        confidence_score=confidence_score
    )

    return jsonify({"status": "success"})


@app.route("/confidence-feedback", methods=["POST"])
def confidence_feedback():
    user_id = request.form.get("user_id")
    feedback = int(request.form.get("feedback", 0))
    confidence_score = float(request.form.get("confidence_score", 0))

    feedback_manager = FeedbackManager()
    feedback_manager.save_feedback(
        user_id=user_id,
        meal_type="confidence",
        foods=[],
        rating=feedback,
        confidence_score=confidence_score
    )

    return jsonify({"success": True})


@app.route("/dashboard/<user_id>")
def dashboard(user_id):
    profile_path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    if not os.path.exists(profile_path):
        return render_template("login.html", error_message="User not found")

    with open(profile_path) as f:
        user = json.load(f)

    return render_template("dashboard.html", user=user)


@app.route("/create-account/<user_id>")
def create_account(user_id):
    return render_template("create_account.html", user_id=user_id)


@app.route("/create-account/<user_id>", methods=["POST"])
def save_account(user_id):
    username = request.form["username"].strip()
    password = request.form["password"].strip()
    confirm_password = request.form["confirm_password"].strip()

    if password != confirm_password:
        return render_template(
            "create_account.html",
            user_id=user_id,
            error_message="Passwords do not match"
        )

    with open(USERS_INDEX, "r") as f:
        users = json.load(f)

    for uid in users:
        profile_path_check = os.path.join(PROFILE_DIR, f"{uid}.json")
        if not os.path.exists(profile_path_check):
            continue

        with open(profile_path_check) as pf:
            existing_user = json.load(pf)

        if (existing_user.get("username") == username and uid != user_id):
            return render_template(
                "create_account.html",
                user_id=user_id,
                error_message="Username already exists"
            )

    profile_path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    with open(profile_path) as f:
        user = json.load(f)

    user["username"] = username
    user["password"] = password

    with open(profile_path, "w") as f:
        json.dump(user, f, indent=4, default=json_converter)

    session["user_id"] = user_id
    return redirect(url_for("dashboard", user_id=user_id))


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
    username = form["name"].strip().lower().replace(" ", "_")
    user_id = f"{username}_{uuid.uuid4().hex[:8]}"
    today = datetime.today().strftime("%Y-%m-%d")

    valid_genes, valid_biomarkers = get_valid_sets()
    genome_parser = GenomeParser("data/genenutrient.csv")
    pdf_file = request.files.get("report_pdf")

    pdf_biomarkers = []
    unknown_biomarkers = []

    if (pdf_file and pdf_file.filename != "" and allowed_file(pdf_file.filename)):
        try:
            pdf_biomarkers = process_pdf(pdf_file)
        except Exception as e:
            print("PDF ERROR:", e)

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
            return (f"Invalid biomarker entered: {n}", 400)

        biomarkers.append({
            "name": n,
            "value": float(v),
            "unit": (u or "").strip()
        })

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

    genes = []
    gene_rsids = form.getlist("gene_rsid[]")
    gene_genotypes = form.getlist("gene_genotype[]")
    df_gene = pd.read_csv("data/genenutrient.csv")

    for rsid, genotype in zip(gene_rsids, gene_genotypes):
        rsid = (rsid or "").strip()
        genotype = (genotype or "").strip().upper()

        if not rsid or not genotype:
            continue

        match = df_gene[df_gene["rsid"].astype(str).str.strip() == rsid]

        if match.empty:
            continue

        gene_symbol = match.iloc[0]["gene_symbol"]

        genes.append({
            "gene": gene_symbol,
            "rsid": rsid,
            "genotype": genotype
        })

    genome_file = request.files.get("genome_file")

    if (genome_file and genome_file.filename != "" and allowed_genome_file(genome_file.filename)):
        try:
            genome_path = os.path.join(UPLOAD_FOLDER, genome_file.filename)
            genome_file.save(genome_path)
            extracted_variants = genome_parser.extract_variants(genome_path)

            for g in extracted_variants:
                update_gene(genes, g["gene"], g["rsid"], g["genotype"])
        except Exception as e:
            print("GENOME PARSE ERROR:", e)

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

    profile_path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    with open(profile_path, "w") as f:
        json.dump(user_profile, f, indent=4, default=json_converter)

    with open(USERS_INDEX, "r") as f:
        users = json.load(f)

    if user_id not in users:
        users.append(user_id)

    with open(USERS_INDEX, "w") as f:
        json.dump(users, f, indent=4)

    return redirect(url_for("create_account", user_id=user_id))


# ------------------ PROFILE CHECK ------------------

@app.route("/check-profile/<user_id>")
def check_profile(user_id):
    path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    with open(path) as f:
        user = json.load(f)

    updates_needed = []

    if months_difference(user["last_updated"]["weight"]) >= 1:
        updates_needed.append("Weight (monthly update recommended)")

    if months_difference(user["last_updated"]["height"]) >= 6:
        updates_needed.append("Height (6-month update recommended)")

    if months_difference(user["last_updated"]["biomarkers"]) >= 6:
        updates_needed.append("Biomarkers (6-month update recommended)")

    if updates_needed:
        message = (
            "Based on your profile history, "
            "the following updates are recommended:<br><br>"
            + "<br>".join(updates_needed)
        )
    else:
        message = "Your profile is up to date. You may proceed."

    return render_template(
        "profile_check.html",
        user_id=user_id,
        message=message
    )


# ------------------ UPDATE PROFILE ------------------

@app.route("/update-profile/<user_id>")
def update_profile(user_id):
    path = os.path.join(PROFILE_DIR, f"{user_id}.json")

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


@app.route("/save-updated-profile/<user_id>", methods=["POST"])
def save_updated_profile(user_id):
    path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    with open(path) as f:
        user = json.load(f)

    today = datetime.today().strftime("%Y-%m-%d")
    valid_genes, valid_biomarkers = get_valid_sets()

    # ---------------- PDF UPDATE ----------------
    pdf_file = request.files.get("report_pdf")

    if pdf_file and pdf_file.filename != "" and allowed_file(pdf_file.filename):
        try:
            pdf_biomarkers = process_pdf(pdf_file)
            for b in pdf_biomarkers:
                name = (b.get("name") or "").lower()
                value = b.get("value")
                unit = b.get("unit", "")

                if name in valid_biomarkers and value is not None:
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
        user["height_cm"] = float(request.form["height"])
        user["last_updated"]["height"] = today

    if request.form.get("weight"):
        user["weight_kg"] = float(request.form["weight"])
        user["last_updated"]["weight"] = today

    # ---------------- BIOMARKER UPDATE ----------------
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

    # ---------------- GENE UPDATE ----------------
    genome_parser = GenomeParser("data/genenutrient.csv")
    genome_file = request.files.get("genome_file")

    if (genome_file and genome_file.filename != "" and allowed_genome_file(genome_file.filename)):
        try:
            genome_path = os.path.join(UPLOAD_FOLDER, genome_file.filename)
            genome_file.save(genome_path)
            extracted_variants = genome_parser.extract_variants(genome_path)

            for g in extracted_variants:
                update_gene(
                    user["genes"],
                    g["gene"],
                    g["rsid"],
                    g["genotype"]
                )
            user["last_updated"]["genes"] = today
        except Exception as e:
            print("GENOME UPDATE ERROR:", e)

    with open(path, "w") as f:
        json.dump(user, f, indent=4, default=json_converter)

    return redirect(url_for("dashboard", user_id=user_id))


# ------------------ DOWNLOAD REPORT ------------------

@app.route("/download-report/<user_id>")
def download_report(user_id):
    profile_path = os.path.join(PROFILE_DIR, f"{user_id}.json")
    plan_path = os.path.join(PROFILE_RESULTS_DIR, f"{user_id}_latest_plan.json")

    if not os.path.exists(profile_path):
        return ("User profile not found", 404)

    if not os.path.exists(plan_path):
        return ("Generate meal plan first", 400)

    with open(profile_path) as f:
        user_profile = json.load(f)

    with open(plan_path) as f:
        plan = json.load(f)

    pdf_path = generate_html_pdf(app, user_profile, plan, user_id)
    return send_file(pdf_path, as_attachment=True)


# ------------------ GENERATE MEAL ------------------

@app.route("/generate-meal/<user_id>")
def generate_meal(user_id):
    path = os.path.join(PROFILE_DIR, f"{user_id}.json")

    if not os.path.exists(path):
        return "User profile not found", 404

    with open(path) as f:
        user_profile = json.load(f)

    current_signature = hashlib.md5(
        json.dumps(
            {
                "biomarkers": user_profile.get("biomarkers", []),
                "genes": user_profile.get("genes", [])
            },
            sort_keys=True
        ).encode()
    ).hexdigest()

    latest_plan_path = os.path.join(
        PROFILE_RESULTS_DIR,
        f"{user_id}_latest_plan.json"
    )

    best_confidence = 0
    previous_confidence = 0
    old_signature = None
    profile_changed = False

    if os.path.exists(latest_plan_path):
        try:
            with open(latest_plan_path) as oldf:
                old_plan = json.load(oldf)
                best_confidence = float(
                    old_plan.get(
                        "best_confidence",
                        old_plan.get("confidence", 0)
                    )
                )
                previous_confidence = best_confidence
                old_signature = old_plan.get("profile_signature")
                profile_changed = (old_signature != current_signature)
        except:
            best_confidence = 0
            previous_confidence = 0
            old_signature = None
            profile_changed = False

    plan = generate_nutrition_plan(user_profile)
    plan["profile_signature"] = current_signature
    current_confidence = float(plan.get("confidence", 0))

    if best_confidence == 0:
        plan["confidence_state"] = "initial"
        plan["best_confidence"] = current_confidence
        plan["previous_confidence"] = 0
        plan["improvement_possible"] = True
        plan["optimization_complete"] = False

    # ==========================================
    # PROFILE CHANGED
    # Always use latest recommendation
    # ==========================================
    elif profile_changed:
        plan["confidence_state"] = "profile_updated"
        plan["previous_confidence"] = previous_confidence
        plan["best_confidence"] = current_confidence
        plan["improvement_possible"] = True
        plan["optimization_complete"] = False
        plan["confidence_message"] = (
            "Profile updated. Recommendation regenerated using latest "
            "biomarker and genomic information."
        )

    # ==========================================
    # SAME PROFILE
    # Confidence not improved - Keep old plan
    # ==========================================
    elif current_confidence <= best_confidence:
        with open(latest_plan_path) as oldf:
            plan = json.load(oldf)

        plan["confidence_state"] = "best"
        plan["previous_confidence"] = previous_confidence
        plan["best_confidence"] = best_confidence
        plan["improvement_possible"] = False
        plan["optimization_complete"] = True
        plan["confidence_message"] = (
            "No further improvement in recommendation confidence could "
            "be achieved using the current biomarker, genomic and dietary "
            "constraints."
        )

    # ==========================================
    # SAME PROFILE
    # Confidence improved
    # ==========================================
    else:
        plan["confidence_state"] = "improved"
        plan["previous_confidence"] = previous_confidence
        plan["best_confidence"] = current_confidence
        plan["improvement_possible"] = True
        plan["optimization_complete"] = False
        plan["confidence_message"] = (
            "Recommendation confidence improved through adaptive optimization."
        )

    improvement_possible = plan.get("improvement_possible", False)
    plan["generated_time"] = datetime.now().strftime("%d %B %Y, %I:%M %p")
    grouped_evidence = {}

    for ev in plan.get("evidence", []):
        trigger = ev.get("trigger", "")
        if trigger not in grouped_evidence:
            grouped_evidence[trigger] = {
                "trigger": trigger,
                "source": ev.get("source"),
                "status": ev.get("status", ""),
                "action": ev.get("action", ""),
                "nutrients": [],
                "logic_paths": []
            }

        nutrient = ev.get("nutrient_name", "")
        if nutrient and nutrient not in grouped_evidence[trigger]["nutrients"]:
            grouped_evidence[trigger]["nutrients"].append(nutrient)

    # ==========================================
    # 2. PROCESS GENES (Table & Evidence Injection)
    # ==========================================
    gene_analysis = []
    seen_genes = set()

    for gene in plan.get("gene_recommendations", []):
        # A. Build the Data for the Genomic Table
        key = (gene.get("gene"), gene.get("rsid"), gene.get("genotype"))
        if key not in seen_genes:
            seen_genes.add(key)
            nutrients = []
            for g in plan.get("gene_recommendations", []):
                if (g.get("gene") == gene.get("gene") and
                    g.get("rsid") == gene.get("rsid") and
                    g.get("genotype") == gene.get("genotype")):
                    nutrients.append(g.get("nutrient_name"))

            gene_analysis.append({
                "gene": gene.get("gene"),
                "variant": f"{gene.get('rsid')} ({gene.get('genotype')})",
                "nutrient": ", ".join(sorted(set(nutrients))),
                "action": gene.get("action", "Maintain standard intake")
            })

        # B. Inject EVERY Gene into AI Reasoning (Even Normal Ones)
        # RAG trigger format: "GeneName (rsid - genotype)"
        gene_trigger = f"{gene.get('gene')} ({gene.get('rsid')} - {gene.get('genotype')})"
        
        if gene_trigger not in grouped_evidence:
            nutrient_name = gene.get("nutrient_name", "related nutrients")
            grouped_evidence[gene_trigger] = {
                "trigger": gene_trigger,
                "source": "gene",
                "status": "normal",
                "action": "maintain",
                "nutrients": [nutrient_name],
                "logic_paths": []
            }
        else:
            if gene.get("nutrient_name") not in grouped_evidence[gene_trigger]["nutrients"]:
                grouped_evidence[gene_trigger]["nutrients"].append(gene.get("nutrient_name"))

    plan["gene_analysis"] = gene_analysis

    # ==========================================
    # 3. BUILD ONE UNIFIED REASONING STRING
    # ==========================================
    # This prevents the "3x logic path" duplication by combining nutrients
    for trigger, data in grouped_evidence.items():
        nutrient_text = ", ".join(data["nutrients"])
        action_text = data.get("action", "adjust").lower()
        
        if data["source"] == "biomarker":
            unified_reason = (
                f"{trigger.title()} is outside the reference range ({data.get('status', 'abnormal')}). "
                f"Nutritional science indicates that {nutrient_text} impacts this biomarker. "
                f"To compensate, the AI recommendation engine prioritized foods to {action_text} these nutrients."
            )
            data["logic_paths"] = [unified_reason]
            data["logic_summary"] = unified_reason

        else: # Gene
            if data.get("status") == "normal" or action_text == "maintain":
                unified_reason = (
                    f"The genetic variant {trigger} was analyzed for its impact on {nutrient_text}. "
                    f"Because your genotype does not pose an elevated metabolic risk, standard healthy baseline "
                    f"recommendations are maintained without applying aggressive dietary compensations."
                )
            else:
                unified_reason = (
                    f"The genetic variant {trigger} alters your nutritional requirements for {nutrient_text}. "
                    f"To proactively align the meal plan with your genomic profile, the AI prioritized foods "
                    f"to {action_text} these nutrients."
                )
            data["logic_paths"] = [unified_reason]
            data["logic_summary"] = unified_reason

    plan["evidence"] = list(grouped_evidence.values())

    # ==========================================
    # BIOMARKER DISPLAY TABLE
    # ==========================================
    grouped_biomarkers = {}

    for rec in plan.get("biomarker_recommendations", []):
        biomarker = rec.get("biomarker")
        if biomarker not in grouped_biomarkers:
            grouped_biomarkers[biomarker] = {
                "name": biomarker,
                "value": rec.get("current_value"),
                "unit": rec.get("unit"),
                "status": rec.get("status"),
                "reference_range": f"{rec.get('low')} - {rec.get('high')} {rec.get('unit')}",
                "nutrients": []
            }

        nutrient = rec.get("target_nutrient")
        if nutrient and nutrient not in grouped_biomarkers[biomarker]["nutrients"]:
            grouped_biomarkers[biomarker]["nutrients"].append(nutrient)

    plan["biomarker_analysis"] = list(grouped_biomarkers.values())

    # ==========================================
    # GENE DISPLAY TABLE
    # ==========================================
    gene_analysis = []
    seen_genes = set()

    for gene in plan.get("gene_recommendations", []):
        key = (gene.get("gene"), gene.get("rsid"), gene.get("genotype"))
        if key in seen_genes:
            continue

        seen_genes.add(key)
        nutrients = []

        for g in plan.get("gene_recommendations", []):
            if (g.get("gene") == gene.get("gene") and
                g.get("rsid") == gene.get("rsid") and
                g.get("genotype") == gene.get("genotype")):
                nutrients.append(g.get("nutrient_name"))

        gene_analysis.append({
            "gene": gene.get("gene"),
            "variant": f"{gene.get('rsid')} ({gene.get('genotype')})",
            "nutrient": ", ".join(sorted(set(nutrients))),
            "action": gene.get("action")
        })

    plan["gene_analysis"] = gene_analysis

    with open(latest_plan_path, "w") as f:
        json.dump(plan, f, indent=4, default=json_converter)

    print("\n===== GROUPED EVIDENCE =====")
    for e in plan.get("evidence", []):
        print(e)
    print("============================\n")

    return render_template(
        "result.html",
        result={"plan": plan},
        rag_context=plan.get("rag_context", []),
        evidence=plan.get("evidence", []),
        unknown_biomarkers=user_profile.get("unknown_biomarkers", []),
        improvement_possible=improvement_possible,
        user_id=user_id,
        user=user_profile,
        pdf_mode=False
    )


@app.route("/generate-improved-meal/<user_id>")
def generate_improved_meal(user_id):
    return redirect(url_for("generate_meal", user_id=user_id))


@app.route("/generate-evaluation/<user_id>", methods=["POST"])
def generate_evaluation(user_id):
    profile_path = os.path.join(PROFILE_DIR, f"{user_id}.json")
    latest_plan_path = os.path.join(PROFILE_RESULTS_DIR, f"{user_id}_latest_plan.json")

    if not os.path.exists(profile_path):
        return jsonify({
            "success": False,
            "error": "Profile not found"
        })

    if not os.path.exists(latest_plan_path):
        return """
    <script>
        alert('No meal plan found. Please generate your AI Meal Plan first.');
        window.location.href = document.referrer;
    </script>
    """

    with open(profile_path) as f:
        user_profile = json.load(f)

    with open(latest_plan_path) as f:
        plan = json.load(f)

    # ---------------------------------------------------------
    # BUG FIX: Tie evaluation cache strictly to the meal text
    # ---------------------------------------------------------
    current_meal_text = plan.get("llm_recommendation", "")

    if (
        plan.get("llm_evaluation")
        and plan["llm_evaluation"].get("evaluation")
        and plan["llm_evaluation"].get("evaluated_text") == current_meal_text
    ):
        return jsonify({
            "success": True,
            "evaluation": plan["llm_evaluation"]["evaluation"],
            "cached": True
        })
    # ---------------------------------------------------------

    evaluator = LLMMealEvaluator(model="llama3.1:8b-instruct-q4_K_M")

    evaluation = evaluator.evaluate(
        user_profile=user_profile,
        meal_plan=current_meal_text,
        calories=plan.get("calories", 0),
        macros=plan.get("macros", {}),
        rag_context=plan.get("rag_context", []),
        biomarker_recommendations=plan.get("biomarker_recommendations", []),
        gene_recommendations=plan.get("gene_recommendations", [])
    )

    if "evaluation" in evaluation:
        # Save the exact text evaluated to prevent future mismatches
        evaluation["evaluated_text"] = current_meal_text
        plan["llm_evaluation"] = evaluation

        with open(latest_plan_path, "w") as f:
            json.dump(plan, f, indent=4, default=json_converter)

        return jsonify({
            "success": True,
            "evaluation": evaluation["evaluation"]
        })

    return jsonify({
        "success": False,
        "error": evaluation.get("evaluation_error", "Unknown error")
    })


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    app.run(debug=True)