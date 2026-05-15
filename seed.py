"""Seed the database with sample companies and jobs.

The data set is hand-curated to *resemble* the kind of listings published
on glints.com/id (a mix of Indonesian tech companies, retail, finance,
and remote international roles). It is not scraped from Glints — the
schema, copy, and salary ranges are written from scratch so the app
ships with a usable dataset out of the box.

Run:
    python seed.py [--reset]
"""
from __future__ import annotations

import argparse
import sys

from app import create_app
from backend.database import execute, get_db, query_one


COMPANIES: list[dict] = [
    {
        "name": "Tokopedia",
        "industry": "E-commerce",
        "website": "https://www.tokopedia.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Tokopedia adalah perusahaan teknologi yang memungkinkan setiap orang dan pemilik bisnis di Indonesia untuk membuka dan mengelola toko daring dengan mudah.",
        "employees": "1000+", "founded_year": 2009,
    },
    {
        "name": "Gojek",
        "industry": "Super App",
        "website": "https://www.gojek.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Gojek adalah aplikasi on-demand terdepan di Asia Tenggara yang menyediakan beragam layanan mulai dari transportasi, pesan-antar makanan, hingga pembayaran digital.",
        "employees": "1000+", "founded_year": 2010,
    },
    {
        "name": "Traveloka",
        "industry": "Travel & Hospitality",
        "website": "https://www.traveloka.com",
        "city": "Jakarta Barat",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Platform perjalanan dan gaya hidup terdepan di Asia Tenggara.",
        "employees": "1000+", "founded_year": 2012,
    },
    {
        "name": "Bukalapak",
        "industry": "E-commerce",
        "website": "https://www.bukalapak.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Marketplace yang memberdayakan UMKM Indonesia.",
        "employees": "1000+", "founded_year": 2010,
    },
    {
        "name": "Shopee Indonesia",
        "industry": "E-commerce",
        "website": "https://shopee.co.id",
        "city": "Jakarta Pusat",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Platform belanja online terbesar di Asia Tenggara & Taiwan.",
        "employees": "1000+", "founded_year": 2015,
    },
    {
        "name": "BCA Digital",
        "industry": "Banking & Finance",
        "website": "https://www.bcadigital.co.id",
        "city": "Jakarta Pusat",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Bank digital BCA dengan layanan keuangan modern.",
        "employees": "500-1000", "founded_year": 2021,
    },
    {
        "name": "Bank Mandiri",
        "industry": "Banking & Finance",
        "website": "https://www.bankmandiri.co.id",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Salah satu bank terbesar di Indonesia.",
        "employees": "1000+", "founded_year": 1998,
    },
    {
        "name": "Telkomsel",
        "industry": "Telekomunikasi",
        "website": "https://www.telkomsel.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Operator telekomunikasi seluler terbesar di Indonesia.",
        "employees": "1000+", "founded_year": 1995,
    },
    {
        "name": "Pertamina",
        "industry": "Energi",
        "website": "https://www.pertamina.com",
        "city": "Jakarta Pusat",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Perusahaan energi nasional milik negara.",
        "employees": "1000+", "founded_year": 1957,
    },
    {
        "name": "Ruangguru",
        "industry": "EdTech",
        "website": "https://www.ruangguru.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Perusahaan teknologi pendidikan terbesar di Asia Tenggara.",
        "employees": "1000+", "founded_year": 2014,
    },
    {
        "name": "Xendit",
        "industry": "Fintech",
        "website": "https://www.xendit.co",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Infrastruktur pembayaran untuk Asia Tenggara.",
        "employees": "500-1000", "founded_year": 2015,
    },
    {
        "name": "Halodoc",
        "industry": "HealthTech",
        "website": "https://www.halodoc.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Aplikasi kesehatan digital pelopor di Indonesia.",
        "employees": "500-1000", "founded_year": 2016,
    },
    {
        "name": "Grab Indonesia",
        "industry": "Super App",
        "website": "https://www.grab.com/id",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Aplikasi super untuk transportasi, makanan, dan pembayaran.",
        "employees": "1000+", "founded_year": 2014,
    },
    {
        "name": "PT Astra International",
        "industry": "Otomotif",
        "website": "https://www.astra.co.id",
        "city": "Jakarta Utara",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Konglomerat otomotif dan layanan keuangan terbesar.",
        "employees": "1000+", "founded_year": 1957,
    },
    {
        "name": "GoTo Financial",
        "industry": "Fintech",
        "website": "https://www.gotocompany.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Layanan finansial yang menyatukan Gojek dan Tokopedia.",
        "employees": "1000+", "founded_year": 2021,
    },
    {
        "name": "Blibli",
        "industry": "E-commerce",
        "website": "https://www.blibli.com",
        "city": "Jakarta Barat",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Online mall premium di Indonesia.",
        "employees": "1000+", "founded_year": 2011,
    },
    {
        "name": "Sirclo",
        "industry": "SaaS",
        "website": "https://www.sirclo.com",
        "city": "Tangerang",
        "province": "Banten",
        "country": "Indonesia",
        "description": "Solusi commerce enabler untuk brand di Indonesia.",
        "employees": "500-1000", "founded_year": 2013,
    },
    {
        "name": "Kitabisa",
        "industry": "Crowdfunding",
        "website": "https://www.kitabisa.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Platform penggalangan dana sosial dan donasi.",
        "employees": "100-500", "founded_year": 2013,
    },
    {
        "name": "Stockbit",
        "industry": "Fintech",
        "website": "https://www.stockbit.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Komunitas investor saham dan platform sekuritas digital.",
        "employees": "100-500", "founded_year": 2013,
    },
    {
        "name": "Mekari",
        "industry": "SaaS",
        "website": "https://www.mekari.com",
        "city": "Jakarta Selatan",
        "province": "DKI Jakarta",
        "country": "Indonesia",
        "description": "Software ERP & HR cloud untuk bisnis Indonesia.",
        "employees": "500-1000", "founded_year": 2015,
    },
    {
        "name": "Remote.com",
        "industry": "Global HR Platform",
        "website": "https://remote.com",
        "city": "Singapore",
        "province": "",
        "country": "Singapore",
        "description": "Platform global HR yang memungkinkan perusahaan hire talenta worldwide.",
        "employees": "1000+", "founded_year": 2019,
    },
    {
        "name": "Canva",
        "industry": "Design SaaS",
        "website": "https://www.canva.com",
        "city": "Sydney",
        "province": "",
        "country": "Australia",
        "description": "Platform desain visual global.",
        "employees": "1000+", "founded_year": 2013,
    },
    {
        "name": "GitLab Inc",
        "industry": "DevOps",
        "website": "https://about.gitlab.com",
        "city": "Remote",
        "province": "",
        "country": "Worldwide",
        "description": "Platform DevSecOps single application.",
        "employees": "1000+", "founded_year": 2014,
    },
]


# Generic job templates referencing the company by name.
JOB_TEMPLATES: list[dict] = [
    {
        "title": "Backend Engineer (Python)",
        "skills": "python,flask,django,sql,rest api,docker,git,linux",
        "description": "Membangun layanan backend yang andal untuk produk kami.",
        "requirements": "Min 2 tahun pengalaman, kuat di Python dan SQL.",
        "employment_type": "Full-time",
        "min_experience": 2, "min_age": 21, "max_age": 40,
        "salary_min": 10_000_000, "salary_max": 25_000_000,
    },
    {
        "title": "Frontend Engineer (React)",
        "skills": "javascript,typescript,react,html,css,git,rest api",
        "description": "Mengembangkan interface yang responsif dan accessible.",
        "requirements": "Pengalaman minimal 2 tahun dengan React.",
        "employment_type": "Full-time",
        "min_experience": 2, "min_age": 21, "max_age": 40,
        "salary_min": 9_000_000, "salary_max": 22_000_000,
    },
    {
        "title": "Data Analyst",
        "skills": "sql,excel,python,data science,communication",
        "description": "Menganalisis data bisnis dan menyajikan insight.",
        "requirements": "Mahir SQL dan tools analitik.",
        "employment_type": "Full-time",
        "min_experience": 1, "min_age": 20, "max_age": 35,
        "salary_min": 7_000_000, "salary_max": 16_000_000,
    },
    {
        "title": "Mobile Developer (Kotlin/Swift)",
        "skills": "kotlin,swift,git,rest api",
        "description": "Membangun aplikasi mobile Android & iOS.",
        "requirements": "Pengalaman publikasi aplikasi mobile.",
        "employment_type": "Full-time",
        "min_experience": 2, "min_age": 22, "max_age": 40,
        "salary_min": 11_000_000, "salary_max": 26_000_000,
    },
    {
        "title": "DevOps Engineer",
        "skills": "linux,docker,kubernetes,aws,git,python",
        "description": "Mengelola infrastruktur cloud dan CI/CD pipeline.",
        "requirements": "Familiar dengan AWS dan container.",
        "employment_type": "Full-time",
        "min_experience": 3, "min_age": 23, "max_age": 45,
        "salary_min": 13_000_000, "salary_max": 30_000_000,
    },
    {
        "title": "UI/UX Designer",
        "skills": "design,communication,problem solving",
        "description": "Mendesain user experience yang intuitif.",
        "requirements": "Portofolio yang kuat di Figma.",
        "employment_type": "Full-time",
        "min_experience": 1, "min_age": 20, "max_age": 38,
        "salary_min": 8_000_000, "salary_max": 18_000_000,
    },
    {
        "title": "Marketing Specialist",
        "skills": "marketing,communication,excel,problem solving",
        "description": "Merencanakan kampanye marketing digital.",
        "requirements": "Punya pengalaman digital marketing.",
        "employment_type": "Full-time",
        "min_experience": 1, "min_age": 21, "max_age": 35,
        "salary_min": 6_000_000, "salary_max": 13_000_000,
    },
    {
        "title": "Customer Service Representative",
        "skills": "customer service,communication,english",
        "description": "Melayani pertanyaan dan keluhan customer.",
        "requirements": "Sabar, komunikatif, dan responsif.",
        "employment_type": "Full-time",
        "min_experience": 0, "min_age": 19, "max_age": 35,
        "salary_min": 4_500_000, "salary_max": 7_500_000,
    },
    {
        "title": "Accountant",
        "skills": "accounting,excel,communication",
        "description": "Mengelola pembukuan dan laporan pajak.",
        "requirements": "Lulusan akuntansi, paham pajak.",
        "employment_type": "Full-time",
        "min_experience": 1, "min_age": 22, "max_age": 40,
        "salary_min": 6_000_000, "salary_max": 12_000_000,
    },
    {
        "title": "Product Manager",
        "skills": "project management,communication,leadership,problem solving",
        "description": "Memimpin pengembangan produk dari ide hingga launch.",
        "requirements": "Minimum 3 tahun pengalaman PM.",
        "employment_type": "Full-time",
        "min_experience": 3, "min_age": 25, "max_age": 45,
        "salary_min": 17_000_000, "salary_max": 35_000_000,
    },
]


def reset_tables() -> None:
    db = get_db()
    for table in (
        "company_search_log", "cv_uploads", "jobs", "companies",
        "experiences", "partners", "otps",
    ):
        db.execute(f"DELETE FROM {table}")
    db.execute("DELETE FROM users WHERE role != 'admin'")
    db.commit()


def seed() -> None:
    inserted_companies = 0
    inserted_jobs = 0
    for c in COMPANIES:
        existing = query_one("SELECT id FROM companies WHERE name=?", (c["name"],))
        if existing:
            cid = existing["id"]
        else:
            cid = execute(
                "INSERT INTO companies(name, industry, website, city, province, country, "
                "description, employees, founded_year, is_approved) "
                "VALUES(?,?,?,?,?,?,?,?,?,1)",
                (
                    c["name"], c["industry"], c["website"], c["city"], c["province"],
                    c["country"], c["description"], c["employees"], c["founded_year"],
                ),
            )
            inserted_companies += 1
        # Pick 2-4 jobs per company deterministically
        idx = inserted_companies % len(JOB_TEMPLATES)
        for offset in (0, 3, 5):
            t = JOB_TEMPLATES[(idx + offset) % len(JOB_TEMPLATES)]
            existing_job = query_one(
                "SELECT id FROM jobs WHERE company_id=? AND title=?",
                (cid, t["title"]),
            )
            if existing_job:
                continue
            execute(
                "INSERT INTO jobs(company_id, title, description, requirements, "
                "skills, employment_type, country, province, city, salary_min, "
                "salary_max, min_experience, min_age, max_age, is_active) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                (
                    cid, t["title"], t["description"], t["requirements"],
                    t["skills"], t["employment_type"], c["country"],
                    c.get("province") or "", c["city"],
                    t.get("salary_min"), t.get("salary_max"),
                    t["min_experience"], t["min_age"], t["max_age"],
                ),
            )
            inserted_jobs += 1
    print(f"Inserted {inserted_companies} companies and {inserted_jobs} jobs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe data first")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        if args.reset:
            print("Resetting tables...")
            reset_tables()
        seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
