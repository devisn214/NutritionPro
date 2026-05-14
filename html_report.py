from xhtml2pdf import pisa
from flask import render_template
import os


def generate_html_pdf(
    app,
    user_profile,
    plan,
    user_id
):

    reports_dir = "reports"

    os.makedirs(
        reports_dir,
        exist_ok=True
    )

    pdf_path = os.path.join(
        reports_dir,
        f"{user_id}_nutrition_report.pdf"
    )

    with app.app_context():

        html = render_template(

            "result.html",

            result={"plan": plan},

            rag_context=plan.get(
                "rag_context",
                []
            ),

            evidence=[],

            unknown_biomarkers=user_profile.get(
                "unknown_biomarkers",
                []
            ),

            user=user_profile,

            user_id=user_id,

            pdf_mode=True
        )

    with open(pdf_path, "wb") as pdf_file:

        pisa.CreatePDF(

            src=html,

            dest=pdf_file
        )

    return pdf_path