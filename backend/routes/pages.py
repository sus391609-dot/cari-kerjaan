"""HTML page routes."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for

from ..auth import admin_required, company_required, current_user, login_required


bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    return render_template("index.html", user=current_user())


@bp.get("/login")
def login():
    return render_template("login.html", user=current_user())


@bp.get("/register")
def register():
    return render_template("register.html", user=current_user())


@bp.get("/verify-otp")
def verify_otp_page():
    return render_template("verify_otp.html", user=current_user())


@bp.get("/jobs")
def jobs():
    return render_template("jobs.html", user=current_user())


@bp.get("/jobs/<int:job_id>")
def job_detail(job_id: int):
    return render_template("job_detail.html", user=current_user(), job_id=job_id)


@bp.get("/cv")
@login_required
def cv_upload():
    return render_template("cv_upload.html", user=current_user())


@bp.get("/generate-cv")
def generate_cv():
    # Open to both logged-in and guest users so visitors can try the builder.
    return render_template("generate_cv.html", user=current_user())


@bp.get("/generate-cover-letter")
def generate_cover_letter():
    return render_template("generate_cover_letter.html", user=current_user())


@bp.get("/share-experience")
@login_required
def share_experience():
    return render_template("share_experience.html", user=current_user())


@bp.get("/logout")
def logout():
    from ..auth import logout_user
    logout_user()
    return redirect(url_for("pages.index"))


@bp.get("/maintenance")
def maintenance():
    return render_template("maintenance.html")


# ----------------- Admin ----------------- #


@bp.get("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html", user=current_user())


@bp.get("/admin/companies")
@admin_required
def admin_companies():
    return render_template("admin/companies.html", user=current_user())


@bp.get("/admin/users")
@admin_required
def admin_users():
    return render_template("admin/users.html", user=current_user())


@bp.get("/admin/jobs")
@admin_required
def admin_jobs():
    return render_template("admin/jobs.html", user=current_user())


@bp.get("/admin/approvals")
@admin_required
def admin_approvals():
    return render_template("admin/approvals.html", user=current_user())


@bp.get("/admin/partners")
@admin_required
def admin_partners():
    return render_template("admin/partners.html", user=current_user())


@bp.get("/admin/experiences")
@admin_required
def admin_experiences():
    return render_template("admin/experiences.html", user=current_user())


@bp.get("/admin/maintenance")
@admin_required
def admin_maintenance():
    return render_template("admin/maintenance.html", user=current_user())


# ----------------- Company ----------------- #


@bp.get("/company")
@company_required
def company_dashboard():
    return render_template("company/dashboard.html", user=current_user())


@bp.get("/company/post-job")
@company_required
def company_post_job():
    return render_template("company/post_job.html", user=current_user())
